import streamlit as st
import pandas as pd
import requests
import datetime
import time
import plotly.express as px
from textblob import TextBlob

# --- Page Config ---
st.set_page_config(page_title="2026 Macro Stock Pro", layout="wide")
st.title("📈 AI Stock Pro: 2026 Market Analysis")

# --- Initialize Session State ---
if 'results_data' not in st.session_state:
    st.session_state.results_data = {}
if 'analysis_logs' not in st.session_state:
    st.session_state.analysis_logs = []
if 'quota_info' not in st.session_state:
    st.session_state.quota_info = {"remaining": 100, "limit": 100}

NEWS_API_KEY = st.secrets.get("news_api_key")

# --- Logic Functions ---
def get_news_sentiment(ticker, api_key, start_date, end_date):
    """Fetches news and updates global rate limit quota."""
    base_url = "https://newsapi.org"
    params = {
        "q": ticker,
        "from": start_date.strftime('%Y-%m-%d'),
        "to": end_date.strftime('%Y-%m-%d'),
        "language": "en",
        "sortBy": "relevancy",
        "apiKey": api_key
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        
        # Update Quota Info from Headers
        remaining = response.headers.get("X-RateLimit-Remaining")
        limit = response.headers.get("X-RateLimit-Limit")
        if remaining:
            st.session_state.quota_info["remaining"] = int(remaining)
        if limit:
            st.session_state.quota_info["limit"] = int(limit)

        if response.status_code != 200:
            return None, f"Error {response.status_code}: {response.reason}"

        data = response.json()
        articles = data.get("articles", [])
        if not articles:
            return 0.0, "No news found."
            
        scores = []
        for art in articles[:10]:
            text = f"{art.get('title', '')} {art.get('description', '')}"
            sentiment_score = TextBlob(text).sentiment.polarity
            scores.append(sentiment_score)
            
            st.session_state.analysis_logs.append({
                "Ticker": ticker,
                "Title": art.get('title', 'No Title')[:60],
                "Score": round(sentiment_score, 2)
            })
        return sum(scores) / len(scores), "Success"
        
    except Exception as e:
        return None, str(e)

def analyze_ticker(ticker, start_dt, end_dt):
    cur_rate = 3.64 # Fed Rate for April 2026
    sentiment, status = get_news_sentiment(ticker, NEWS_API_KEY, start_dt, end_dt)
    
    if sentiment is not None:
        final_score = sentiment + (0.05 if cur_rate < 4.0 else -0.05)
        if final_score > 0.10: rec, color = "BUY", "green"
        elif final_score < -0.10: rec, color = "SELL", "red"
        else: rec, color = "HOLD", "orange"
        
        st.session_state.results_data[ticker] = {
            "Score": round(final_score, 2), "Sentiment": round(sentiment, 2),
            "Recommendation": rec, "Color": color, "Status": status
        }
    else:
        st.session_state.results_data[ticker] = {"Status": status}

# --- Sidebar ---
with st.sidebar:
    st.header("📊 Control Center")
    
    # Quota Monitor
    q_rem = st.session_state.quota_info["remaining"]
    q_lim = st.session_state.quota_info["limit"]
    st.subheader("📡 API Quota Monitor")
    st.progress(q_rem / q_lim if q_lim > 0 else 0)
    st.caption(f"{q_rem} / {q_lim} requests remaining for today")
    if q_rem < 10:
        st.warning("⚠️ Critical: Low API quota remaining!")

    watchlist_input = st.text_area("Enter Tickers", "AAPL, NVDA, TSLA, SCHD")
    today = datetime.date.today()
    date_range = st.date_input("Analysis Window", value=(today - datetime.timedelta(days=7), today),
                               min_value=today - datetime.timedelta(days=30), max_value=today)
    
    if st.button("🔍 Run Full Analysis"):
        st.session_state.results_data = {}
        st.session_state.analysis_logs = []
        tickers = [t.strip().upper() for t in watchlist_input.split(",")]
        for t in tickers:
            analyze_ticker(t, date_range[0], date_range[1])

# --- Main App Execution ---
if st.session_state.results_data:
    df = pd.DataFrame.from_dict(st.session_state.results_data, orient='index').reset_index()
    df.rename(columns={'index': 'Ticker'}, inplace=True)
    
    # Filter only successful results for the chart
    valid_df = df[df['Status'] == "Success"]
    if not valid_df.empty:
        fig = px.bar(valid_df, x='Ticker', y='Score', color='Recommendation',
                     color_discrete_map={'BUY': '#2ecc71', 'HOLD': '#f1c40f', 'SELL': '#e74c3c'},
                     title="Weighted Scores (Sentiment + Macro Buffer)")
        st.plotly_chart(fig, use_container_width=True)

    # Display Deep-Dives
    for ticker, info in st.session_state.results_data.items():
        with st.expander(f"{ticker} — {info.get('Recommendation', 'ERROR')}"):
            if info['Status'] == "Success":
                st.metric("Score", info['Score'], delta=info['Sentiment'])
                st.write(f"Status: {info['Status']}")
            else:
                st.error(f"Error: {info['Status']}")
                if st.button(f"🔄 Retry {ticker}", key=f"retry_{ticker}"):
                    analyze_ticker(ticker, date_range[0], date_range[1])
                    st.rerun()

    with st.expander("📝 Raw Sentiment Log"):
        st.dataframe(pd.DataFrame(st.session_state.analysis_logs), hide_index=True)
else:
    st.info("👈 Enter tickers in the sidebar and run analysis to see results.")


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

# --- API Keys ---
# Ensure 'news_api_key' is set in Streamlit Cloud Secrets
NEWS_API_KEY = st.secrets.get("news_api_key")

# --- Logic Functions ---
def get_news_sentiment(ticker, api_key, start_date, end_date):
    """Fetches news and updates global rate limit quota with parsing safety."""
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
        
        # Capture Rate Limit Headers
        remaining = response.headers.get("X-RateLimit-Remaining")
        limit = response.headers.get("X-RateLimit-Limit")
        if remaining: st.session_state.quota_info["remaining"] = int(remaining)
        if limit: st.session_state.quota_info["limit"] = int(limit)

        # Safety Check: If not 200 OK, the API returned an HTML error or message
        if response.status_code != 200:
            return None, f"Error {response.status_code}: {response.reason}"

        # Safety Check: Attempt to parse JSON
        data = response.json()
        articles = data.get("articles", [])
        if not articles:
            return 0.0, "No news found for this ticker."
            
        scores = []
        for art in articles[:10]:
            title = art.get('title', 'No Title')
            text = f"{title} {art.get('description', '')}"
            sentiment_score = TextBlob(text).sentiment.polarity
            scores.append(sentiment_score)
            
            st.session_state.analysis_logs.append({
                "Ticker": ticker,
                "Title": title[:60],
                "Score": round(sentiment_score, 2)
            })
        
        avg_sentiment = sum(scores) / len(scores) if scores else 0.0
        return avg_sentiment, "Success"
        
    except requests.exceptions.JSONDecodeError:
        return None, "API returned HTML instead of JSON (likely a Cloud block)."
    except Exception as e:
        return None, f"System Error: {str(e)}"

def analyze_ticker(ticker, start_dt, end_dt):
    """Processes a single ticker with 2026 Macro context."""
    # April 2026 Macro Context: Fed Rate at 3.64%
    cur_rate = 3.64 
    sentiment, status = get_news_sentiment(ticker, NEWS_API_KEY, start_dt, end_dt)
    
    if sentiment is not None:
        # Final Score logic including Macro Buffer
        final_score = sentiment + (0.05 if cur_rate < 4.0 else -0.05)
        if final_score > 0.10: rec, color = "BUY", "green"
        elif final_score < -0.10: rec, color = "SELL", "red"
        else: rec, color = "HOLD", "orange"
        
        st.session_state.results_data[ticker] = {
            "Score": round(final_score, 2), 
            "Sentiment": round(sentiment, 2),
            "Recommendation": rec, 
            "Color": color, 
            "Status": status
        }
    else:
        st.session_state.results_data[ticker] = {"Status": status}

# --- Sidebar ---
with st.sidebar:
    st.header("📊 Control Center")
    
    # Quota Monitor Visual
    q_rem = st.session_state.quota_info["remaining"]
    q_lim = st.session_state.quota_info["limit"]
    st.subheader("📡 NewsAPI Quota")
    st.progress(q_rem / q_lim if q_lim > 0 else 0)
    st.caption(f"{q_rem} / {q_lim} calls left today")

    watchlist_input = st.text_area("Enter Tickers", "AAPL, NVDA, TSLA, SCHD")
    
    # Date Range (Free tier = 30 day history max)
    today = datetime.date.today()
    date_range = st.date_input("Analysis Window", 
                               value=(today - datetime.timedelta(days=7), today),
                               min_value=today - datetime.timedelta(days=30), 
                               max_value=today)
    
    if st.button("🔍 Run Full Analysis"):
        st.session_state.results_data = {}
        st.session_state.analysis_logs = []
        if len(date_range) == 2:
            start_dt, end_dt = date_range
            tickers = [t.strip().upper() for t in watchlist_input.split(",")]
            for t in tickers:
                analyze_ticker(t, start_dt, end_dt)
        else:
            st.error("Please select a valid start and end date.")

# --- Main App Execution ---
if not NEWS_API_KEY:
    st.warning("⚠️ NewsAPI Key missing! Go to App Settings -> Secrets and add 'news_api_key'.")
    st.stop()

if st.session_state.results_data:
    # Prepare Dataframe for Chart
    df = pd.DataFrame.from_dict(st.session_state.results_data, orient='index').reset_index()
    df.rename(columns={'index': 'Ticker'}, inplace=True)
    
    # Visualize Scores
    valid_df = df[df['Status'] == "Success"]
    if not valid_df.empty:
        st.subheader("📊 Sentiment vs Macro Baseline")
        fig = px.bar(valid_df, x='Ticker', y='Score', color='Recommendation',
                     color_discrete_map={'BUY': '#2ecc71', 'HOLD': '#f1c40f', 'SELL': '#e74c3c'})
        fig.add_hline(y=0.10, line_dash="dot", line_color="green", annotation_text="Bullish")
        fig.add_hline(y=-0.10, line_dash="dot", line_color="red", annotation_text="Bearish")
        st.plotly_chart(fig, use_container_width=True)

    # Individual Stock Cards
    st.subheader("🔍 Individual Analysis Deep-Dive")
    for ticker, info in st.session_state.results_data.items():
        with st.expander(f"{ticker} — {info.get('Recommendation', 'ERROR')}"):
            if info['Status'] == "Success":
                col1, col2 = st.columns(2)
                col1.metric("Final Score", info['Score'], delta=info['Sentiment'])
                col2.markdown(f"**Signal**: :{info['Color']}[{info['Recommendation']}]")
                st.write(f"**Context**: Analyzed against a 3.64% Fed Funds Rate baseline (April 2026).")
            else:
                st.error(f"Analysis Failed: {info['Status']}")
                if st.button(f"🔄 Retry {ticker}", key=f"retry_{ticker}"):
                    # Rerun only this ticker using the currently selected date range
                    start_dt, end_dt = date_range
                    analyze_ticker(ticker, start_dt, end_dt)
                    st.rerun()

    # Article Logs
    st.divider()
    with st.expander("📝 View Detailed Headline Sentiment Log"):
        if st.session_state.analysis_logs:
            st.dataframe(pd.DataFrame(st.session_state.analysis_logs), hide_index=True)
        else:
            st.write("No logs available.")
else:
    st.info("👈 Use the sidebar to enter tickers and click 'Run Full Analysis'.")


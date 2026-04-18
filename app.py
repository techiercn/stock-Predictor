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
    st.session_state.results_data = {} # Using dict for easy ticker updates
if 'analysis_logs' not in st.session_state:
    st.session_state.analysis_logs = []

# --- API Keys ---
NEWS_API_KEY = st.secrets.get("news_api_key")

# --- Logic Functions ---
def get_news_sentiment(ticker, api_key, start_date, end_date):
    """Fetches news and checks for common 403/429 errors."""
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
        
        # Handle NewsAPI specific errors (403 = Cloud/Auth, 429 = Rate Limit)
        if response.status_code != 200:
            return None, f"Error {response.status_code}: {response.reason}"

        data = response.json()
        articles = data.get("articles", [])
        if not articles:
            return 0.0, "No news found for this period."
            
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
        avg_sentiment = sum(scores) / len(scores)
        return avg_sentiment, "Success"
        
    except Exception as e:
        return None, str(e)

def analyze_ticker(ticker, start_dt, end_dt):
    """Main processing loop for a single ticker."""
    # Current Effective Fed Funds Rate as of April 2026 is ~3.64%
    cur_rate = 3.64 
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
    watchlist_input = st.text_area("Enter Tickers", "AAPL, NVDA, TSLA, SCHD")
    
    # NewsAPI 30-day limit
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
    
    # Charting
    valid_df = df[df['Status'] == "Success"]
    if not valid_df.empty:
        fig = px.bar(valid_df, x='Ticker', y='Score', color='Recommendation',
                     color_discrete_map={'BUY': '#2ecc71', 'HOLD': '#f1c40f', 'SELL': '#e74c3c'})
        st.plotly_chart(fig, use_container_width=True)

    # Individual Ticker Cards with "Try Again"
    st.subheader("🔍 Stock Analysis Cards")
    for ticker, info in st.session_state.results_data.items():
        with st.expander(f"{ticker} — {info.get('Recommendation', 'FAILED')}"):
            if info['Status'] == "Success":
                st.metric("Final Weighted Score", info['Score'], delta=info['Sentiment'])
                st.write(f"**Recommendation**: :{info['Color']}[{info['Recommendation']}]")
            else:
                st.error(f"Analysis Failed: {info['Status']}")
                if st.button(f"🔄 Retry {ticker}", key=f"retry_{ticker}"):
                    analyze_ticker(ticker, date_range[0], date_range[1])
                    st.rerun()

    # Log View
    with st.expander("📝 Article Sentiment Log"):
        st.dataframe(pd.DataFrame(st.session_state.analysis_logs), hide_index=True)
else:
    st.info("Enter tickers and click 'Run Full Analysis' to begin.")


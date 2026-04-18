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
    st.session_state.results_data = None
if 'analysis_logs' not in st.session_state:
    st.session_state.analysis_logs = []

# --- API Keys ---
NEWS_API_KEY = st.secrets.get("news_api_key")

# --- Logic Functions ---
def get_news_sentiment(ticker, api_key, start_date, end_date):
    """Fetches news with date filtering and safe param building."""
    base_url = "https://newsapi.org"
    
    # ISO 8601 formatting for NewsAPI
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
        data = response.json()
        
        if data.get("status") == "ok" and data.get("totalResults", 0) > 0:
            articles = data["articles"][:10]
            scores = []
            for art in articles:
                title = art.get('title', 'No Title')
                text = f"{title} {art.get('description', '')}"
                sentiment_score = TextBlob(text).sentiment.polarity
                scores.append(sentiment_score)
                
                st.session_state.analysis_logs.append({
                    "Ticker": ticker,
                    "Title": title[:60],
                    "Score": round(sentiment_score, 2)
                })
            return sum(scores) / len(scores) if scores else 0.0
        return 0.0
    except Exception as e:
        st.sidebar.error(f"⚠️ {ticker} Error: {str(e)}")
        return 0.0

def get_recommendation(score):
    if score > 0.10: return "BUY", "green", "Bullish sentiment relative to 2026 baseline."
    if score < -0.10: return "SELL", "red", "Bearish cycle or high interest rate pressure."
    return "HOLD", "orange", "Mixed sentiment or neutral macro data."

# --- Sidebar ---
with st.sidebar:
    st.header("📊 Control Center")
    watchlist = st.text_area("Enter Tickers", "AAPL, NVDA, TSLA, SCHD")
    
    # Date Range Selector
    # Note: NewsAPI free tier limits to last 30 days
    today = datetime.date.today()
    thirty_days_ago = today - datetime.timedelta(days=30)
    
    st.subheader("📅 Analysis Window")
    date_range = st.date_input(
        "Select Range",
        value=(today - datetime.timedelta(days=7), today),
        min_value=thirty_days_ago,
        max_value=today
    )
    
    scan_btn = st.button("🔍 Run Full Analysis")
    
    st.divider()
    st.subheader("📝 Live Sentiment Log")
    with st.expander("View Article Scores"):
        if st.session_state.analysis_logs:
            st.dataframe(pd.DataFrame(st.session_state.analysis_logs), hide_index=True)

# --- Main App Execution ---
if not NEWS_API_KEY:
    st.warning("⚠️ NewsAPI Key missing! Add 'news_api_key' to your Secrets.")
    st.stop()

# Actual April 2026 Macro Data
# Effective Fed Funds Rate is currently holding steady at ~3.64%
cur_rate = 3.64 

if scan_btn and len(date_range) == 2:
    st.session_state.analysis_logs = [] 
    start_dt, end_dt = date_range
    tickers = [t.strip().upper() for t in watchlist.split(",")]
    temp_results = []
    
    with st.status(f"Scanning 2026 news ({start_dt} to {end_dt})...") as status:
        for s in tickers:
            sentiment = get_news_sentiment(s, NEWS_API_KEY, start_dt, end_dt)
            final_score = sentiment + (0.05 if cur_rate < 4.0 else -0.05)
            rec, color, reason = get_recommendation(final_score)
            
            temp_results.append({
                "Ticker": s, "Score": round(final_score, 2), 
                "Sentiment": round(sentiment, 2), "Recommendation": rec, 
                "Color": color, "Reason": reason
            })
            time.sleep(0.2)
        status.update(label="Analysis Complete!", state="complete")
    st.session_state.results_data = temp_results

# --- Visuals ---
if st.session_state.results_data:
    df = pd.DataFrame(st.session_state.results_data)
    
    st.subheader("📊 Weighted Score Analysis")
    fig = px.bar(df, x='Ticker', y='Score', color='Recommendation',
                 color_discrete_map={'BUY': '#2ecc71', 'HOLD': '#f1c40f', 'SELL': '#e74c3c'})
    fig.add_hline(y=0.10, line_dash="dot", line_color="green")
    fig.add_hline(y=-0.10, line_dash="dot", line_color="red")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🔍 Deep-Dive Reports")
    for item in st.session_state.results_data:
        with st.expander(f"{item['Ticker']} — {item['Recommendation']}"):
            st.metric("Sentiment Score", f"{item['Score']} / 1.0", delta=item['Sentiment'])
            st.write(f"**Rationale**: {item['Reason']}")
            st.caption(f"Macro Buffer: +0.05 (Fed Rate {cur_rate}% < 4.0% threshold)")

    st.divider()
    st.dataframe(df.drop(columns=['Color']), use_container_width=True)


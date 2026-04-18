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
def get_news_sentiment(ticker, api_key):
    """Fetches news using a params dictionary to prevent URL formatting errors."""
    # This is the stable base URL
    base_url = "https://newsapi.org/v2/everything"
    
    # Let the requests library handle the formatting
    params = {
        "q": ticker,
        "language": "en",
        "sortBy": "relevancy",
        "apiKey": api_key
    }
    
    try:
        # requests.get combines the URL and params perfectly
        response = requests.get(base_url, params=params, timeout=10)
        data = response.json()
        
        if data.get("status") == "ok" and data.get("totalResults", 0) > 0:
            articles = data["articles"][:10]
            scores = []
            for art in articles:
                text = f"{art.get('title', '')} {art.get('description', '')}"
                sentiment_score = TextBlob(text).sentiment.polarity
                scores.append(sentiment_score)
                
                # Log entry for the sidebar
                st.session_state.analysis_logs.append({
                    "Ticker": ticker,
                    "Title": art.get('title', 'No Title')[:60],
                    "Score": round(sentiment_score, 2)
                })
            return sum(scores) / len(scores) if scores else 0.0
        return 0.0
    except Exception as e:
        # Use a sidebar error so it doesn't break the main dashboard
        st.sidebar.error(f"⚠️ {ticker} URL Error: {str(e)}")
        return 0.0


def get_recommendation(score):
    if score > 0.10: return "BUY", "green", "Positive sentiment + macro tailwinds."
    if score < -0.10: return "SELL", "red", "Negative news cycle or macro pressure."
    return "HOLD", "orange", "Mixed signals in news and macro data."

# --- Sidebar ---
with st.sidebar:
    st.header("📊 Control Center")
    watchlist = st.text_area("Enter Tickers", "AAPL, NVDA, TSLA, SCHD")
    scan_btn = st.button("🔍 Run Full Analysis")
    
    st.divider()
    st.subheader("📝 Live Analysis Log")
    with st.expander("View Article Sentiment Scores"):
        if st.session_state.analysis_logs:
            log_df = pd.DataFrame(st.session_state.analysis_logs)
            st.dataframe(log_df, use_container_width=True, hide_index=True)
        else:
            st.write("No data processed yet.")

# --- Main App Execution ---
if not NEWS_API_KEY:
    st.warning("⚠️ NewsAPI Key missing! Add 'news_api_key' to your Secrets.")
    st.stop()

# 2026 Macro Context
cur_rate = 3.64 

if scan_btn:
    st.session_state.analysis_logs = [] # Clear old logs
    tickers = [t.strip().upper() for t in watchlist.split(",")]
    temp_results = []
    
    with st.status("Analyzing 2026 Global Intelligence...") as status:
        for s in tickers:
            sentiment = get_news_sentiment(s, NEWS_API_KEY)
            
            # Weighted Score calculation
            final_score = sentiment + (0.05 if cur_rate < 4.0 else -0.05)
            rec, color, reason = get_recommendation(final_score)
            
            temp_results.append({
                "Ticker": s, "Score": round(final_score, 2), 
                "Sentiment": round(sentiment, 2), "Recommendation": rec, 
                "Color": color, "Reason": reason
            })
            st.write(f"✅ {s}: Sentiment processed.")
            time.sleep(0.2)
        status.update(label="Analysis Complete!", state="complete")
    st.session_state.results_data = temp_results

# --- Visuals & Reports ---
if st.session_state.results_data:
    df = pd.DataFrame(st.session_state.results_data)
    
    st.subheader("📊 Sentiment vs Baseline")
    fig = px.bar(df, x='Ticker', y='Score', color='Recommendation',
                 color_discrete_map={'BUY': '#2ecc71', 'HOLD': '#f1c40f', 'SELL': '#e74c3c'})
    fig.add_hline(y=0.10, line_dash="dot", line_color="green", annotation_text="Bullish")
    fig.add_hline(y=-0.10, line_dash="dot", line_color="red", annotation_text="Bearish")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🔍 Deep-Dive Reports")
    cols = st.columns(len(st.session_state.results_data))
    for i, item in enumerate(st.session_state.results_data):
        with cols[i]:
            st.metric(item['Ticker'], item['Recommendation'], delta=item['Score'])
            st.caption(item['Reason'])

    st.divider()
    st.dataframe(df.drop(columns=['Color']), use_container_width=True)


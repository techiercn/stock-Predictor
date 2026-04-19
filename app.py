import streamlit as st
import pandas as pd
import requests
import datetime
import time
import plotly.express as px

# --- Page Config ---
st.set_page_config(page_title="2026 Macro Stock Pro", layout="wide")
st.title("📈 AI Stock Pro: 2026 Macro-Adjusted Edition")

# --- Initialize Session State ---
if 'results_data' not in st.session_state:
    st.session_state.results_data = {}
if 'daily_usage' not in st.session_state:
    st.session_state.daily_usage = 0

AV_API_KEY = st.secrets.get("av_api_key")

# --- Logic Functions ---
def get_av_sentiment_with_retry(ticker, api_key, retries=3):
    """Fetches sentiment with automatic retries for 'char 0' empty responses."""
    url = "https://alphavantage.co"
    params = {"function": "NEWS_SENTIMENT", "tickers": ticker, "apikey": api_key, "limit": 5}
    
    for i in range(retries):
        try:
            response = requests.get(url, params=params, timeout=15)
            st.session_state.daily_usage += 1
            
            # Check for empty response (The 'char 0' culprit)
            if not response.text or response.text.strip() == "":
                if i < retries - 1:
                    wait_time = (i + 1) * 5
                    st.warning(f"⚠️ Empty response for {ticker}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                return None, "Empty response after retries (Cloud IP Rate Limit)."

            data = response.json()
            
            # Check for API limit messages
            if "Information" in data or "Note" in data:
                return None, "API Limit: " + (data.get("Information") or data.get("Note"))
            
            feed = data.get("feed", [])
            if not feed: return 0.0, "No news found."
            
            scores = [float(s.get("ticker_sentiment_score", 0)) 
                      for art in feed for s in art.get("ticker_sentiment", []) 
                      if s.get("ticker") == ticker]
            
            return (sum(scores) / len(scores)) if scores else 0.0, "Success"
            
        except Exception as e:
            if i < retries - 1:
                time.sleep(5)
                continue
            return None, f"Connection Error: {str(e)}"
    return None, "Maximum retries reached."

def analyze_ticker(ticker, fed_rate, geo_penalty):
    sentiment, status = get_av_sentiment_with_retry(ticker, AV_API_KEY)
    
    if sentiment is not None:
        rate_penalty = (fed_rate - 3.50) * 0.08
        final_score = sentiment - rate_penalty - geo_penalty
        
        if final_score > 0.15: rec, color, reason = "BUY", "green", "Bullish sentiment + favorable macro."
        elif final_score < -0.15: rec, color, reason = "SELL", "red", "Bearish sentiment or macro pressure."
        else: rec, color, reason = "HOLD", "orange", "Neutral or conflicting signals."
        
        st.session_state.results_data[ticker] = {
            "Score": round(final_score, 2), "Sentiment": round(sentiment, 2),
            "Recommendation": rec, "Color": color, "Status": status, "Reason": reason
        }
    else:
        st.session_state.results_data[ticker] = {"Status": status}

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Macro Controls")
    st.metric("Calls Today", f"{st.session_state.daily_usage}/25")
    fed_rate = st.slider("Fed Funds Rate (%)", 0.0, 10.0, 3.64, 0.25)
    risks = st.multiselect("Geopolitical Risks", 
                          ["Strait of Hormuz Closure", "NATO-Russia Escalation", "US-China Trade War"],
                          default=["Strait of Hormuz Closure"])
    geo_penalty = len(risks) * 0.10
    
    st.divider()
    watchlist = st.text_area("Tickers", "AAPL, NVDA, TSLA")
    queue_status = st.empty()
    scan_btn = st.button("🔍 Run Full Analysis")

# --- Execution ---
if scan_btn:
    tickers = [t.strip().upper() for t in watchlist.split(",")]
    st.session_state.results_data = {}
    
    for i, t in enumerate(tickers):
        with st.spinner(f"Analyzing {t}..."):
            analyze_ticker(t, fed_rate, geo_penalty)
        if i < len(tickers) - 1:
            for rem in range(15, 0, -1): # Increased to 15s for cloud stability
                queue_status.warning(f"⏳ Cooldown: Next scan in {rem}s...")
                time.sleep(1)
    queue_status.success("✅ Complete!")
    st.rerun()

# --- UI ---
if st.session_state.results_data:
    df = pd.DataFrame.from_dict(st.session_state.results_data, orient='index').reset_index()
    df.rename(columns={'index': 'Ticker'}, inplace=True)
    valid_df = df[df['Status'] == "Success"]
    
    if not valid_df.empty:
        st.plotly_chart(px.bar(valid_df, x='Ticker', y='Score', color='Recommendation',
                               color_discrete_map={'BUY': '#2ecc71', 'HOLD': '#f1c40f', 'SELL': '#e74c3c'}))

    for ticker, info in st.session_state.results_data.items():
        with st.expander(f"{ticker} — {info.get('Recommendation', 'ERROR')}"):
            if info['Status'] == "Success":
                st.metric("Adjusted Score", info['Score'], delta=info['Sentiment'])
                st.markdown(f"**Signal**: :{info['Color']}[{info['Recommendation']}]")
                st.write(info['Reason'])
            else:
                st.error(f"Failed: {info['Status']}")


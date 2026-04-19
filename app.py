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
def get_av_sentiment(ticker, api_key):
    url = "https://alphavantage.co"
    params = {"function": "NEWS_SENTIMENT", "tickers": ticker, "apikey": api_key, "limit": 5}
    try:
        response = requests.get(url, params=params, timeout=15)
        st.session_state.daily_usage += 1
        
        if not response.text:
            return None, "Empty response (Likely soft-blocked)."
        
        data = response.json()
        if "Information" in data or "Note" in data:
            return None, "API Limit: " + (data.get("Information") or data.get("Note"))
        
        feed = data.get("feed", [])
        if not feed: return 0.0, "No news found."
        
        scores = [float(s.get("ticker_sentiment_score", 0)) 
                  for art in feed for s in art.get("ticker_sentiment", []) 
                  if s.get("ticker") == ticker]
        
        return (sum(scores) / len(scores)), "Success" if scores else (0.0, "No ticker sentiment.")
    except Exception as e:
        return None, f"Connection Error: {str(e)}"

def analyze_ticker(ticker, fed_rate, geo_penalty):
    sentiment, status = get_av_sentiment(ticker, AV_API_KEY)
    if sentiment is not None:
        rate_penalty = (fed_rate - 3.50) * 0.08
        final_score = sentiment - rate_penalty - geo_penalty
        
        rec, color = ("BUY", "green") if final_score > 0.15 else (("SELL", "red") if final_score < -0.15 else ("HOLD", "orange"))
        
        st.session_state.results_data[ticker] = {
            "Score": round(final_score, 2), "Sentiment": round(sentiment, 2),
            "Recommendation": rec, "Color": color, "Status": status
        }
    else:
        st.session_state.results_data[ticker] = {"Status": status}

# --- Sidebar Controls ---
with st.sidebar:
    st.header("⚙️ Macro Controls")
    st.metric("Daily Usage", f"{st.session_state.daily_usage}/25")
    
    fed_rate = st.slider("Fed Funds Rate (%)", 0.0, 10.0, 3.64, 0.25)
    risks = st.multiselect("Geopolitical Risks", 
                          ["Strait of Hormuz Closure", "NATO-Russia Escalation", "US-China Trade War"],
                          default=["Strait of Hormuz Closure"])
    geo_penalty = len(risks) * 0.10
    
    st.divider()
    watchlist = st.text_area("Tickers", "AAPL, NVDA, TSLA")
    
    # --- The Queue System ---
    queue_placeholder = st.empty()
    scan_btn = st.button("🔍 Run Analysis Queue")

# --- Execution Loop ---
if scan_btn:
    if not AV_API_KEY:
        st.error("Missing API Key")
    else:
        tickers = [t.strip().upper() for t in watchlist.split(",")]
        st.session_state.results_data = {}
        
        for i, t in enumerate(tickers):
            with st.spinner(f"Analyzing {t}..."):
                analyze_ticker(t, fed_rate, geo_penalty)
            
            # If not the last ticker, start the 12-second cooldown
            if i < len(tickers) - 1:
                for remaining in range(12, 0, -1):
                    queue_placeholder.warning(f"⏳ Rate Limit Cooldown: Next scan in {remaining}s...")
                    time.sleep(1)
        
        queue_placeholder.success("✅ Analysis Queue Complete!")
        st.rerun()

# --- Display UI ---
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
                st.metric("Final Score", info['Score'], delta=info['Sentiment'])
            else:
                st.error(info['Status'])


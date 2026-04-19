import streamlit as st
import pandas as pd
import requests
import datetime
import time
import plotly.express as px

# --- Page Config ---
st.set_page_config(page_title="2026 Macro Stock Pro", layout="wide")
st.title("📈 AI Stock Pro: 2026 Alpha Vantage Edition")

# --- Initialize Session State ---
if 'results_data' not in st.session_state:
    st.session_state.results_data = {}
if 'daily_calls' not in st.session_state:
    st.session_state.daily_calls = 0

AV_API_KEY = st.secrets.get("av_api_key")

# --- Logic Functions ---
def get_av_sentiment(ticker, api_key):
    """Fetches sentiment with safety checks for empty/non-JSON responses."""
    url = "https://alphavantage.co"
    params = {"function": "NEWS_SENTIMENT", "tickers": ticker, "apikey": api_key, "limit": 5}
    
    try:
        response = requests.get(url, params=params, timeout=15)
        st.session_state.daily_calls += 1
        
        if not response.text or response.text.strip() == "":
            return None, "Empty response (Likely rate limited)."

        if response.status_code != 200:
            return None, f"HTTP {response.status_code}: {response.reason}"

        try:
            data = response.json()
        except Exception:
            return None, "Server sent non-JSON data (Check daily 25-call limit)."

        if "Information" in data or "Note" in data:
            return None, f"API Notice: {data.get('Information') or data.get('Note')}"

        feed = data.get("feed", [])
        if not feed:
            return 0.0, "No news found."

        ticker_scores = [
            float(s.get("ticker_sentiment_score", 0))
            for art in feed
            for s in art.get("ticker_sentiment", [])
            if s.get("ticker") == ticker
        ]
        
        return (sum(ticker_scores) / len(ticker_scores)), "Success" if ticker_scores else (0.0, "No ticker sentiment in feed.")
        
    except Exception as e:
        return None, f"System Error: {str(e)}"

def analyze_ticker(ticker):
    """Processes ticker with April 2026 Macro context."""
    cur_rate = 3.64 # Fed Funds Rate baseline for April 2026
    sentiment, status = get_av_sentiment(ticker, AV_API_KEY)
    
    if sentiment is not None:
        final_score = sentiment + 0.05 # Macro tailwind for rates < 4.0%
        if final_score > 0.15: rec, color = "BUY", "green"
        elif final_score < -0.15: rec, color = "SELL", "red"
        else: rec, color = "HOLD", "orange"
        
        st.session_state.results_data[ticker] = {
            "Score": round(final_score, 2), "Sentiment": round(sentiment, 2),
            "Recommendation": rec, "Color": color, "Status": status
        }
    else:
        st.session_state.results_data[ticker] = {"Status": status}

# --- Sidebar ---
with st.sidebar:
    st.header("📊 Controls")
    
    # Quota Tracker
    st.write(f"**Calls Today:** {st.session_state.daily_calls} / 25")
    st.progress(min(st.session_state.daily_calls / 25, 1.0))
    
    watchlist = st.text_area("Enter Tickers (max 4-5 recommended)", "AAPL, NVDA, TSLA")
    scan_btn = st.button("🔍 Run Full Analysis")
    
    countdown_placeholder = st.empty()

# --- Main App Logic ---
if not AV_API_KEY:
    st.warning("⚠️ API Key missing! Add 'av_api_key' to Secrets.")
    st.stop()

if scan_btn:
    tickers = [t.strip().upper() for t in watchlist.split(",")]
    st.session_state.results_data = {}
    
    with st.status("Fetching Market Intelligence...") as status:
        for i, t in enumerate(tickers):
            analyze_ticker(t)
            st.write(f"✅ {t} Processed.")
            
            # Rate Limit Countdown
            if i < len(tickers) - 1:
                for remaining in range(12, 0, -1):
                    countdown_placeholder.metric("Next Scan In...", f"{remaining}s")
                    time.sleep(1)
                countdown_placeholder.empty()
                
        status.update(label="Analysis Complete!", state="complete")

# --- UI Display ---
if st.session_state.results_data:
    df = pd.DataFrame.from_dict(st.session_state.results_data, orient='index').reset_index()
    df.rename(columns={'index': 'Ticker'}, inplace=True)
    
    valid_df = df[df['Status'] == "Success"]
    if not valid_df.empty:
        st.plotly_chart(px.bar(valid_df, x='Ticker', y='Score', color='Recommendation',
                               color_discrete_map={'BUY': '#2ecc71', 'HOLD': '#f1c40f', 'SELL': '#e74c3c'}))

    st.subheader("🔍 Individual Analysis Deep-Dive")
    for ticker, info in st.session_state.results_data.items():
        with st.expander(f"{ticker} — {info.get('Recommendation', 'ERROR')}"):
            if info['Status'] == "Success":
                st.metric("Weighted Score", info['Score'], delta=info['Sentiment'])
                st.write(f"Signal: :{info['Color']}[{info['Recommendation']}]")
                st.caption(f"Fed Funds Rate: 3.64% (April 2026)")
            else:
                st.error(f"Reason: {info['Status']}")


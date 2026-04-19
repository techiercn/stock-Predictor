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

AV_API_KEY = st.secrets.get("av_api_key")

def get_av_sentiment(ticker, api_key):
    """Fetches sentiment with safety checks for empty/non-JSON responses."""
    url = "https://www.alphavantage.co/query"
    params = {"function": "NEWS_SENTIMENT", "tickers": ticker, "apikey": api_key, "limit": 5}
    
    try:
        response = requests.get(url, params=params, timeout=15)
        
        # Check if response is empty (causes the char 0 error)
        if not response.text or response.text.strip() == "":
            return None, "Empty response from API (Likely rate limited)."

        # Check status code
        if response.status_code != 200:
            return None, f"HTTP {response.status_code}: {response.reason}"

        # Attempt JSON parsing safely
        try:
            data = response.json()
        except Exception:
            return None, "Server sent non-JSON data (Check your daily limit)."

        # Handle API warning/info messages
        if "Information" in data or "Note" in data:
            return None, f"API Notice: {data.get('Information') or data.get('Note')}"

        feed = data.get("feed", [])
        if not feed:
            return 0.0, "No recent news found."

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
    """Processes ticker with 2026 Macro context."""
    cur_rate = 3.64 # Fed Funds Rate as of mid-April 2026
    sentiment, status = get_av_sentiment(ticker, AV_API_KEY)
    
    if sentiment is not None:
        # Buffer: +0.05 because rates (3.64%) are below the 4.0% restrictive threshold
        final_score = sentiment + 0.05
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
    watchlist = st.text_area("Enter Tickers", "AAPL, NVDA, TSLA")
    
    if st.button("🔍 Run Full Analysis"):
        tickers = [t.strip().upper() for t in watchlist.split(",")]
        # Clear logs to avoid clutter
        st.session_state.results_data = {}
        
        with st.status("Fetching Market Intelligence...") as status:
            for i, t in enumerate(tickers):
                analyze_ticker(t)
                st.write(f"✅ {t} Processed.")
                # STRICT RATE LIMIT: 5 requests per minute = 12 sec delay
                if i < len(tickers) - 1:
                    time.sleep(12) 
            status.update(label="Analysis Complete!", state="complete")

# --- UI ---
if st.session_state.results_data:
    df = pd.DataFrame.from_dict(st.session_state.results_data, orient='index').reset_index()
    df.rename(columns={'index': 'Ticker'}, inplace=True)
    
    valid_df = df[df['Status'] == "Success"]
    if not valid_df.empty:
        st.plotly_chart(px.bar(valid_df, x='Ticker', y='Score', color='Recommendation',
                               color_discrete_map={'BUY': '#2ecc71', 'HOLD': '#f1c40f', 'SELL': '#e74c3c'}))

    for ticker, info in st.session_state.results_data.items():
        with st.expander(f"{ticker} — {info.get('Status', 'ERROR')}"):
            if info['Status'] == "Success":
                st.metric("Weighted Score", info['Score'], delta=info['Sentiment'])
                st.write(f"Signal: :{info['Color']}[{info['Recommendation']}]")
            else:
                st.error(f"Reason: {info['Status']}")


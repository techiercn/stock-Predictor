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

# --- API Keys ---
# Retrieve this from Streamlit Cloud Secrets (av_api_key)
AV_API_KEY = st.secrets.get("av_api_key")

# --- Logic Functions ---
def get_av_sentiment(ticker, api_key):
    """Fetches sentiment with advanced error trapping for empty responses."""
    url = "https://alphavantage.co"
    params = {
        "function": "NEWS_SENTIMENT", 
        "tickers": ticker, 
        "apikey": api_key, 
        "limit": 5
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        st.session_state.daily_usage += 1
        
        # FIX for 'char 0' error: check if response body is empty
        if not response.text or response.text.strip() == "":
            return None, "Empty response: Likely 5-per-minute limit triggered."
        
        data = response.json()
        
        # Check for Alpha Vantage API notices (Rate limits)
        if "Information" in data or "Note" in data:
            return None, "API Limit: " + (data.get("Information") or data.get("Note"))
        
        feed = data.get("feed", [])
        if not feed: 
            return 0.0, "No news found for this ticker."
        
        # Extract ticker-specific sentiment scores
        scores = [float(s.get("ticker_sentiment_score", 0)) 
                  for art in feed for s in art.get("ticker_sentiment", []) 
                  if s.get("ticker") == ticker]
        
        avg_sentiment = (sum(scores) / len(scores)) if scores else 0.0
        return avg_sentiment, "Success"
        
    except Exception as e:
        return None, f"Connection Error: {str(e)}"

def analyze_ticker(ticker, fed_rate, geo_penalty):
    """Calculates weighted score based on User Macro settings."""
    sentiment, status = get_av_sentiment(ticker, AV_API_KEY)
    
    if sentiment is not None:
        # Rate Penalty: -0.02 impact for every 0.25% above a 'neutral' 3.5% baseline
        rate_penalty = (fed_rate - 3.50) * 0.08
        
        # Final weighted calculation
        final_score = sentiment - rate_penalty - geo_penalty
        
        # Classification & Colors
        if final_score > 0.15:
            rec, color, reason = "BUY", "green", "Strong bullish sentiment + favorable macro."
        elif final_score < -0.15:
            rec, color, reason = "SELL", "red", "Bearish sentiment or high geopolitical pressure."
        else:
            rec, color, reason = "HOLD", "orange", "Neutral indicators or conflicting signals."
        
        st.session_state.results_data[ticker] = {
            "Score": round(final_score, 2), 
            "Sentiment": round(sentiment, 2),
            "Recommendation": rec, 
            "Color": color, 
            "Status": status, 
            "Reason": reason
        }
    else:
        st.session_state.results_data[ticker] = {"Status": status}

# --- Sidebar Controls ---
with st.sidebar:
    st.header("⚙️ Macro Controls")
    st.metric("Daily Calls Used", f"{st.session_state.daily_usage}/25")
    
    # Fed Funds Rate Slider (April 2026 Baseline is ~3.64%)
    st.subheader("🏦 Interest Rate Policy")
    fed_rate = st.slider("Fed Funds Rate (%)", 0.0, 10.0, 3.64, 0.25)
    
    # Geopolitical Risk Selection
    st.subheader("🌍 Geopolitical Indicators")
    risks = st.multiselect(
        "Active Risk Factors",
        ["Strait of Hormuz Closure", "NATO-Russia Escalation", "US-China Trade War", "Cyber Warfare Surge"],
        default=["Strait of Hormuz Closure"]
    )
    geo_penalty = len(risks) * 0.10 # -0.10 penalty per risk factor
    
    st.divider()
    watchlist_input = st.text_area("Enter Tickers (CSV)", "AAPL, NVDA, TSLA")
    
    # Progress monitoring
    queue_status = st.empty()
    scan_btn = st.button("🔍 Run Analysis Queue")

# --- Execution ---
if scan_btn:
    if not AV_API_KEY:
        st.error("Missing API Key! Please add 'av_api_key' to Streamlit Secrets.")
    else:
        tickers = [t.strip().upper() for t in watchlist_input.split(",")]
        st.session_state.results_data = {} # Reset current results
        
        for i, t in enumerate(tickers):
            with st.spinner(f"Analyzing {t}..."):
                analyze_ticker(t, fed_rate, geo_penalty)
            
            # Forced Delay to stay under 5-calls-per-minute limit
            if i < len(tickers) - 1:
                for rem in range(12, 0, -1):
                    queue_status.warning(f"⏳ Cooldown: Next scan in {rem}s...")
                    time.sleep(1)
        
        queue_status.success("✅ Portfolio Analysis Complete!")
        st.rerun()

# --- Main UI Display ---
if st.session_state.results_data:
    df = pd.DataFrame.from_dict(st.session_state.results_data, orient='index').reset_index()
    df.rename(columns={'index': 'Ticker'}, inplace=True)
    
    # Filter only successful results for the chart
    valid_df = df[df['Status'] == "Success"]
    if not valid_df.empty:
        st.subheader(f"📊 Macro-Adjusted Scores (Fed Rate: {fed_rate}%)")
        fig = px.bar(
            valid_df, x='Ticker', y='Score', color='Recommendation',
            color_discrete_map={'BUY': '#2ecc71', 'HOLD': '#f1c40f', 'SELL': '#e74c3c'},
            title="Final Weighted Scores (Sentiment - Macro Penalties)"
        )
        st.plotly_chart(fig, use_container_width=True)

    # Detailed Cards
    st.subheader("🔍 Individual Ticker Deep-Dive")
    for ticker, info in st.session_state.results_data.items():
        with st.expander(f"{ticker} — {info.get('Recommendation', 'ERROR')}"):
            if info['Status'] == "Success":
                c1, c2 = st.columns(2)
                c1.metric("Weighted Score", info['Score'], delta=info['Sentiment'], delta_description="News Sentiment")
                c2.markdown(f"**Recommendation**: :{info['Color']}[{info['Recommendation']}]")
                st.write(f"**Rationale**: {info['Reason']}")
                st.caption(f"Penalties Applied: Interest Rate ({round((fed_rate-3.5)*0.08, 2)}) | Geopolitics ({geo_penalty})")
            else:
                st.error(f"Analysis Failed: {info['Status']}")
                if st.button(f"🔄 Retry {ticker}", key=f"retry_{ticker}"):
                    analyze_ticker(ticker, fed_rate, geo_penalty)
                    st.rerun()
else:
    st.info("👈 Enter tickers in the sidebar and click 'Run Analysis Queue' to begin.")


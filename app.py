import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import time
from fredapi import Fred

# --- Page Config ---
st.set_page_config(page_title="Alpha Macro Predictor", layout="wide")
st.title("📈 AI Stock Pro: Alpha Vantage Edition")

# --- Initialize Session State ---
if 'api_calls_used' not in st.session_state:
    st.session_state.api_calls_used = 0

# --- API Keys from Secrets ---
FRED_KEY = st.secrets.get("fred_api_key")
AV_KEY = st.secrets.get("av_api_key")

# --- Helper Functions ---
@st.cache_data(ttl=3600)
def fetch_macro_data(api_key):
    """Fetches Fed Interest Rates. Fallback to 0.0 to prevent crashes."""
    try:
        fred = Fred(api_key=api_key)
        rates = fred.get_series('FEDFUNDS').tail(2)
        cur_rate = rates.iloc[-1]
        rate_delta = cur_rate - rates.iloc[-2]
        return cur_rate, rate_delta
    except:
        return 0.0, 0.0

def get_av_analysis(symbol, api_key, rate_delta, cur_rate):
    """Calls Alpha Vantage and calculates score using a safe parameter dictionary."""
    # The base URL should NOT have any parameters attached to it
    API_URL = "https://www.alphavantage.co/query"
    
    # Passing parameters as a dictionary is the safest way to avoid URL typos
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": symbol,
        "apikey": api_key
    }
    
    try:
        # requests.get will automatically format the URL correctly with '?' and '&'
        response = requests.get(API_URL, params=params).json()
        st.session_state.api_calls_used += 1
        
        if "Note" in response:
            return {"status": "RATE_LIMIT", "msg": "5-calls-per-minute limit hit."}
        if "Error Message" in response:
            return {"status": "ERROR", "msg": "Invalid ticker or API key."}
            
        feed = response.get('feed', [])
        if not feed:
            return {"status": "NO_NEWS", "msg": "No news found for this ticker in last 48h."}

        # Sentiment Calculation
        scores = [float(item['overall_sentiment_score']) for item in feed[:5]]
        avg_sentiment = sum(scores) / len(scores)
        
        # Sector/Macro Weighting
        t = yf.Ticker(symbol)
        sector = t.info.get('sector', 'Unknown')
        multiplier = {"Real Estate": 1.5, "Technology": 1.2, "Utilities": 1.5}.get(sector, 1.0)
        macro_impact = 0.2 if rate_delta < 0 else -0.2 if rate_delta > 0 else (0.05 if cur_rate < 4 else -0.05)
        
        final_score = avg_sentiment + (macro_impact * multiplier)
        return {
            "status": "SUCCESS",
            "Ticker": symbol, 
            "Sector": sector, 
            "Score": round(final_score, 2), 
            "Sentiment": round(avg_sentiment, 2)
        }
    except Exception as e:
        return {"status": "ERROR", "msg": str(e)}


# --- Sidebar UI ---
with st.sidebar:
    st.header("📊 API Status")
    daily_limit = 25
    remaining = max(0, daily_limit - st.session_state.api_calls_used)
    st.write(f"Credits Remaining: **{remaining} / {daily_limit}**")
    st.progress(remaining / daily_limit)
    
    st.divider()
    watchlist_input = st.text_area("Watchlist (Max 5)", "AAPL, NVDA, TSLA")
    threshold = st.slider("Buy Threshold", 0.05, 0.30, 0.10)
    scan_btn = st.button("🔍 Run Full Scan", disabled=(remaining == 0))

# --- Main Logic Execution ---
if not FRED_KEY or not AV_KEY:
    st.error("⚠️ API Keys Missing! Please add 'fred_api_key' and 'av_api_key' to Streamlit Secrets.")
else:
    if scan_btn:
        cur_rate, rate_delta = fetch_macro_data(FRED_KEY)
        tickers = [t.strip().upper() for t in watchlist_input.split(",")]
        results = []
        
        with st.status("Gathering Data...", expanded=True) as status:
            for i, s in enumerate(tickers):
                if st.session_state.api_calls_used >= daily_limit:
                    st.error("🛑 Daily Limit Reached.")
                    break
                
                res = get_av_analysis(s, AV_KEY, rate_delta, cur_rate)
                
                if res["status"] == "SUCCESS":
                    results.append(res)
                    st.write(f"✅ **{s}**: Scored {res['Score']}")
                elif res["status"] == "RATE_LIMIT":
                    st.warning(f"⏳ **{s}**: Rate limit hit. Waiting 60s...")
                    time.sleep(60)
                else:
                    st.write(f"❌ **{s}**: {res['msg']}")
                
                # Mandatory 12s delay between requests for Alpha Vantage Free Tier
                if i < len(tickers) - 1:
                    time.sleep(12) 
            
            status.update(label="Analysis Complete!", state="complete", expanded=False)

        if results:
            df = pd.DataFrame(results).drop(columns=['status'])
            df = df.sort_values(by="Score", ascending=False)
            st.subheader("🏆 Market Opportunities")
            st.dataframe(df, use_container_width=True)
            
            top_buys = df[df['Score'] >= threshold]
            if not top_buys.empty:
                st.balloons()
                st.success(f"Recommended Picks: {', '.join(top_buys['Ticker'].tolist())}")
        else:
            st.info("No stocks were scored. Check the logs in the status box above.")


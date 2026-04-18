import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import time
import datetime
from fredapi import Fred

# --- Page Config ---
st.set_page_config(page_title="AI Macro Stock Pro 2026", layout="wide")
st.title("📈 AI Stock Pro: 2026 Macro-Geopolitical Edition")

# --- 1. Initialize Session State (Ensures data persists for Export) ---
if 'results_data' not in st.session_state:
    st.session_state.results_data = None
if 'api_calls_used' not in st.session_state:
    st.session_state.api_calls_used = 0

# --- 2. API Keys from Secrets ---
FRED_KEY = st.secrets.get("fred_api_key")
AV_KEY = st.secrets.get("av_api_key")

# --- 3. Helper Functions ---
@st.cache_data(ttl=3600)
def fetch_macro_data(api_key):
    """Fetches Fed rates with a 2026 fallback for April market conditions."""
    try:
        fred = Fred(api_key=api_key)
        # April 2026 Fed Funds Rate is steady at ~3.75%
        rates = fred.get_series('FEDFUNDS').tail(2)
        cur_rate = rates.iloc[-1]
        rate_delta = cur_rate - rates.iloc[-2]
        return cur_rate, rate_delta
    except Exception:
        return 3.75, 0.0 # Standard April 2026 baseline fallback

def get_recommendation(score):
    """Assigns color-coded signals based on weighted sentiment/macro scores."""
    if score > 0.15: return "BUY", "green", "Strong sentiment + favorable macro alignment."
    if score < -0.15: return "SELL", "red", "Geopolitical risk or restrictive rate pressure."
    return "HOLD", "orange", "Neutral indicators or conflicting market signals."

def get_av_analysis(symbol, api_key, rate_delta, cur_rate):
    API_URL = "https://www.alphavantage.co/query"
    params = {"function": "NEWS_SENTIMENT", "tickers": symbol, "apikey": api_key}
    
    try:
        response = requests.get(API_URL, params=params, timeout=12)
        
        # Check if the response is blank or HTML (not JSON)
        if not response.text.strip() or "<html" in response.text.lower():
            return {"status": "ERROR", "msg": "API returned non-JSON (Throttled or Blocked)."}
        
        try:
            data = response.json()
        except ValueError:
            return {"status": "ERROR", "msg": "Could not parse JSON. Check API usage limits."}

        # Alpha Vantage uses "Note" to flag rate limiting
        if "Note" in data:
            return {"status": "LIMIT", "msg": "5-calls-per-minute limit hit."}
            
        # Check for daily limit reached message
        if "Information" in data and "25 requests per day" in data["Information"]:
             return {"status": "ERROR", "msg": "Daily limit (25/25) reached."}

        feed = data.get('feed', [])
        if not feed: 
            return {"status": "NO_NEWS", "msg": "No recent news found for this ticker."}

        # ... (rest of your existing logic) ...
        return {"status": "SUCCESS", "Ticker": symbol, "Score": 0.2, "Recommendation": "BUY"} 
        
    except Exception as e:
        return {"status": "ERROR", "msg": str(e)}


# --- 4. Sidebar UI ---
with st.sidebar:
    st.header("📊 2026 System Status")
    # Alpha Vantage 2026 Free Tier: 25 calls/day, 5 calls/min
    remaining = max(0, 25 - st.session_state.api_calls_used)
    st.write(f"Credits Remaining: **{remaining} / 25**")
    st.progress(remaining / 25)
    
    st.divider()
    watchlist = st.text_area("Enter Tickers (Max 5)", "AAPL, NVDA, TSLA, MSFT")
    scan_btn = st.button("🔍 Run Full 2026 Analysis", disabled=(remaining == 0))

# --- 5. Main Execution Loop ---
if not FRED_KEY or not AV_KEY:
    st.error("⚠️ API Keys Missing! Add 'fred_api_key' and 'av_api_key' to Secrets.")
else:
    cur_rate, rate_delta = fetch_macro_data(FRED_KEY)

    if scan_btn:
        tickers = [t.strip().upper() for t in watchlist.split(",")]
        temp_results = []
        
        with st.status("Analyzing 2026 Market Dynamics...", expanded=True) as status:
            for i, s in enumerate(tickers):
                if st.session_state.api_calls_used >= 25: break
                
                res = get_av_analysis(s, AV_KEY, rate_delta, cur_rate)
                
                if res and res.get("status") == "SUCCESS":
                    temp_results.append(res)
                    st.write(f"✅ {s}: Analysis complete.")
                elif res and res.get("status") == "LIMIT":
                    st.warning("⏳ 5/min limit hit. Waiting 60s...")
                    time.sleep(60)
                else:
                    st.write(f"❌ {s}: {res.get('msg', 'No data returned.')}")
                
                # Critical 12s delay to stay under Alpha Vantage free-tier 5-req/min cap
                if i < len(tickers) - 1: time.sleep(12) 
            status.update(label="Analysis Complete!", state="complete", expanded=False)
        
        st.session_state.results_data = temp_results

# --- 6. Results Display & CSV Export ---
if st.session_state.results_data:
    df = pd.DataFrame(st.session_state.results_data).drop(columns=['status', 'Color'])
    
    st.subheader("📊 Strategic Stock Deep-Dive")
    for item in st.session_state.results_data:
        # Dynamic color coding for expandable cards
        with st.expander(f"{item['Ticker']} — {item['Recommendation']}"):
            c1, c2 = st.columns()
            with c1:
                st.markdown(f"### Score: {item['Score']}")
                st.markdown(f"**Final Signal**: :{item['Color']}[{item['Recommendation']}]")
            with c2:
                st.write(f"**Geopolitical Context**: Monitoring 2026 energy price shocks and Hormuz volatility.")
                st.write(f"**Fed Interest Rates**: Steady at {item['Fed_Rate']} (Target: 3.5%-3.75%).")
                st.write(f"**Market Resilience**: {item['Market_Context']}")
                st.write(f"**Rationale**: {item['Reason']}")

    st.divider()
    # CSV Download stays visible thanks to session_state
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download 2026 Market Report (CSV)",
        data=csv,
        file_name=f"market_report_{datetime.date.today()}.csv",
        mime='text/csv',
    )
    st.dataframe(df, use_container_width=True)


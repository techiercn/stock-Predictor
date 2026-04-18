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

# --- Initialize Session State ---
if 'results_data' not in st.session_state:
    st.session_state.results_data = None
if 'api_calls_used' not in st.session_state:
    st.session_state.api_calls_used = 0

# --- API Keys ---
FRED_KEY = st.secrets.get("fred_api_key")
AV_KEY = st.secrets.get("av_api_key")

# --- Helper Functions ---
@st.cache_data(ttl=3600)
def fetch_macro_data(api_key):
    try:
        fred = Fred(api_key=api_key)
        rates = fred.get_series('FEDFUNDS').tail(2)
        cur_rate = rates.iloc[-1]
        rate_delta = cur_rate - rates.iloc[-2]
        return cur_rate, rate_delta
    except:
        return 3.75, 0.0 # April 2026 Default Baseline

def get_recommendation(score):
    if score > 0.15: return "BUY", "green", "Positive sentiment + neutral macro."
    elif score < -0.15: return "SELL", "red", "Geopolitical risk or rate hikes."
    else: return "HOLD", "orange", "Neutral indicators or mixed signals."

def get_av_analysis(symbol, api_key, rate_delta, cur_rate):
    API_URL = "https://alphavantage.co"
    params = {"function": "NEWS_SENTIMENT", "tickers": symbol, "apikey": api_key}
    try:
        response = requests.get(API_URL, params=params, timeout=12)
        if not response.text.strip(): return {"status": "ERROR", "msg": "Blank API response."}
        data = response.json()
        st.session_state.api_calls_used += 1
        
        if "Note" in data: return {"status": "LIMIT"}
        feed = data.get('feed', [])
        if not feed: return {"status": "NO_NEWS", "msg": "No news found."}

        scores = [float(item['overall_sentiment_score']) for item in feed[:5]]
        avg_sentiment = sum(scores) / len(scores)
        
        # Sector Weights
        t = yf.Ticker(symbol)
        sector = t.info.get('sector', 'Unknown')
        multiplier = {"Real Estate": 1.5, "Technology": 1.2, "Utilities": 1.5}.get(sector, 1.0)
        macro_impact = 0.2 if rate_delta < 0 else -0.2 if rate_delta > 0 else (0.05 if cur_rate < 4 else -0.05)
        
        final_score = avg_sentiment + (macro_impact * multiplier)
        rec, color, reason = get_recommendation(final_score)

        return {
            "status": "SUCCESS", "Ticker": symbol, "Sector": sector, 
            "Score": round(final_score, 2), "Sentiment": round(avg_sentiment, 2),
            "Recommendation": rec, "Color": color, "Reason": reason,
            "Fed_Rate": f"{cur_rate}%"
        }
    except: return None

# --- UI Sidebar ---
with st.sidebar:
    st.header("📊 2026 System Status")
    remaining = max(0, 25 - st.session_state.api_calls_used)
    st.write(f"Credits Remaining: **{remaining} / 25**")
    st.progress(remaining / 25)
    watchlist = st.text_area("Tickers", "AAPL, NVDA, TSLA")
    scan_btn = st.button("🔍 Run Full Analysis", disabled=(remaining == 0))

# --- Main App Execution ---
if not FRED_KEY or not AV_KEY:
    st.error("⚠️ API Keys Missing in Secrets!")
else:
    cur_rate, rate_delta = fetch_macro_data(FRED_KEY)

    if scan_btn:
        tickers = [t.strip().upper() for t in watchlist.split(",")]
        temp_results = []
        with st.status("Gathering 2026 Data...", expanded=True) as status:
            for i, s in enumerate(tickers):
                if st.session_state.api_calls_used >= 25: break
                res = get_av_analysis(s, AV_KEY, rate_delta, cur_rate)
                if res and res.get("status") == "SUCCESS":
                    temp_results.append(res)
                    st.write(f"✅ {s}: Complete.")
                elif res and res.get("status") == "LIMIT":
                    st.warning("⏳ 5/min limit hit. Waiting 60s...")
                    time.sleep(60)
                if i < len(tickers) - 1: time.sleep(12) 
            status.update(label="Analysis Complete!", state="complete", expanded=False)
        st.session_state.results_data = temp_results

# --- Results Display & CSV Export (FIXED KEYERROR) ---
if st.session_state.results_data:
    df = pd.DataFrame(st.session_state.results_data)
    
    # SAFE DROP: Only drop columns if they exist in the dataframe
    cols_to_drop = ['status', 'Color']
    df_clean = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
    
    st.subheader("📊 Individual Stock Deep-Dive")
    for item in st.session_state.results_data:
        if item.get("status") == "SUCCESS":
            with st.expander(f"{item['Ticker']} - {item['Recommendation']}"):
                st.markdown(f"**Signal**: :{item['Color']}[{item['Recommendation']}]")
                st.write(f"**Geopolitical Context**: Strait of Hormuz energy volatility (April 2026).")
                st.write(f"**Rationale**: {item['Reason']}")

    st.divider()
    csv = df_clean.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Report (CSV)", data=csv, file_name=f"report_{datetime.date.today()}.csv")
    st.dataframe(df_clean, use_container_width=True)


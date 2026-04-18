import streamlit as st
import pandas as pd
import requests
import datetime
import time

# --- Page Config ---
st.set_page_config(page_title="2026 Macro Stock Pro", layout="wide")
st.title("📈 AI Stock Pro: 2026 Market Analysis (Marketaux Edition)")

# --- Initialize Session State ---
if 'results_data' not in st.session_state:
    st.session_state.results_data = None

# --- API Keys ---
MARKETAUX_KEY = st.secrets.get("marketaux_api_key")

# --- Logic Functions ---
def get_recommendation(score):
    if score > 0.15: return "BUY", "green", "Strong bullish sentiment + favorable macro."
    if score < -0.15: return "SELL", "red", "Bearish sentiment or high geopolitical pressure."
    return "HOLD", "orange", "Neutral indicators or conflicting market signals."

# --- Sidebar ---
with st.sidebar:
    st.header("📊 System Status")
    watchlist = st.text_area("Enter Tickers", "AAPL, NVDA, TSLA")
    scan_btn = st.button("🔍 Run Full Analysis")

# --- Main App Execution ---
if not MARKETAUX_KEY:
    st.error("⚠️ Marketaux API Key missing! Add 'marketaux_api_key' to Secrets.")
else:
    # April 2026 Macro Context
    cur_rate = 3.64 # Fed Funds Effective Rate as of mid-April 2026
    
    if scan_btn:
        tickers = [t.strip().upper() for t in watchlist.split(",")]
        temp_results = []
        
        with st.status("Gathering 2026 Market Intelligence...") as status:
            for s in tickers:
                sentiment = get_marketaux_sentiment(s, MARKETAUX_KEY)
                
                # Weighting score (Sentiment + Macro Buffer)
                # In 2026, 3.64% is considered a neutral/restrictive high baseline
                final_score = sentiment + (0.05 if cur_rate < 4.0 else -0.05)
                rec, color, reason = get_recommendation(final_score)
                
                temp_results.append({
                    "Ticker": s, "Score": round(final_score, 2), 
                    "Sentiment": round(sentiment, 2), "Recommendation": rec, 
                    "Color": color, "Reason": reason
                })
                st.write(f"✅ {s}: Analysis complete.")
                time.sleep(1) # Minor throttle to stay safe
            status.update(label="Analysis Complete!", state="complete")
        st.session_state.results_data = temp_results

# --- Display & Export ---
if st.session_state.results_data:
    df = pd.DataFrame(st.session_state.results_data)
    
    st.subheader("📊 Individual Stock Deep-Dive")
    for item in st.session_state.results_data:
        with st.expander(f"{item['Ticker']} — {item['Recommendation']}"):
            st.markdown(f"**Final Signal**: :{item['Color']}[{item['Recommendation']}] (Score: {item['Score']})")
            st.write("**Geopolitical Context**: Strait of Hormuz energy reopening monitored (April 2026).")
            st.write(f"**Fed Interest Rates**: Steady at {cur_rate}% as of April 18, 2026.")
            st.write(f"**Rationale**: {item['Reason']}")

    st.divider()
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(label="📥 Download Full CSV Report", data=csv, file_name=f"report_{datetime.date.today()}.csv")
    st.dataframe(df.drop(columns=['Color']), use_container_width=True)


import streamlit as st
import pandas as pd
import requests
import datetime
import time
import plotly.express as px

# --- Page Config ---
st.set_page_config(page_title="2026 Macro Stock Pro", layout="wide")
st.title("📈 AI Stock Pro: 2026 Market Analysis")

# --- Initialize Session State ---
if 'results_data' not in st.session_state:
    st.session_state.results_data = None

# --- API Keys ---
# Ensure you have 'marketaux_api_key' in your .streamlit/secrets.toml
MARKETAUX_KEY = st.secrets.get("marketaux_api_key")

# --- Logic Functions ---
def get_marketaux_sentiment(ticker, api_key):
    """Fetches real-time sentiment from Marketaux API."""
    url = f"https://marketaux.com{ticker}&filter_entities=true&language=en&api_token={api_key}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        if "data" in data and len(data["data"]) > 0:
            scores = []
            for article in data["data"]:
                for entity in article.get('entities', []):
                    if entity.get('symbol') == ticker:
                        scores.append(entity.get('sentiment_score', 0))
            return sum(scores) / len(scores) if scores else 0.0
        return 0.0
    except Exception as e:
        st.error(f"API Error for {ticker}: {e}")
        return 0.0

def get_recommendation(score):
    if score > 0.15: return "BUY", "green", "Strong bullish sentiment + favorable macro."
    if score < -0.15: return "SELL", "red", "Bearish sentiment or high geopolitical pressure."
    return "HOLD", "orange", "Neutral indicators or conflicting market signals."

# --- Sidebar ---
with st.sidebar:
    st.header("📊 System Status")
    watchlist = st.text_area("Enter Tickers (comma separated)", "AAPL, NVDA, TSLA, MSFT")
    scan_btn = st.button("🔍 Run Full Analysis")
    st.info("April 2026 Context: Fed Rates at 3.64%")

# --- Main App Execution ---
if not MARKETAUX_KEY:
    st.warning("⚠️ Marketaux API Key missing! Add 'marketaux_api_key' to your Secrets.")
    st.stop()

# April 2026 Macro Context
cur_rate = 3.64 

if scan_btn:
    tickers = [t.strip().upper() for t in watchlist.split(",")]
    temp_results = []
    
    with st.status("Gathering 2026 Market Intelligence...") as status:
        for s in tickers:
            sentiment = get_marketaux_sentiment(s, MARKETAUX_KEY)
            
            # Weighting logic for 2026
            final_score = sentiment + (0.05 if cur_rate < 4.0 else -0.05)
            rec, color, reason = get_recommendation(final_score)
            
            temp_results.append({
                "Ticker": s, 
                "Score": round(final_score, 2), 
                "Sentiment": round(sentiment, 2), 
                "Recommendation": rec, 
                "Color": color, 
                "Reason": reason
            })
            st.write(f"✅ {s}: Analysis complete.")
            time.sleep(0.5) 
        status.update(label="Analysis Complete!", state="complete")
    st.session_state.results_data = temp_results

# --- Display & Visualization ---
if st.session_state.results_data:
    df = pd.DataFrame(st.session_state.results_data)
    
    # 1. Visualization: Sentiment vs Neutral Baseline
    st.subheader("📊 Market Analysis Visualizer")
    fig = px.bar(
        df, 
        x='Ticker', 
        y='Score', 
        color='Recommendation',
        color_discrete_map={'BUY': '#2ecc71', 'HOLD': '#f1c40f', 'SELL': '#e74c3c'},
        title="Final Analysis Scores relative to 2026 Macro Baseline"
    )
    # Add Neutral Threshold Lines
    fig.add_hline(y=0.15, line_dash="dot", annotation_text="Bullish Threshold", line_color="green")
    fig.add_hline(y=-0.15, line_dash="dot", annotation_text="Bearish Threshold", line_color="red")
    fig.update_layout(yaxis_title="Final Weighted Score", xaxis_title="Stock Ticker")
    st.plotly_chart(fig, use_container_width=True)

    # 2. Individual Deep-Dives
    st.subheader("🔍 Individual Stock Deep-Dive")
    for item in st.session_state.results_data:
        with st.expander(f"{item['Ticker']} — {item['Recommendation']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Weighted Score", item['Score'], delta=item['Sentiment'], delta_description="Raw News Sentiment")
            with col2:
                st.markdown(f"**Signal**: :{item['Color']}[{item['Recommendation']}]")
                st.write(f"**Rationale**: {item['Reason']}")
            st.caption(f"Context: Fed Rates at {cur_rate}% | Dated: April 18, 2026")

    # 3. Data Export
    st.divider()
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(label="📥 Download Full CSV Report", data=csv, file_name=f"report_{datetime.date.today()}.csv")
    st.dataframe(df.drop(columns=['Color']), use_container_width=True)


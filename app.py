import streamlit as st
import pandas as pd
import requests
import datetime
import time
import plotly.express as px
from textblob import TextBlob

# --- Page Config ---
st.set_page_config(page_title="2026 Macro Stock Pro", layout="wide")
st.title("📈 AI Stock Pro: 2026 Market Analysis (NewsAPI Edition)")

# --- Initialize Session State ---
if 'results_data' not in st.session_state:
    st.session_state.results_data = None

# --- API Keys ---
# Replace 'marketaux_api_key' with 'news_api_key' in your Streamlit Secrets
NEWS_API_KEY = st.secrets.get("news_api_key")

# --- Logic Functions ---
def get_news_sentiment(ticker, api_key):
    """Fetches news from NewsAPI and calculates sentiment using TextBlob."""
    url = f"https://newsapi.org{ticker}&language=en&sortBy=relevancy&apiKey={api_key}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get("status") == "ok" and data.get("totalResults", 0) > 0:
            articles = data["articles"][:10]  # Analyze top 10 articles
            scores = []
            for art in articles:
                # Combine title and description for better context
                text = f"{art.get('title', '')} {art.get('description', '')}"
                analysis = TextBlob(text)
                scores.append(analysis.sentiment.polarity) # Ranges from -1.0 to 1.0
            
            return sum(scores) / len(scores) if scores else 0.0
        return 0.0
    except Exception as e:
        st.error(f"NewsAPI Error for {ticker}: {e}")
        return 0.0

def get_recommendation(score):
    if score > 0.10: return "BUY", "green", "Positive news trend + macro tailwinds."
    if score < -0.10: return "SELL", "red", "Negative news cycle or macro pressure."
    return "HOLD", "orange", "Mixed sentiment or neutral macro environment."

# --- Sidebar ---
with st.sidebar:
    st.header("📊 System Status")
    watchlist = st.text_area("Enter Tickers (comma separated)", "AAPL, NVDA, TSLA")
    scan_btn = st.button("🔍 Run Full Analysis")
    st.info("Macro Context: April 2026")

# --- Main App Execution ---
if not NEWS_API_KEY:
    st.warning("⚠️ NewsAPI Key missing! Add 'news_api_key' to your Secrets.")
    st.stop()

cur_rate = 3.64 

if scan_btn:
    tickers = [t.strip().upper() for t in watchlist.split(",")]
    temp_results = []
    
    with st.status("Analyzing 2026 Global News...") as status:
        for s in tickers:
            sentiment = get_news_sentiment(s, NEWS_API_KEY)
            
            # Weighting logic (Sentiment + Fed Rate Buffer)
            final_score = sentiment + (0.05 if cur_rate < 4.0 else -0.05)
            rec, color, reason = get_recommendation(final_score)
            
            temp_results.append({
                "Ticker": s, "Score": round(final_score, 2), 
                "Sentiment": round(sentiment, 2), "Recommendation": rec, 
                "Color": color, "Reason": reason
            })
            st.write(f"✅ {s}: Sentiment processed.")
            time.sleep(0.2) # Faster than Marketaux
        status.update(label="Analysis Complete!", state="complete")
    st.session_state.results_data = temp_results

# --- Display & Visualization ---
if st.session_state.results_data:
    df = pd.DataFrame(st.session_state.results_data)
    
    st.subheader("📊 Sentiment vs Baseline")
    fig = px.bar(df, x='Ticker', y='Score', color='Recommendation',
                 color_discrete_map={'BUY': '#2ecc71', 'HOLD': '#f1c40f', 'SELL': '#e74c3c'})
    fig.add_hline(y=0.10, line_dash="dot", line_color="green")
    fig.add_hline(y=-0.10, line_dash="dot", line_color="red")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🔍 Stock Deep-Dive")
    for item in st.session_state.results_data:
        with st.expander(f"{item['Ticker']} — {item['Recommendation']}"):
            st.metric("Final Score", item['Score'], delta=f"{item['Sentiment']} Sentiment")
            st.markdown(f"**Rationale**: {item['Reason']}")
            st.caption("Data source: NewsAPI (v2/everything)")

    st.divider()
    st.dataframe(df.drop(columns=['Color']), use_container_width=True)


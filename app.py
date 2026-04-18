import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from fredapi import Fred
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- Page Config ---
st.set_page_config(page_title="Macro Pro: Top Picks", layout="wide")
st.title("🚀 AI Stock Pro: Top Market Picks")

# --- API Keys ---
FRED_KEY = st.secrets.get("fred_api_key")
NEWSDATA_KEY = st.secrets.get("newsdata_api_key")

# --- Cached Macro Data ---
@st.cache_data(ttl=3600)
def fetch_macro_data(api_key):
    if not api_key: return 0.0, 0.0
    try:
        fred = Fred(api_key=api_key)
        rates = fred.get_series('FEDFUNDS').tail(2)
        cur_rate = rates.iloc[-1]
        rate_delta = cur_rate - rates.iloc[-2]
        return cur_rate, rate_delta
    except Exception:
        return 0.0, 0.0

# --- Cached Stock Analysis ---
@st.cache_data(ttl=1800)
def get_stock_analysis(symbol, api_key, rate_delta, cur_rate):
    try:
        t = yf.Ticker(symbol)
        sector = t.info.get('sector', 'Unknown')
        
        # Sentiment Analysis via NewsData.io
        analyzer = SentimentIntensityAnalyzer()
        # Query format: https://newsdata.io/api/1/latest?apikey=YOUR_API_KEY&q=TOPIC
        url = f"https://newsdata.io{api_key}&q={symbol}&language=en"
        r = requests.get(url).json()
        articles = r.get('results', [])[:5] 
        
        sentiment = sum([analyzer.polarity_scores(a['title'])['compound'] for a in articles])/len(articles) if articles else 0
        
        # Sector Multipliers
        multiplier = {"Real Estate": 1.5, "Utilities": 1.5, "Technology": 1.2}.get(sector, 1.0)
        macro_impact = 0.2 if rate_delta < 0 else -0.2 if rate_delta > 0 else (0.05 if cur_rate < 4 else -0.05)
        
        final_score = sentiment + (macro_impact * multiplier)
        return {"Ticker": symbol, "Sector": sector, "Score": round(final_score, 2), "Sentiment": round(sentiment, 2)}
    except Exception:
        return None

# --- UI Sidebar ---
st.sidebar.header("Global Watchlist")
watchlist_input = st.sidebar.text_area("Tickers to Scan", "AAPL, NVDA, TSLA, MSFT, O, XOM")
threshold = st.sidebar.slider("Buy Threshold", 0.05, 0.30, 0.10)
scan_btn = st.sidebar.button("🔍 Run Full Scan")

# --- Main App Execution ---
if not FRED_KEY or not NEWSDATA_KEY:
    st.error("Missing API Keys! Add 'fred_api_key' and 'newsdata_api_key' to your Secrets.")
else:
    cur_rate, rate_delta = fetch_macro_data(FRED_KEY)

    if scan_btn:
        tickers = [t.strip().upper() for t in watchlist_input.split(",")]
        results = []
        progress = st.progress(0)

        for i, s in enumerate(tickers):
            res = get_stock_analysis(s, NEWSDATA_KEY, rate_delta, cur_rate)
            if res: results.append(res)
            progress.progress((i + 1) / len(tickers))

        if results:
            df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
            top_buys = df[df['Score'] >= threshold]

            st.subheader("🏆 Current Top Opportunities")
            if not top_buys.empty:
                cols = st.columns(min(len(top_buys), 4))
                for idx, (_, row) in enumerate(top_buys.head(4).iterrows()):
                    with cols[idx]:
                        st.metric(label=row['Ticker'], value=f"Score: {row['Score']}", delta=f"Sent: {row['Sentiment']}")
                        st.caption(f"Sector: {row['Sector']}")
            else:
                st.info(f"No stocks meet the {threshold} threshold.")

            st.divider()
            st.write("### Complete Rankings")
            st.dataframe(df, use_container_width=True)
        else:
            st.error("Scan failed. Verify your NewsData.io key and internet connection.")


import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from fredapi import Fred
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- Page Config & Styling ---
st.set_page_config(page_title="Macro Pro: Top Picks", layout="wide")
st.title("🚀 AI Stock Pro: Top Market Picks")

# --- API Keys ---
FRED_KEY = st.secrets.get("fred_api_key")
NEWS_KEY = st.secrets.get("news_api_key")

# --- Core Logic Functions ---
def get_analysis(symbol, news_key, rate_change, current_rate):
    """Utility to run the full analysis for a single ticker."""
    try:
        t = yf.Ticker(symbol)
        sector = t.info.get('sector', 'Unknown')
        
        # Sentiment Analysis
        analyzer = SentimentIntensityAnalyzer()
        url = f"https://newsapi.org{symbol}+(stock+OR+fed)&apiKey={news_key}"
        r = requests.get(url).json()
        articles = r.get('articles', [])[:5]
        sentiment = sum([analyzer.polarity_scores(a['title'])['compound'] for a in articles])/len(articles) if articles else 0
        
        # Macro weighting
        multiplier = {"Real Estate": 1.5, "Utilities": 1.5, "Technology": 1.0}.get(sector, 1.0)
        macro_impact = 0.2 if rate_change < 0 else -0.2 if rate_change > 0 else (0.05 if current_rate < 4 else -0.05)
        
        final_score = sentiment + (macro_impact * multiplier)
        return {"Ticker": symbol, "Sector": sector, "Score": round(final_score, 2), "Sentiment": round(sentiment, 2)}
    except:
        return None

# --- Sidebar Inputs ---
st.sidebar.header("Global Watchlist")
watchlist_input = st.sidebar.text_area("Enter All Tickers to Scan (comma separated)", "AAPL, NVDA, TSLA, MSFT, O, XOM")
threshold = st.sidebar.slider("Buy Threshold", 0.05, 0.30, 0.10)
scan_btn = st.sidebar.button("🔍 Scan for Top Picks")

# --- Main Dashboard ---
if scan_btn:
    tickers = [t.strip().upper() for t in watchlist_input.split(",")]
    
    # 1. Get Global Macro Context (Only once per scan)
    fred = Fred(api_key=FRED_KEY)
    rates = fred.get_series('FEDFUNDS').tail(2)
    cur_rate, rate_delta = rates.iloc[-1], rates.iloc[-1] - rates.iloc[-2]

    st.subheader("🏆 Current Top Opportunities")
    results = []
    
    # Progress bar for scanning
    progress = st.progress(0)
    for i, s in enumerate(tickers):
        res = get_analysis(s, NEWS_KEY, rate_delta, cur_rate)
        if res: results.append(res)
        progress.progress((i + 1) / len(tickers))

    # 2. Filter and Sort
    df = pd.DataFrame(results).sort_values(by="Score", ascending=False)
    top_buys = df[df['Score'] >= threshold]

    if not top_buys.empty:
        # Display Top Picks as visual "Cards"
        cols = st.columns(len(top_buys[:4])) # Show up to 4 top picks in columns
        for idx, row in enumerate(top_buys.iloc[:4].iterrows()):
            data = row[1]
            with cols[idx]:
                st.metric(label=data['Ticker'], value=f"Score: {data['Score']}", delta=f"Sent: {data['Sentiment']}")
                st.caption(f"Sector: {data['Sector']}")
    else:
        st.info("No strong 'BUY' signals detected in the current watchlist.")

    st.divider()
    st.write("### All Watchlist Rankings")
    st.dataframe(df, use_container_width=True)


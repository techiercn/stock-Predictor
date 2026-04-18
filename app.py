import streamlit as st
import yfinance as yf

# 1. Define Sector Sensitivity Mapping
SECTOR_SENSITIVITY = {
    "Real Estate": 1.5,      # Highly sensitive
    "Utilities": 1.5,
    "Financial Services": 1.2,
    "Technology": 1.0,
    "Consumer Defensive": 0.5, # Less sensitive
}

def get_sector_data(ticker_symbol):
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        return info.get('sector', 'Unknown'), info.get('industry', 'Unknown')
    except:
        return "Unknown", "Unknown"

# --- Usage in Recommendation Engine ---
ticker = st.sidebar.text_input("Ticker", "AAPL")
sector, industry = get_sector_data(ticker)

st.write(f"**Detected Sector**: {sector} | **Industry**: {industry}")

# Adjust recommendation weight based on sector
multiplier = SECTOR_SENSITIVITY.get(sector, 1.0)
# Final Macro Score = (Interest Rate Change) * (Sector Multiplier)


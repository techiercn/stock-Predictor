import streamlit as st
import pandas as pd
import requests
import time
from fredapi import Fred

# --- Page Setup ---
st.set_page_config(page_title="Pro Stock Analyzer", layout="wide")
st.title("📈 AI Stock Pro: 2026 Macro Analysis")

# --- Helper: Analysis Function ---
def get_recommendation(score):
    if score > 0.15: return "BUY", "success", "Strong sentiment and favorable macro."
    if score < -0.15: return "SELL", "error", "High geopolitical risk and rate pressure."
    return "HOLD", "warning", "Conflicting macro data or market uncertainty."

# --- Main Execution ---
# [Logic for fetching AV News and FRED data as previously defined]

if st.sidebar.button("🔍 Run Full Analysis"):
    # (Pre-fetch FRED rate_delta and current_rate here)
    results = [] # Stores final data for the CSV
    
    # After loop completes...
    if results:
        df = pd.DataFrame(results)
        
        # --- Display Results with Color Recommendations ---
        st.subheader("📊 Market Analysis Report")
        for idx, row in df.iterrows():
            rec, color, reason = get_recommendation(row['Score'])
            
            with st.expander(f"{row['Ticker']} - Recommendation: {rec}"):
                st.write(f"**Recommendation**: :{color}[{rec}]")
                st.write(f"**Geopolitical Context**: Tracking energy impacts from Strait of Hormuz.")
                st.write(f"**Fed Interest Rates**: Rates steady at 3.75%.")
                st.write(f"**Rationale**: {reason}")
        
        # --- Save Report Feature ---
        st.divider()
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Full Analysis as CSV",
            data=csv,
            file_name='market_report_april_2026.csv',
            mime='text/csv',
        )


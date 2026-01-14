"""
Raw Data Page - View full dataset

Complete dataset with all cars, sortable and filterable.
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from model import load_data, fit_models, calculate_deal_scores

st.markdown("# 📊 Raw Data")
st.markdown("View and download the complete dataset")

# Load data
with st.spinner("Loading data..."):
    df = load_data()
    model_linear, model_log = fit_models(df)
    df = calculate_deal_scores(df, model_linear, model_log)

    # Filter valid predictions
    df_valid = df.dropna(subset=["discount_pct", "predicted_price_log"]).copy()

# Summary statistics
st.markdown("### 📈 Dataset Summary")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Cars", f"{len(df_valid):,}")
with col2:
    st.metric("Price Range", f"{df_valid['price'].min()/1000:.0f}k - {df_valid['price'].max()/1000:.0f}k SEK")
with col3:
    st.metric("Mileage Range", f"{df_valid['mileage'].min()/1000:.0f}k - {df_valid['mileage'].max()/1000:.0f}k km")
with col4:
    st.metric("Year Range", f"{int(df_valid['model_year'].min())} - {int(df_valid['model_year'].max())}")

st.markdown("---")

# Full data table
st.markdown("### 🗂️ Complete Dataset")

# Select columns to display
display_cols = [
    "registration_number", "price", "predicted_price_log", "discount_pct",
    "model_year", "mileage", "horsepower", "engine_code", "fuel_type",
    "driving_type", "location", "franchise_approved", "source", "url"
]

display_df = df_valid[display_cols].copy()

# Rename for readability
display_df.columns = [
    "Registration", "Price (SEK)", "Predicted Price", "Discount %",
    "Year", "Mileage (km)", "HP", "Engine", "Fuel",
    "Drive", "Location", "Certified", "Source", "Link"
]

# Round numbers
display_df["Predicted Price"] = display_df["Predicted Price"].round(0).astype(int)
display_df["Discount %"] = display_df["Discount %"].round(1)
display_df["Price (SEK)"] = display_df["Price (SEK)"].astype(int)
display_df["Mileage (km)"] = display_df["Mileage (km)"].astype(int)
display_df["Year"] = display_df["Year"].astype(int)

# Handle missing locations
display_df["Location"] = display_df["Location"].fillna("N/A")

# Display dataframe
st.dataframe(
    display_df,
    column_config={
        "Link": st.column_config.LinkColumn("Link", display_text="View →"),
        "Price (SEK)": st.column_config.NumberColumn(format="%d"),
        "Predicted Price": st.column_config.NumberColumn(format="%d"),
        "Discount %": st.column_config.NumberColumn(format="%.1f%%"),
        "Mileage (km)": st.column_config.NumberColumn(format="%d"),
        "Certified": st.column_config.CheckboxColumn("Certified"),
    },
    hide_index=True,
    width="stretch",
    height=600
)

# Download button
st.markdown("### 💾 Download Data")

csv = display_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label="Download as CSV",
    data=csv,
    file_name="volvo_xc60_deals.csv",
    mime="text/csv",
)

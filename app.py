"""
Volvo XC60 Deal Finder - Main App Entry Point

Multi-page Streamlit app for finding the best deals on used Volvo XC60s.
"""

import streamlit as st

# Page config (must be first Streamlit command)
st.set_page_config(
    page_title="Volvo XC60 Deal Finder",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Landing page
st.markdown("""
# 🚗 Volvo XC60 Deal Finder

Welcome to the Volvo XC60 Deal Finder! Use the navigation on the left to:

- **🏠 Deals** - View best deals with interactive scatter plot and filtering
- **🔍 Search** - Search for a specific car and find comparable alternatives
- **📊 Raw Data** - View and download the complete dataset

---

## How It Works

This app uses a **polynomial regression model** (R² = 0.948) to predict fair market prices for used Volvo XC60s based on:
- Mileage (linear, quadratic, and cubic terms)
- Horsepower
- Model year
- Engine code
- Fuel type
- Driving type (AWD/FWD)
- Franchise certification status

Cars priced significantly below their predicted value are highlighted as **good deals**.

👈 **Get started by selecting a page from the sidebar!**
""")

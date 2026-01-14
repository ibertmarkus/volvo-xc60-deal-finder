"""
Search Page - Find a car and see comparable alternatives

Search by registration number and find similar cars.
"""

import streamlit as st
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from model import load_data, fit_models, calculate_deal_scores

st.markdown("# 🔍 Car Search")
st.markdown("Search for a specific car and find comparable alternatives")


@st.cache_data
def get_data_with_scores():
    """Load data and calculate deal scores (cached)."""
    df = load_data()
    model_linear, model_log = fit_models(df)
    df = calculate_deal_scores(df, model_linear, model_log)
    df_valid = df.dropna(subset=["discount_pct", "predicted_price_log"]).copy()
    return df_valid


def calculate_comparable_cars(df, target_reg, n=5):
    """
    Find n most comparable cars using weighted feature distance.

    Features:
    - Continuous: model_year, mileage, horsepower (normalized)
    - Categorical: engine_code, fuel_type (one-hot encoded)

    Weights: year=0.2, mileage=0.4, HP=0.2, engine=0.1, fuel=0.1
    """
    # Get target car
    target = df[df["registration_number"] == target_reg].iloc[0]

    # Exclude target car from comparison
    comparison_df = df[df["registration_number"] != target_reg].copy()

    # Continuous features
    continuous_features = ["model_year", "mileage", "horsepower"]
    continuous_weights = [0.2, 0.4, 0.2]

    # Normalize continuous features to 0-1 scale
    scaler = StandardScaler()

    # Fit on all data including target
    all_continuous = df[continuous_features].values
    scaler.fit(all_continuous)

    # Transform
    target_continuous = scaler.transform(target[continuous_features].values.reshape(1, -1))[0]
    comparison_continuous = scaler.transform(comparison_df[continuous_features].values)

    # Calculate weighted continuous distance
    continuous_dist = np.zeros(len(comparison_df))
    for i, (feature, weight) in enumerate(zip(continuous_features, continuous_weights)):
        continuous_dist += weight * (comparison_continuous[:, i] - target_continuous[i]) ** 2

    # Categorical features (simple binary match)
    engine_match = (comparison_df["engine_code"] == target["engine_code"]).astype(int) * 0.1
    fuel_match = (comparison_df["fuel_type"] == target["fuel_type"]).astype(int) * 0.1

    # Total distance (lower is more similar)
    # Subtract categorical matches because they reduce distance
    total_distance = np.sqrt(continuous_dist) - engine_match.values - fuel_match.values

    # Get indices of n closest cars
    closest_indices = np.argsort(total_distance)[:n]

    # Return comparable cars with distance scores
    comparable = comparison_df.iloc[closest_indices].copy()
    comparable["similarity_score"] = 100 - (total_distance[closest_indices] * 50)  # Convert to 0-100 scale
    comparable["similarity_score"] = comparable["similarity_score"].clip(0, 100)

    return comparable


# Load data
df = get_data_with_scores()

# Search interface
st.markdown("### 🔎 Search for a Car")

# Autocomplete-style search
registration_options = [""] + sorted(df["registration_number"].tolist())
selected_reg = st.selectbox(
    "Enter or select registration number:",
    options=registration_options,
    index=0
)

if selected_reg:
    # Get car details
    car = df[df["registration_number"] == selected_reg].iloc[0]

    # Display selected car
    st.markdown("---")
    st.markdown(f"## 🚗 {selected_reg}")

    # Two columns for details
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📋 Specifications")
        location_display = car['location'] if pd.notna(car['location']) and car['location'] else 'N/A'
        st.markdown(f"""
        - **Year:** {int(car['model_year'])}
        - **Engine:** {car['engine_code']} ({car['horsepower']:.0f} HP)
        - **Fuel:** {car['fuel_type']}
        - **Drive:** {car['driving_type']}
        - **Mileage:** {car['mileage']:,.0f} km
        - **Location:** {location_display}
        - **Certified:** {'Yes' if car['franchise_approved'] else 'No'}
        """)

    with col2:
        st.markdown("### 💰 Pricing")
        st.markdown(f"""
        - **Listed Price:** {car['price']:,.0f} SEK
        - **Predicted Fair Value:** {car['predicted_price_log']:,.0f} SEK
        - **Discount:** {car['discount_pct']:.1f}% ({car['discount_sek']:,.0f} SEK)
        """)

        # Deal indicator
        if car['discount_pct'] > 10:
            st.success("🎉 **Excellent deal!**")
        elif car['discount_pct'] > 5:
            st.info("✅ **Good deal**")
        elif car['discount_pct'] > 0:
            st.warning("⚠️ **Fair price**")
        else:
            st.error("❌ **Overpriced**")

    # Link to listing
    if pd.notna(car['url']):
        st.markdown(f"[🔗 View Listing]({car['url']})")

    # Find comparable cars
    st.markdown("---")
    st.markdown("### 🔄 20 Most Comparable Cars")
    st.caption("Based on year, mileage, horsepower, engine type, and fuel type")

    comparable = calculate_comparable_cars(df, selected_reg, n=20)

    # Display comparable cars
    for idx, (_, comp_car) in enumerate(comparable.iterrows(), 1):
        with st.expander(f"#{idx} - {comp_car['registration_number']} ({comp_car['similarity_score']:.0f}% similar)", expanded=(idx <= 2)):
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**Specs**")
                comp_location = comp_car['location'] if pd.notna(comp_car['location']) and comp_car['location'] else 'N/A'
                st.markdown(f"""
                - Year: {int(comp_car['model_year'])}
                - Engine: {comp_car['engine_code']}
                - HP: {comp_car['horsepower']:.0f}
                - Fuel: {comp_car['fuel_type']}
                - Mileage: {comp_car['mileage']:,.0f} km
                - Location: {comp_location}
                """)

            with col2:
                st.markdown("**Price**")
                st.markdown(f"""
                - Price: {comp_car['price']:,.0f} SEK
                - Predicted: {comp_car['predicted_price_log']:,.0f} SEK
                - Discount: {comp_car['discount_pct']:.1f}%
                """)

            with col3:
                st.markdown("**Comparison**")

                # Price difference
                price_diff = comp_car['price'] - car['price']
                price_diff_pct = (price_diff / car['price']) * 100
                st.markdown(f"Price vs selected: {price_diff:+,.0f} SEK ({price_diff_pct:+.1f}%)")

                # Mileage difference
                mileage_diff = comp_car['mileage'] - car['mileage']
                st.markdown(f"Mileage vs selected: {mileage_diff:+,.0f} km")

                # Deal quality comparison
                if comp_car['discount_pct'] > car['discount_pct']:
                    st.success(f"Better deal (+{comp_car['discount_pct'] - car['discount_pct']:.1f}%)")
                elif comp_car['discount_pct'] < car['discount_pct']:
                    st.warning(f"Worse deal ({comp_car['discount_pct'] - car['discount_pct']:.1f}%)")
                else:
                    st.info("Similar deal")

                # Link
                if pd.notna(comp_car['url']):
                    st.markdown(f"[View Listing →]({comp_car['url']})")

else:
    st.info("👆 Select a registration number to view car details and comparable alternatives")

    # Show some example searches
    st.markdown("### 💡 Try searching for:")
    example_regs = df.nlargest(3, "discount_pct")["registration_number"].tolist()
    st.markdown("**Best deals:**")
    for reg in example_regs:
        st.markdown(f"- `{reg}`")

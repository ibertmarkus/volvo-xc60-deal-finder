"""
Deals Page - Find the best Volvo XC60 deals

Shows scatter plot and top 50 deals table with interactive filtering.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Import model functions
from model import load_data, fit_models, compare_models, calculate_deal_scores

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A5F;
        margin-bottom: 0.5rem;
    }
    .stDataFrame {
        font-size: 0.85rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }
    /* Reduce padding for wider content */
    .block-container {
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 100%;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def get_model_data():
    """Load data and fit models (cached)."""
    df = load_data()
    model_linear, model_log = fit_models(df)
    comparison = compare_models(model_linear, model_log, df)
    df = calculate_deal_scores(df, model_linear, model_log)
    return df, model_linear, model_log, comparison


def get_coefficients_df(model):
    """Extract coefficients as a DataFrame."""
    coef_df = pd.DataFrame({
        "Variable": model.params.index,
        "Coefficient": model.params.values,
        "Std Error": model.bse.values,
        "t-stat": model.tvalues.values,
        "p-value": model.pvalues.values
    })

    # Add significance stars
    def sig_stars(p):
        if p < 0.001:
            return "***"
        elif p < 0.01:
            return "**"
        elif p < 0.05:
            return "*"
        elif p < 0.1:
            return "."
        return ""

    coef_df["Sig."] = coef_df["p-value"].apply(sig_stars)

    # Format for display
    coef_df["Coefficient"] = coef_df["Coefficient"].apply(lambda x: f"{x:,.4f}")
    coef_df["Std Error"] = coef_df["Std Error"].apply(lambda x: f"{x:,.4f}")
    coef_df["t-stat"] = coef_df["t-stat"].apply(lambda x: f"{x:.2f}")
    coef_df["p-value"] = coef_df["p-value"].apply(lambda x: f"{x:.4f}" if x >= 0.0001 else "<0.0001")

    return coef_df


# Header
st.markdown('<p class="main-header">🏠 Best Deals</p>', unsafe_allow_html=True)
st.markdown("Find underpriced cars using regression analysis")

# Load data
with st.spinner("Loading data and fitting models..."):
    df, model_linear, model_log, comparison = get_model_data()

# Filter out NaN predictions
df_valid = df.dropna(subset=["discount_pct", "predicted_price_log"]).copy()

# =====================
# SIDEBAR FILTERS
# =====================
st.sidebar.header("🔍 Filters")

# Year range
year_min, year_max = int(df_valid["model_year"].min()), int(df_valid["model_year"].max())
year_range = st.sidebar.slider(
    "Model Year",
    min_value=year_min,
    max_value=year_max,
    value=(year_min, year_max)
)

# Engine code
engines = sorted(df_valid["engine_code"].unique())
selected_engines = st.sidebar.multiselect(
    "Engine Code",
    options=engines,
    default=engines
)

# Fuel type
fuels = sorted(df_valid["fuel_type"].unique())
selected_fuels = st.sidebar.multiselect(
    "Fuel Type",
    options=fuels,
    default=fuels
)

# Price range
price_min, price_max = int(df_valid["price"].min()), int(df_valid["price"].max())
price_range = st.sidebar.slider(
    "Price (SEK)",
    min_value=price_min,
    max_value=price_max,
    value=(price_min, price_max),
    step=10000,
    format="%d"
)

# Mileage range
mileage_min, mileage_max = int(df_valid["mileage"].min()), int(df_valid["mileage"].max())
mileage_range = st.sidebar.slider(
    "Mileage (km)",
    min_value=mileage_min,
    max_value=mileage_max,
    value=(mileage_min, mileage_max),
    step=10000,
    format="%d"
)

# Minimum discount
min_discount = st.sidebar.slider(
    "Minimum Discount %",
    min_value=-30,
    max_value=30,
    value=-30,
    step=1
)

# Apply filters
mask = (
    (df_valid["model_year"] >= year_range[0]) &
    (df_valid["model_year"] <= year_range[1]) &
    (df_valid["engine_code"].isin(selected_engines)) &
    (df_valid["fuel_type"].isin(selected_fuels)) &
    (df_valid["price"] >= price_range[0]) &
    (df_valid["price"] <= price_range[1]) &
    (df_valid["mileage"] >= mileage_range[0]) &
    (df_valid["mileage"] <= mileage_range[1]) &
    (df_valid["discount_pct"] >= min_discount)
)
df_filtered = df_valid[mask].copy()

st.sidebar.markdown(f"**{len(df_filtered)}** cars match filters")

# =====================
# MODEL STATISTICS
# =====================
st.markdown("---")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("R² (Log Model)", f"{comparison['Log-Linear Model']['R² (log scale)']:.3f}")
with col2:
    st.metric("Adj. R²", f"{comparison['Log-Linear Model']['Adj. R² (log scale)']:.3f}")
with col3:
    st.metric("RMSE (log)", f"{comparison['Log-Linear Model']['RMSE (log scale)']:.4f}")
with col4:
    st.metric("Cars in Model", f"{len(df_valid):,}")

# =====================
# PREPARE TABLE DATA (all filtered cars, sorted by discount)
# =====================
table_deals = df_filtered.sort_values("discount_pct", ascending=False).copy().reset_index(drop=True)

# =====================
# SCATTER PLOT
# =====================
st.markdown("### 📊 Price vs Mileage")

# Get selected registration from session state
selected_reg = st.session_state.get("selected_car", None)

# Create hover text
df_filtered["hover_text"] = df_filtered.apply(
    lambda r: f"<b>{r['registration_number']}</b><br>" +
              f"Price: {r['price']:,.0f} SEK<br>" +
              f"Predicted: {r['predicted_price_log']:,.0f} SEK<br>" +
              f"Discount: {r['discount_pct']:.1f}%<br>" +
              f"Year: {int(r['model_year'])}<br>" +
              f"Engine: {r['engine_code']} ({r['horsepower']:.0f} HP)<br>" +
              f"Mileage: {r['mileage']:,.0f} km<br>" +
              f"Location: {r['location'] if pd.notna(r['location']) and r['location'] else 'N/A'}",
    axis=1
)

# Handle empty filtered data
if len(df_filtered) == 0:
    st.warning("No cars match your filter criteria. Try adjusting the filters.")
    st.stop()

# Color scale centered at 0
max_abs_discount = max(abs(df_filtered["discount_pct"].min()), abs(df_filtered["discount_pct"].max()), 1)

fig = px.scatter(
    df_filtered,
    x="mileage",
    y="price",
    color="discount_pct",
    color_continuous_scale="RdYlGn",
    range_color=[-max_abs_discount, max_abs_discount],
    hover_name="registration_number",
    custom_data=["url", "registration_number", "discount_pct"],
    labels={
        "mileage": "Mileage (km)",
        "price": "Price (SEK)",
        "discount_pct": "Discount %"
    }
)

fig.update_traces(
    hovertemplate=df_filtered["hover_text"],
    marker=dict(size=10, opacity=0.7)
)

# Highlight selected car from table
if selected_reg and selected_reg in df_filtered["registration_number"].values:
    selected_car = df_filtered[df_filtered["registration_number"] == selected_reg].iloc[0]
    fig.add_trace(go.Scatter(
        x=[selected_car["mileage"]],
        y=[selected_car["price"]],
        mode="markers",
        marker=dict(
            size=25,
            color="rgba(0,0,0,0)",
            line=dict(color="blue", width=3)
        ),
        name=f"Selected: {selected_reg}",
        hoverinfo="skip",
        showlegend=True
    ))

fig.update_layout(
    height=500,
    xaxis=dict(
        tickformat=",",
        range=[0, min(df_filtered["mileage"].quantile(0.99) * 1.1, df_filtered["mileage"].max() * 1.05)]  # Use 99th percentile with padding, or max if smaller
    ),
    yaxis=dict(
        tickformat=",",
        range=[df_filtered["price"].min() * 0.95, df_filtered["price"].max() * 1.05]  # Add padding
    ),
    coloraxis_colorbar=dict(title="Discount %"),
    hovermode="closest",
    margin=dict(l=20, r=20, t=40, b=20)  # Reduce margins for wider plot
)

# Add click event info
st.plotly_chart(fig, width="stretch", key="main_scatter")
st.caption("💡 Green = underpriced (good deal), Red = overpriced. Hover for details.")

# =====================
# ALL CARS TABLE
# =====================
st.markdown(f"### 📋 All Cars ({len(table_deals)} total)")
st.caption("💡 Sorted by discount %. Click a row to highlight it on the plot above")

# Format table columns - keep raw URL for LinkColumn
table_df = table_deals[[
    "registration_number", "price", "predicted_price_log",
    "discount_pct", "discount_sek",
    "model_year", "mileage", "horsepower", "engine_code",
    "fuel_type", "driving_type", "location", "url"
]].copy()

table_df.columns = [
    "Reg. Nr", "Price (SEK)", "Predicted (SEK)",
    "Discount %", "Discount (SEK)",
    "Year", "Mileage (km)", "HP", "Engine",
    "Fuel", "Drive", "Location", "Link"
]

# Round numbers
table_df["Predicted (SEK)"] = table_df["Predicted (SEK)"].round(0).astype(int)
table_df["Discount %"] = table_df["Discount %"].round(1)
table_df["Discount (SEK)"] = table_df["Discount (SEK)"].round(0).astype(int)
table_df["Price (SEK)"] = table_df["Price (SEK)"].astype(int)
table_df["Mileage (km)"] = table_df["Mileage (km)"].astype(int)
table_df["Year"] = table_df["Year"].astype(int)

# Handle missing locations
table_df["Location"] = table_df["Location"].fillna("N/A")

# Display with row selection enabled
selection = st.dataframe(
    table_df,
    column_config={
        "Link": st.column_config.LinkColumn("Link", display_text="View →"),
        "Price (SEK)": st.column_config.NumberColumn(format="%d"),
        "Predicted (SEK)": st.column_config.NumberColumn(format="%d"),
        "Discount %": st.column_config.NumberColumn(format="%.1f%%"),
        "Discount (SEK)": st.column_config.NumberColumn(format="%d"),
        "Mileage (km)": st.column_config.NumberColumn(format="%d"),
    },
    hide_index=True,
    width="stretch",
    height=600,
    on_select="rerun",
    selection_mode="single-row",
    key="deals_table"
)

# Update session state when row is selected
if selection and selection.selection and selection.selection.rows:
    selected_idx = selection.selection.rows[0]
    new_selected = table_df.iloc[selected_idx]["Reg. Nr"]
    if st.session_state.get("selected_car") != new_selected:
        st.session_state["selected_car"] = new_selected
        st.rerun()

# =====================
# REGRESSION COEFFICIENTS
# =====================
with st.expander("📈 Show Regression Coefficients (Log-Linear Model)"):
    coef_df = get_coefficients_df(model_log)

    st.markdown("**Significance:** *** p<0.001, ** p<0.01, * p<0.05, . p<0.1")
    st.dataframe(coef_df, hide_index=True, width="stretch")

    # Interpretation
    st.markdown("#### Key Interpretations:")

    mileage_coef = model_log.params.get("mileage_10k", 0)
    mileage_sq_coef = model_log.params.get("mileage_10k_sq", 0)
    mileage_cu_coef = model_log.params.get("mileage_10k_cu", 0)
    franchise_coef = model_log.params.get("franchise_approved", 0)

    st.markdown(f"""
    - **Mileage (linear):** {(np.exp(mileage_coef) - 1) * 100:.1f}% per 10,000 km
    - **Mileage (quadratic):** {(np.exp(mileage_sq_coef) - 1) * 100:.2f}% (diminishing depreciation)
    - **Mileage (cubic):** {(np.exp(mileage_cu_coef) - 1) * 100:.3f}% (complex curve)
    - **Franchise Approved:** {(np.exp(franchise_coef) - 1) * 100:.1f}% premium for certified cars
    """)

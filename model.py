"""
Price prediction model for Volvo XC60 - Finding good deals.

Compares Linear vs Log-Linear OLS models to identify cars priced below their fair value.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
from pathlib import Path

# Paths
DATA_FILE = Path("data/volvo_xc60_cleaned.csv")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def load_data():
    """Load and prepare data for modeling."""
    df = pd.read_csv(DATA_FILE)

    # Add location column if it doesn't exist (for backward compatibility)
    if "location" not in df.columns:
        df["location"] = None

    # Scale mileage to 10,000 km units for interpretability
    df["mileage_10k"] = df["mileage"] / 10000

    # Add mileage squared and cubed for complex depreciation curve
    df["mileage_10k_sq"] = df["mileage_10k"] ** 2
    df["mileage_10k_cu"] = df["mileage_10k"] ** 3

    # Create log price
    df["log_price"] = np.log(df["price"])

    # Fill missing franchise_approved with False, convert to int for regression
    df["franchise_approved"] = df["franchise_approved"].fillna(False)
    df["franchise_approved"] = df["franchise_approved"].astype(int)

    # Reference categories (most common):
    # engine_code: T6, fuel_type: Plugin Hybrid, driving_type: AWD

    return df


def fit_models(df):
    """Fit both Linear and Log-Linear OLS models."""

    # Continuous: mileage_10k, mileage_10k_sq, mileage_10k_cu (polynomial), horsepower, franchise_approved
    # Fixed effects: model_year, engine_code, fuel_type, driving_type
    # Dropped: transmission (99% Automatic - no predictive value)

    formula_linear = """price ~ mileage_10k + mileage_10k_sq + mileage_10k_cu + horsepower + franchise_approved +
        C(model_year) +
        C(engine_code, Treatment('T6')) +
        C(fuel_type, Treatment('Plugin Hybrid')) +
        C(driving_type, Treatment('AWD'))"""

    formula_log = """log_price ~ mileage_10k + mileage_10k_sq + mileage_10k_cu + horsepower + franchise_approved +
        C(model_year) +
        C(engine_code, Treatment('T6')) +
        C(fuel_type, Treatment('Plugin Hybrid')) +
        C(driving_type, Treatment('AWD'))"""

    # Fit models
    model_linear = smf.ols(formula_linear, data=df).fit()
    model_log = smf.ols(formula_log, data=df).fit()

    return model_linear, model_log


def compare_models(model_linear, model_log, df):
    """Compare model fit statistics."""

    # For log model, calculate comparable R² using actual prices
    log_predicted = np.exp(model_log.fittedvalues)
    ss_res_log = np.sum((df["price"] - log_predicted) ** 2)
    ss_tot = np.sum((df["price"] - df["price"].mean()) ** 2)
    r2_log_comparable = 1 - ss_res_log / ss_tot

    comparison = {
        "Linear Model": {
            "R²": model_linear.rsquared,
            "Adj. R²": model_linear.rsquared_adj,
            "AIC": model_linear.aic,
            "BIC": model_linear.bic,
            "RMSE": np.sqrt(model_linear.mse_resid),
        },
        "Log-Linear Model": {
            "R² (log scale)": model_log.rsquared,
            "Adj. R² (log scale)": model_log.rsquared_adj,
            "R² (price scale)": r2_log_comparable,
            "AIC": model_log.aic,
            "BIC": model_log.bic,
            "RMSE (log scale)": np.sqrt(model_log.mse_resid),
        }
    }

    return comparison


def calculate_deal_scores(df, model_linear, model_log):
    """Calculate how much each car deviates from predicted price."""

    # Linear model: residual in SEK
    df["predicted_linear"] = model_linear.fittedvalues
    df["residual_linear"] = df["price"] - df["predicted_linear"]
    df["discount_sek"] = -df["residual_linear"]  # Positive = good deal

    # Log model: residual as percentage
    df["predicted_log"] = model_log.fittedvalues
    df["predicted_price_log"] = np.exp(df["predicted_log"])
    df["residual_log"] = df["log_price"] - df["predicted_log"]
    df["discount_pct"] = (1 - np.exp(df["residual_log"])) * 100  # Positive = good deal

    return df


def create_deal_ranking(df):
    """Create ranking of best deals."""

    # Filter out rows with NaN predictions (missing categories)
    valid_df = df.dropna(subset=["discount_pct", "predicted_price_log"])

    # Sort by percentage discount (log model)
    ranking = valid_df.sort_values("discount_pct", ascending=False)

    # Select relevant columns
    cols = [
        "registration_number", "price", "predicted_price_log",
        "discount_pct", "discount_sek",
        "model_year", "mileage", "horsepower", "engine_code", "fuel_type",
        "driving_type", "model_variant_original"
    ]

    ranking = ranking[cols].copy()
    ranking.columns = [
        "Reg. Nr", "Actual Price", "Predicted Price",
        "Discount %", "Discount SEK",
        "Year", "Mileage (km)", "HP", "Engine", "Fuel",
        "Drive", "Model Variant"
    ]

    # Round for readability
    ranking["Predicted Price"] = ranking["Predicted Price"].round(0).astype(int)
    ranking["Discount %"] = ranking["Discount %"].round(1)
    ranking["Discount SEK"] = ranking["Discount SEK"].round(0).astype(int)

    return ranking


def plot_diagnostics(model_linear, model_log, df):
    """Create diagnostic plots for both models."""

    fig, axes = plt.subplots(2, 3, figsize=(14, 9))

    # Linear model diagnostics
    # Residuals vs Fitted
    axes[0, 0].scatter(model_linear.fittedvalues, model_linear.resid, alpha=0.5, s=20)
    axes[0, 0].axhline(y=0, color='r', linestyle='--')
    axes[0, 0].set_xlabel("Fitted Values (SEK)")
    axes[0, 0].set_ylabel("Residuals (SEK)")
    axes[0, 0].set_title("Linear: Residuals vs Fitted")

    # Q-Q plot
    from scipy import stats
    stats.probplot(model_linear.resid, dist="norm", plot=axes[0, 1])
    axes[0, 1].set_title("Linear: Q-Q Plot")

    # Histogram of residuals
    axes[0, 2].hist(model_linear.resid, bins=30, edgecolor='black', alpha=0.7)
    axes[0, 2].set_xlabel("Residuals (SEK)")
    axes[0, 2].set_title("Linear: Residual Distribution")

    # Log-Linear model diagnostics
    # Residuals vs Fitted
    axes[1, 0].scatter(model_log.fittedvalues, model_log.resid, alpha=0.5, s=20)
    axes[1, 0].axhline(y=0, color='r', linestyle='--')
    axes[1, 0].set_xlabel("Fitted Values (log price)")
    axes[1, 0].set_ylabel("Residuals (log)")
    axes[1, 0].set_title("Log-Linear: Residuals vs Fitted")

    # Q-Q plot
    stats.probplot(model_log.resid, dist="norm", plot=axes[1, 1])
    axes[1, 1].set_title("Log-Linear: Q-Q Plot")

    # Histogram of residuals
    axes[1, 2].hist(model_log.resid, bins=30, edgecolor='black', alpha=0.7)
    axes[1, 2].set_xlabel("Residuals (log)")
    axes[1, 2].set_title("Log-Linear: Residual Distribution")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "model_diagnostics.png", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR / 'model_diagnostics.png'}")


def plot_deals(df, n_highlight=10):
    """Create scatter plot highlighting best deals."""

    # Filter out NaN predictions for plotting
    plot_df = df.dropna(subset=["discount_pct"])

    fig, ax = plt.subplots(figsize=(12, 8))

    # Color by deal score
    colors = plot_df["discount_pct"]
    scatter = ax.scatter(plot_df["mileage"], plot_df["price"], c=colors,
                         cmap="RdYlGn", alpha=0.6, s=50)

    # Highlight top deals
    top_deals = plot_df.nlargest(n_highlight, "discount_pct")
    ax.scatter(top_deals["mileage"], top_deals["price"],
               facecolors='none', edgecolors='blue', s=150, linewidths=2,
               label=f"Top {n_highlight} Deals")

    # Annotate top deals
    for _, row in top_deals.iterrows():
        ax.annotate(f"{row['registration_number']}\n{row['discount_pct']:.0f}% off",
                    (row["mileage"], row["price"]),
                    textcoords="offset points", xytext=(5, 5),
                    fontsize=8, alpha=0.8)

    ax.set_xlabel("Mileage (km)")
    ax.set_ylabel("Price (SEK)")
    ax.set_title("Volvo XC60 Deals: Green = Underpriced, Red = Overpriced")
    ax.legend()

    # Format axes
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}k'))
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1000:.0f}k'))

    plt.colorbar(scatter, label="Discount %")
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "best_deals.png", dpi=150)
    plt.close()
    print(f"Saved: {OUTPUT_DIR / 'best_deals.png'}")


def save_model_summary(model_linear, model_log, comparison):
    """Save model comparison and coefficients."""

    with open(OUTPUT_DIR / "model_comparison.txt", "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("VOLVO XC60 PRICE MODEL COMPARISON\n")
        f.write("=" * 80 + "\n\n")

        # Model comparison
        f.write("MODEL FIT STATISTICS\n")
        f.write("-" * 40 + "\n")
        for model_name, stats in comparison.items():
            f.write(f"\n{model_name}:\n")
            for stat, value in stats.items():
                f.write(f"  {stat}: {value:.4f}\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("LINEAR MODEL RESULTS (price in SEK)\n")
        f.write("=" * 80 + "\n")
        f.write(model_linear.summary().as_text())

        f.write("\n\n" + "=" * 80 + "\n")
        f.write("LOG-LINEAR MODEL RESULTS (log price)\n")
        f.write("=" * 80 + "\n")
        f.write(model_log.summary().as_text())

        # Coefficient interpretation for log model
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("LOG-LINEAR COEFFICIENT INTERPRETATION (% change in price)\n")
        f.write("=" * 80 + "\n")
        for name, coef in model_log.params.items():
            pct_change = (np.exp(coef) - 1) * 100
            if name == "Intercept":
                f.write(f"  Base price (T6, Plugin Hybrid, AWD, age=0, mileage=0): {np.exp(coef):,.0f} SEK\n")
            elif name == "mileage_10k":
                f.write(f"  {name}: {pct_change:+.1f}% per 10k km (linear effect)\n")
            elif name == "mileage_10k_sq":
                f.write(f"  {name}: {pct_change:+.2f}% (quadratic - diminishing depreciation)\n")
            elif name == "franchise_approved":
                f.write(f"  {name}: {pct_change:+.1f}% (certified car premium)\n")
            else:
                f.write(f"  {name}: {pct_change:+.1f}%\n")

    print(f"Saved: {OUTPUT_DIR / 'model_comparison.txt'}")


def main():
    print("=" * 60)
    print("Volvo XC60 Price Model")
    print("=" * 60)

    # Load data
    print("\nLoading data...")
    df = load_data()
    print(f"  Loaded {len(df)} cars")

    # Fit models
    print("\nFitting models...")
    model_linear, model_log = fit_models(df)
    print("  Linear model: done")
    print("  Log-Linear model: done")

    # Compare models
    print("\nModel comparison:")
    comparison = compare_models(model_linear, model_log, df)
    print(f"  Linear R²: {comparison['Linear Model']['R²']:.4f}")
    print(f"  Log-Linear R² (log scale): {comparison['Log-Linear Model']['R² (log scale)']:.4f}")
    print(f"  Log-Linear R² (price scale): {comparison['Log-Linear Model']['R² (price scale)']:.4f}")

    # Calculate deal scores
    print("\nCalculating deal scores...")
    df = calculate_deal_scores(df, model_linear, model_log)

    # Create ranking
    ranking = create_deal_ranking(df)
    ranking.to_csv(OUTPUT_DIR / "deal_ranking.csv", index=False)
    print(f"Saved: {OUTPUT_DIR / 'deal_ranking.csv'}")

    # Print top 10 deals
    print("\n" + "=" * 60)
    print("TOP 10 BEST DEALS")
    print("=" * 60)
    top10 = ranking.head(10)
    for i, (_, row) in enumerate(top10.iterrows(), 1):
        print(f"\n{i}. {row['Reg. Nr']} - {row['Engine']} ({row['Year']})")
        print(f"   Price: {row['Actual Price']:,} SEK")
        print(f"   Fair value: {row['Predicted Price']:,} SEK")
        print(f"   Discount: {row['Discount %']:.1f}% ({row['Discount SEK']:,} SEK)")
        print(f"   Mileage: {row['Mileage (km)']:,} km")

    # Save outputs
    print("\n" + "=" * 60)
    print("Saving outputs...")
    save_model_summary(model_linear, model_log, comparison)
    plot_diagnostics(model_linear, model_log, df)
    plot_deals(df)

    print("\nDone!")


if __name__ == "__main__":
    main()

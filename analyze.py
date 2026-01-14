"""
Scatter plot of price vs mileage with regression line.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Load data
df = pd.read_csv('data/volvo_xc60_listings.csv')

# Filter out rows with missing values
df_clean = df.dropna(subset=['price', 'mileage'])

x = df_clean['mileage'].values
y = df_clean['price'].values

# Fit linear regression
coeffs = np.polyfit(x, y, 1)
slope, intercept = coeffs
regression_line = np.poly1d(coeffs)

# Create scatter plot
plt.figure(figsize=(10, 6))
plt.scatter(x, y, alpha=0.5, s=30, label='Cars')

# Add regression line
x_line = np.linspace(x.min(), x.max(), 100)
plt.plot(x_line, regression_line(x_line), 'r-', linewidth=2,
         label=f'Regression: price = {slope:,.0f} × mileage + {intercept:,.0f}')

plt.xlabel('Mileage (Swedish mil)')
plt.ylabel('Price (SEK)')
plt.title('Volvo XC60 Price vs Mileage')
plt.legend()
plt.grid(True, alpha=0.3)

# Format y-axis with thousands separator
plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}'))

# Save to output folder
output_dir = Path('output')
output_dir.mkdir(exist_ok=True)
output_path = output_dir / 'price_vs_mileage.png'
plt.savefig(output_path, dpi=150, bbox_inches='tight')
plt.close()

print(f"Plot saved to: {output_path}")
print(f"\nRegression equation:")
print(f"  Price = {slope:,.0f} × Mileage + {intercept:,.0f}")
print(f"\nInterpretation:")
print(f"  Each additional mil reduces price by ~{abs(slope):,.0f} SEK")

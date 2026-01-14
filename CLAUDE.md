# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a **used car deal finder** for Volvo XC60 vehicles in the Swedish market. The system scrapes listings from multiple dealership websites, builds price prediction models using regression analysis, and identifies cars priced significantly below their fair market value.

**Data Science Pipeline:**
1. **Scraping:** Collect listings from 3 Swedish dealership websites
2. **Cleaning:** Merge, deduplicate, standardize, and engineer features
3. **Modeling:** Build OLS regression models to predict fair prices
4. **Analysis:** Identify underpriced vehicles (best deals)

## Core Scripts

### Data Collection (Scrapers)

#### scraper.py
**Source:** Volvo Selekt (official Volvo certified pre-owned marketplace)
- URL: https://selekt.volvocars.se/sv-se/store/all/vehicles?models=XC60
- **Primary data source** (preferred for deduplication)
- Extracts: price, model year, mileage, fuel type, engine power, transmission, color, registration number
- Handles: pagination, cookie consent, infinite scroll, "Load more" buttons
- Output: `data/volvo_xc60_listings.csv`

**Run:** `python scraper.py` (headless) or `python scraper.py --visible` (visible browser)

#### scraper_bilia.py
**Source:** Bilia dealership network
- URL: https://www.bilia.se/bilar/sok-bil/?brand=volvo&model=xc60
- Additional fields: drive wheels, electric type, engine name, location
- Clicks "Motor och miljö" tab to extract detailed specifications
- Output: `data/bilia_xc60_listings.csv`

**Run:** `python scraper_bilia.py` (headless) or `python scraper_bilia.py --visible` (visible browser)

#### scraper_rejmes.py
**Source:** Rejmes dealership
- URL: https://rejmes.se/bilar/begagnade-bilar/begagnade-volvo/begagnade-volvo-xc60/
- Uses "Visa fler bilar" button to load all listings
- Output: `data/rejmes_xc60_listings.csv`

**Run:** `python scraper_rejmes.py` (headless) or `python scraper_rejmes.py --visible` (visible browser)

**Scraper Features:**
- Robust handling of dynamic content (Selenium WebDriver)
- Cookie consent automation
- Multiple selector strategies for resilience
- Error recovery and logging
- Automatic ChromeDriver management (webdriver-manager)

### Data Processing

#### clean_data.py
Data cleaning and integration pipeline:

**Operations:**
1. **Merge datasets** from Volvo Selekt and Bilia (Rejmes support coming soon)
2. **Deduplicate** by registration number (Swedish format: ABC123)
   - Prefers Volvo Selekt data when duplicates exist
   - Hash-based detection across sources
3. **Standardize categories:**
   - Swedish → English translations
   - Fuel types: "Laddhybrid" → "Plugin Hybrid", "Bensin" → "Petrol", "Diesel" → "Diesel", "Mildhybrid" → "Mild Hybrid"
   - Transmission: "Automat" → "Automatic", "Manuell" → "Manual"
   - Drive type: "4WD/AWD" → "AWD", "FWD" → "FWD"
4. **Extract engine codes** (T5, T6, T8, B4, B5, D4, D5) from model_variant strings
5. **Infer missing engine codes** from horsepower patterns
6. **Feature engineering:**
   - `age` = current year - model_year
   - `horsepower` = extracted from "engine_power" field (removes "hk" suffix)
7. **Data validation** and quality checks

**Output:** `data/volvo_xc60_cleaned.csv` (cleaned and merged dataset for modeling)

**Run:** `python clean_data.py`

### Modeling and Analysis

#### model.py
Price prediction and deal identification using OLS regression:

**Models:**
1. **Linear model:**
   ```
   price = β₀ + β₁·mileage + β₂·horsepower + fixed_effects + ε
   ```

2. **Log-linear model:**
   ```
   log(price) = β₀ + β₁·mileage + β₂·horsepower + fixed_effects + ε
   ```

**Fixed Effects (Categorical Variables):**
- `model_year` (2015-2026)
- `engine_code` (T5, T6, T8, B4, B5, D4, D5)
- `fuel_type` (Plugin Hybrid, Petrol, Diesel, Mild Hybrid, Electric)
- `transmission` (Automatic, Manual)
- `driving_type` (AWD, FWD)

**Reference Categories:**
- Engine: T6 (high-performance gasoline)
- Fuel: Plugin Hybrid
- Transmission: Automatic
- Drive: AWD

**Deal Scoring:**
- `predicted_price` = model prediction for each car
- `discount_pct` = (predicted - actual) / predicted × 100
- `discount_sek` = predicted - actual
- **Best deals** = highest discount_pct (cars priced well below fair value)

**Outputs:**
- `output/deal_ranking.csv` - All cars ranked by discount percentage (top deals first)
- `output/model_comparison.txt` - Model statistics (R², AIC, BIC, RMSE, coefficients)
- `output/model_diagnostics.png` - Residual plots (4 panels: residuals vs fitted, Q-Q plot, scale-location, residuals vs leverage)
- `output/best_deals.png` - Scatter plot (price vs mileage) with top 10 deals highlighted

**Run:** `python model.py`

#### analyze.py
Simple exploratory visualization:
- Scatter plot: price vs mileage
- Linear regression trend line
- Shows negative correlation (higher mileage → lower price)

**Output:** `output/price_vs_mileage.png`

**Run:** `python analyze.py`

### Utilities

#### test_price_extraction.py
Debug tool for testing price extraction from detail pages. Useful when scraper fails to extract prices correctly.

**Run:** `python test_price_extraction.py`

## Data Schema

### Key Fields

**Raw Data (from scrapers):**
- `registration_number` - Unique car identifier (Swedish format: ABC123)
- `price` - Listing price in SEK (Swedish Kronor)
- `model_year` - Manufacturing year (e.g., 2022)
- `mileage` - Odometer reading in kilometers
- `fuel_type` - Laddhybrid, Bensin, Diesel, Mildhybrid, El (Swedish)
- `engine_power` - e.g., "250 hk" (hk = horsepower in Swedish)
- `transmission` - Automat, Manuell (Swedish)
- `driving_type` - 4WD/AWD, FWD
- `color` - Exterior color
- `model_variant` - Full specification string (contains engine code)

**Cleaned Data (after clean_data.py):**
- All raw fields (translated to English)
- `engine_code` - T5, T6, T8, B4, B5, D4, D5 (extracted/inferred)
- `horsepower` - Numeric value (e.g., 250)
- `age` - Current year - model_year

**Model Outputs (from model.py):**
- `predicted_price_linear` - Linear model prediction
- `predicted_price_loglinear` - Log-linear model prediction
- `discount_pct` - Percentage below fair value
- `discount_sek` - Absolute discount in SEK

### Engine Codes

Volvo XC60 engine codes and their characteristics:
- **T5** - 2.0L turbocharged gasoline (~250 hp)
- **T6** - 2.0L supercharged + turbocharged gasoline (~320 hp)
- **T8** - 2.0L plugin hybrid (gasoline + electric, ~390 hp)
- **B4** - 2.0L mild hybrid gasoline (~197 hp)
- **B5** - 2.0L mild hybrid gasoline (~250 hp)
- **D4** - 2.0L diesel (~190 hp)
- **D5** - 2.0L diesel (~235 hp)

## Directory Structure

```
volvoxc60/
├── CLAUDE.md                      # This file
├── requirements.txt               # Python dependencies
│
├── scraper.py                     # Volvo Selekt scraper
├── scraper_bilia.py               # Bilia scraper
├── scraper_rejmes.py              # Rejmes scraper (WIP)
├── test_price_extraction.py       # Debug utility
│
├── clean_data.py                  # Data cleaning & merging
├── model.py                       # Price prediction models
├── analyze.py                     # Basic visualization
│
├── data/                          # Raw and processed data
│   ├── volvo_xc60_listings.csv    # Volvo Selekt raw data
│   ├── bilia_xc60_listings.csv    # Bilia raw data
│   ├── rejmes_xc60_listings.csv   # Rejmes raw data
│   └── volvo_xc60_cleaned.csv     # Cleaned & combined data
│
└── output/                        # Model results & visualizations
    ├── deal_ranking.csv           # Ranked list of best deals
    ├── model_comparison.txt       # Model statistics
    ├── model_diagnostics.png      # Residual plots
    ├── best_deals.png             # Scatter plot with deals highlighted
    └── price_vs_mileage.png       # Basic price/mileage plot
```

## Technologies

**Web Scraping:**
- Selenium WebDriver (browser automation)
- webdriver-manager (automatic ChromeDriver management)
- Chrome/Chromium (headless mode supported)

**Data Processing:**
- pandas (data manipulation, CSV I/O)
- re (regex for pattern extraction)

**Statistical Modeling:**
- statsmodels (OLS regression)
- numpy (numerical operations, log transforms)

**Visualization:**
- matplotlib (scatter plots, histograms, Q-Q plots)
- scipy.stats (statistical tests for diagnostics)

## Typical Workflow

### Complete Pipeline

1. **Scrape fresh data from all sources:**
   ```bash
   python scraper.py
   python scraper_bilia.py
   python scraper_rejmes.py
   ```
   This updates the raw CSV files in `data/`

2. **Clean and merge datasets:**
   ```bash
   python clean_data.py
   ```
   Creates `data/volvo_xc60_cleaned.csv`

3. **Build models and identify deals:**
   ```bash
   python model.py
   ```
   Generates:
   - `output/deal_ranking.csv` (sorted by best deals)
   - `output/model_comparison.txt` (model statistics)
   - `output/model_diagnostics.png` (diagnostic plots)
   - `output/best_deals.png` (visualization)

4. **Review results:**
   - Open `output/deal_ranking.csv` in Excel
   - Sort by `discount_pct` (descending) to see top deals
   - Check `model_comparison.txt` for model performance
   - Review `model_diagnostics.png` for model validity

### Quick Updates

**Just update Volvo Selekt data (fastest source):**
```bash
python scraper.py
python clean_data.py
python model.py
```

**Debug scraping issues:**
```bash
python scraper.py --visible    # Watch browser actions
python test_price_extraction.py    # Test price extraction
```

**Quick price analysis:**
```bash
python analyze.py    # Simple price vs mileage plot
```

## Key Insights

### Deduplication Strategy
- Cars appear on multiple dealer websites (same registration_number)
- Volvo Selekt data is **preferred** when duplicates exist (official source, most complete)
- Hash-based detection ensures no missed duplicates

### Model Interpretation
- **Negative mileage coefficient:** Higher mileage → lower price (expected)
- **Positive horsepower coefficient:** More power → higher price (expected)
- **Model year fixed effects:** Newer cars → higher prices (controlled for age)
- **Engine code fixed effects:** T8 (plugin hybrid) commands premium over D4/D5 (diesel)
- **Log-linear model:** Often better fit for price data (reduces heteroscedasticity)

### Deal Identification
- **Discount % > 10%** = strong deal candidate
- **Discount SEK > 50,000** = significant absolute savings
- False positives possible:
  - Undisclosed damage/issues
  - Missing features (basic trim vs luxury)
  - Incorrect data entry
  - Regional pricing differences
- **Always verify deals manually** before purchase

### Market Patterns
- Plugin hybrids (T8) hold value well
- Diesel (D4/D5) depreciates faster (shift away from diesel in Sweden)
- AWD preferred (price premium over FWD)
- Mileage heavily impacts price (non-linear relationship)

## Maintenance

### Adding New Data Sources

1. **Create new scraper** (e.g., `scraper_newsite.py`):
   - Copy structure from `scraper.py`
   - Update URL and selectors
   - Test with `--visible` flag
   - Verify CSV output format matches others

2. **Update clean_data.py**:
   - Add new CSV to merge logic
   - Handle any new field names
   - Test deduplication with new source

3. **Document in CLAUDE.md**:
   - Add to scrapers section
   - Note any special handling

### Improving Models

**Add more features:**
- Interior color (black interiors may sell faster)
- Equipment packages (Inscription, R-Design)
- Service history indicators
- Number of previous owners

**Try different models:**
- Random Forest (capture non-linearities)
- XGBoost (better predictive performance)
- Polynomial features (mileage², mileage³)

**Validation:**
- Train/test split (temporal: older listings = train, newer = test)
- Cross-validation (k-fold)
- Out-of-sample prediction accuracy

### Monitoring Data Quality

Check these regularly:
- Missing values in key fields (price, mileage, model_year)
- Outliers (suspiciously low/high prices)
- Duplicate detection rate (should be stable)
- Scraper success rate (listings found vs expected)

## Troubleshooting

### Scrapers Failing

**Issue:** "No listings found"
- Check if website structure changed (inspect selectors)
- Verify URL still works
- Check cookie consent handling
- Run with `--visible` to watch browser

**Issue:** "Price extraction failed"
- Use `test_price_extraction.py` to debug
- Website may have changed HTML structure
- Check for currency symbols, thousands separators

**Issue:** "ChromeDriver version mismatch"
- Update webdriver-manager: `pip install --upgrade webdriver-manager`
- Clear cache: delete `~/.wdm/` folder

### Model Issues

**Issue:** "Low R² (< 0.6)"
- Add more features (equipment, condition indicators)
- Check for outliers (remove or winsorize)
- Try log-linear model instead of linear

**Issue:** "High residuals for certain cars"
- Missing important features (luxury trim, special editions)
- Data entry errors (verify outliers manually)
- Regional pricing not captured

**Issue:** "Heteroscedasticity in residuals"
- Use log-linear model (stabilizes variance)
- Consider robust standard errors
- Check for non-linear relationships

## Future Enhancements

**Data Collection:**
- Add more dealership websites (Hedin Bil, Biltorget, Blocket)
- Scrape historical data (price changes over time)
- Capture additional features (service history, accident reports)

**Modeling:**
- Time series analysis (price depreciation curves)
- Market segmentation (luxury vs base models)
- Seasonal adjustments (prices vary by month)

**Automation:**
- Schedule daily scraping (cron job or Task Scheduler)
- Email alerts for new top deals
- Database backend (replace CSV files)

**User Interface:**
- Web dashboard (Flask/Streamlit)
- Interactive filters (price range, mileage, features)
- Deal notifications

## Notes

- All prices in SEK (Swedish Kronor)
- Mileage in kilometers
- Registration numbers follow Swedish format (ABC123)
- Market: Sweden only (right-hand drive)
- Focus: Used Volvo XC60 (all generations, all trims)

"""
Data cleaning script for Volvo XC60 price prediction model.
Prepares raw scraped data from multiple sources for regression analysis.
"""

import pandas as pd
import re
from pathlib import Path

# Input files
VOLVO_SELEKT_FILE = Path("data/volvo_xc60_listings.csv")
BILIA_FILE = Path("data/bilia_xc60_listings.csv")
REJMES_FILE = Path("data/rejmes_xc60_listings.csv")

# Output file
OUTPUT_FILE = Path("data/volvo_xc60_cleaned.csv")

# Comprehensive Swedish cities list for location validation
SWEDISH_CITIES = {
    # Major cities (population > 50k)
    'STOCKHOLM', 'GÖTEBORG', 'MALMÖ', 'UPPSALA', 'VÄSTERÅS', 'ÖREBRO',
    'LINKÖPING', 'HELSINGBORG', 'NORRKÖPING', 'JÖNKÖPING', 'UMEÅ',
    'LUND', 'BORÅS', 'ESKILSTUNA', 'GÄVLE', 'SÖDERTÄLJE', 'KARLSTAD',
    'HALMSTAD', 'VÄXJÖ', 'SUNDSVALL', 'TROLLHÄTTAN', 'ÖSTERSUND',
    'FALUN', 'SKELLEFTEÅ', 'KRISTIANSTAD', 'KALMAR', 'KUNGÄLV',
    # Medium cities (population 20k-50k)
    'LIDKÖPING', 'SKÖVDE', 'UDDEVALLA', 'MOTALA', 'TRELLEBORG',
    'KARLSKRONA', 'VARBERG', 'ÄNGELHOLM', 'NYKÖPING', 'SANDVIKEN',
    'LIDINGÖ', 'BOLLNÄS', 'ÖRNSKÖLDSVIK', 'LANDSKRONA', 'YSTAD',
    # Dealership cities identified in data
    'LINDESBERG', 'FINSPÅNG', 'MJÖLBY', 'HALLSBERG', 'ÅTVIDABERG',
    'UPPLANDS VÄSBY', 'TÄBY', 'SOLLENTUNA', 'SOLNA', 'NACKA',
    'JÄGERSRO', 'KUNGSÄNGEN', 'HANINGE', 'SISJÖN', 'KISTA',
    'SEGELTORP', 'HUDDINGE', 'MÄRSTA', 'UPPLANDS BRO', 'TIMRÅ',
    'ARÖD', 'ÖSTHAMMAR', 'ARVIKA', 'SALA', 'VARA',
    'LAHOLM', 'ENKÖPING', 'HAMMARBY SJÖSTAD', 'VIMMERBY', 'LJUSDAL',
    'HUDIKSVALL', 'VALLENTUNA', 'ESLÖV', 'KRISTINEHAMN',
    'ALINGSÅS', 'ÅMÅL', 'DINGLE', 'FALKÖPING', 'LYSEKIL',
    'MARIESTAD', 'MELLERUD', 'STRÖMSTAD', 'VÄNERSBORG',
    'HÄRNÖSAND', 'KALIX', 'STRÖMSUND', 'NORRTÄLJE',
    'SANDVIKEN', 'SÖDERHAMN', 'VISBY', 'KÖPING', 'STRÄNGNÄS',
    'KUNGSBACKA', 'STENUNGSUND', 'BRO', 'VÄRNHEM', 'KUNGENS KURVA',
    'SÄVEDALEN'
}


def is_valid_swedish_city(text):
    """Validate if text is a known Swedish city.

    Args:
        text: City name to validate (case-insensitive)

    Returns:
        bool: True if text matches a known Swedish city
    """
    if not text:
        return False
    text_upper = str(text).upper().strip()
    return text_upper in SWEDISH_CITIES


def extract_engine_code(model_variant):
    """Extract engine code (T5, T6, T8, B4, B5, D4, D5) from model variant string."""
    if pd.isna(model_variant):
        return None
    # Look for patterns like T5, T6, T8, B4, B5, D4, D5
    match = re.search(r'\b([TBD]\d)\b', model_variant)
    if match:
        return match.group(1)
    return None


def infer_engine_from_horsepower(hp):
    """Infer engine code from horsepower when model variant is unclear.

    Typical ranges:
    - B4: ~197 hp
    - D5: ~235 hp
    - B5/T5: ~250 hp
    - T6: 252-349 hp
    - T8: 391-455 hp
    """
    if pd.isna(hp):
        return None
    if hp >= 380:
        return "T8"
    elif hp >= 250 and hp < 380:
        return "T6"
    elif hp >= 230 and hp < 250:
        return "B5"  # or T5, but B5 more common in recent years
    elif hp < 230:
        return "B4"
    return None


def extract_horsepower(engine_power):
    """Extract numeric horsepower from string like '455 Hk' or '350 hk / 261 kW'."""
    if pd.isna(engine_power):
        return None
    match = re.search(r'(\d+)\s*[Hh][Kk]', str(engine_power))
    if match:
        return int(match.group(1))
    return None


def clean_fuel_type(fuel_type, electric_type=None):
    """Standardize fuel type categories to English."""
    if pd.isna(fuel_type):
        return None
    fuel_lower = str(fuel_type).lower()

    # Check electric type first if available
    if electric_type and not pd.isna(electric_type):
        electric_lower = str(electric_type).lower()
        if "laddhybrid" in electric_lower:
            return "Plugin Hybrid"
        elif "elbil" in electric_lower:
            return "Electric"
        elif "mildhybrid" in electric_lower:
            return "Mild Hybrid"

    # Check fuel type string (order matters - check specific terms before generic ones)
    if "laddhybrid" in fuel_lower or "plug" in fuel_lower:
        return "Plugin Hybrid"
    elif "bensin+el" in fuel_lower or "bensin + el" in fuel_lower:
        return "Plugin Hybrid"  # Bilia's format for plug-in hybrids
    elif "mildhybrid" in fuel_lower:
        return "Mild Hybrid"
    elif "hybrid" in fuel_lower:
        return "Hybrid"
    elif "el" in fuel_lower and "diesel" not in fuel_lower and "bensin" not in fuel_lower:
        return "Electric"
    elif "diesel" in fuel_lower:
        return "Diesel"
    elif "bensin" in fuel_lower:
        return "Petrol"
    return fuel_type


def clean_transmission(transmission):
    """Standardize transmission categories."""
    if pd.isna(transmission) or transmission == "":
        return None
    trans_lower = str(transmission).lower()
    if "auto" in trans_lower:
        return "Automatic"
    elif "manu" in trans_lower:
        return "Manual"
    return transmission


def clean_driving_type(driving_type):
    """Standardize driving type categories."""
    if pd.isna(driving_type) or driving_type == "":
        return None
    drive_lower = str(driving_type).lower()
    if "fyrhjuls" in drive_lower or "awd" in drive_lower or "4wd" in drive_lower:
        return "AWD"
    elif "framhjuls" in drive_lower or "fwd" in drive_lower:
        return "FWD"
    return driving_type


def normalize_location(location):
    """Normalize Swedish city names - extract clean city from dealer text.

    Handles patterns:
    - "DEALER - CITY" → extract CITY (second part)
    - "CITY - STREET" → extract CITY (validate first part is city)
    - "CITY" → keep as-is
    - Encoding fixes for Swedish characters (Å, Ä, Ö)

    Args:
        location: Raw location string from scrapers

    Returns:
        str: Clean city name in uppercase, or None if empty/invalid
    """
    if pd.isna(location) or location == "":
        return None

    location = str(location).upper().strip()

    # Smart encoding fix: Try all possible Swedish characters for � and validate against cities
    if '�' in location:
        # Try each possible replacement
        for replacement_char in ['Ö', 'Ä', 'Å']:
            test_location = location.replace('�', replacement_char)
            # Check if this makes a valid city (either the full string or parts of it)
            if is_valid_swedish_city(test_location):
                location = test_location
                break
            # Also check if it's part of a "DEALER - CITY" format
            if ' - ' in test_location:
                parts = test_location.split(' - ')
                for part in parts:
                    if is_valid_swedish_city(part.strip()):
                        location = test_location
                        break
            # Check individual words
            for word in test_location.split():
                if is_valid_swedish_city(word.strip(',-')):
                    location = test_location
                    break
            if '�' not in location:  # If we found a match, break outer loop
                break

    # Additional encoding fixes
    location = location.replace('\ufffd', 'Ö')  # Unicode replacement character
    location = location.replace('Ø', 'Ö')  # Norwegian Ø

    # Strategy 1: Handle "DEALER - CITY" or "CITY - STREET" format
    if ' - ' in location:
        parts = [p.strip() for p in location.split(' - ')]

        # Check which part is a valid city
        # Try second part first (most common: "DEALER - CITY")
        if len(parts) >= 2 and is_valid_swedish_city(parts[1]):
            return parts[1].upper()

        # Fallback: try first part (less common: "CITY - STREET")
        if is_valid_swedish_city(parts[0]):
            return parts[0].upper()

        # No valid city found - take second part anyway (likely city)
        # This handles new cities not yet in our list
        if len(parts) >= 2:
            return parts[1].upper()

        # Last resort: take first part
        return parts[0].upper()

    # Strategy 2: Handle "Bilia [CITY] Volvo" format
    # (shouldn't happen after scraper parsing, but defensive)
    if 'BILIA' in location and 'VOLVO' in location:
        match = re.search(r'BILIA\s+([A-ZÅÄÖ\s]+?)\s+VOLVO', location)
        if match:
            city_candidate = match.group(1).strip()
            if is_valid_swedish_city(city_candidate):
                return city_candidate

    # Strategy 3: Extract known city from anywhere in text
    # Useful for complex dealer names like "Bilia Outlet Bilhall Hisingen Aröd"
    # Check multi-word cities first (e.g., "UPPLANDS VÄSBY")
    for city in SWEDISH_CITIES:
        if ' ' in city and city in location:
            return city

    # Check single-word cities
    words = location.split()
    for word in words:
        word_clean = word.strip(',-()').upper()
        if is_valid_swedish_city(word_clean):
            return word_clean

    # Strategy 4: Direct validation (location is just a city name)
    if is_valid_swedish_city(location):
        return location

    # Strategy 5: Remove common dealer prefixes and try again
    dealer_prefixes = [
        'BILBOLAGET PERSONBILAR', 'VOLVO CAR', 'BRANDT PERSONBILAR',
        'FINNVEDENS BIL', 'SKOBES BIL', 'HELMIA BIL', 'BILMÅNSSON I SKÅNE',
        'REJMES PERSONVAGNAR', 'BILKOMPANIET DALARNA', 'JOHAN AHLBERG BIL',
        'BILBOLAGET NORD', 'BILIA PERSONBILAR AB', 'BILIA'
    ]

    for prefix in dealer_prefixes:
        if location.startswith(prefix):
            remainder = location[len(prefix):].strip()
            # Remove leading separators
            remainder = remainder.lstrip('- ')
            if remainder and is_valid_swedish_city(remainder):
                return remainder

    # No match found - return as-is (may be new city not in list)
    # Better to have some location than none
    return location


def load_volvo_selekt():
    """Load and prepare Volvo Selekt data."""
    print(f"Reading Volvo Selekt: {VOLVO_SELEKT_FILE}")
    df = pd.read_csv(VOLVO_SELEKT_FILE, encoding='utf-8')
    print(f"  Loaded {len(df)} rows")

    # Standardize column names
    df = df.rename(columns={
        "model_variant": "model_variant",
        "driving_type": "driving_type",
    })

    # Add source
    df["source"] = "volvo_selekt"

    return df


def load_bilia():
    """Load and prepare Bilia data."""
    print(f"Reading Bilia: {BILIA_FILE}")
    df = pd.read_csv(BILIA_FILE, encoding='utf-8')
    print(f"  Loaded {len(df)} rows")

    # Standardize column names to match Volvo Selekt
    df = df.rename(columns={
        "version": "model_variant",
        "drive_wheels": "driving_type",
        "registration": "registration_number",
        "url": "detail_url",
    })

    # Add source
    df["source"] = "bilia"

    return df


def load_rejmes():
    """Load and prepare Rejmes data."""
    print(f"Reading Rejmes: {REJMES_FILE}")
    df = pd.read_csv(REJMES_FILE, encoding='utf-8')
    print(f"  Loaded {len(df)} rows")

    # Standardize column names to match Volvo Selekt
    df = df.rename(columns={
        "version": "model_variant",
        "drive_wheels": "driving_type",
        "registration": "registration_number",
        "url": "detail_url",
    })

    # Clean fuel type values to be consistent with other sources
    # Rejmes uses "Hybrid el/bensin" instead of "Laddhybrid"
    fuel_map = {
        "Hybrid el/bensin": "Laddhybrid",
    }
    df["fuel_type"] = df["fuel_type"].replace(fuel_map)

    # Add source
    df["source"] = "rejmes"

    return df


def combine_datasets(df_selekt, df_bilia, df_rejmes=None):
    """Combine datasets with consistent columns."""
    print("\nCombining datasets...")

    # Define common columns (order matters for final output)
    common_cols = [
        "registration_number",
        "price",
        "model_year",
        "mileage",
        "model_variant",
        "fuel_type",
        "electric_type",
        "engine_power",
        "transmission",
        "driving_type",
        "color",
        "location",
        "body_type",
        "franchise_approved",
        "standard_equipment",  # Equipment data (Volvo Selekt only)
        "extras",              # Equipment data (Volvo Selekt only)
        "detail_url",
        "source",
        "scrape_date",
    ]

    # List of dataframes to combine
    dfs = [df_selekt, df_bilia]
    if df_rejmes is not None:
        dfs.append(df_rejmes)

    # Ensure all dataframes have all columns
    for df in dfs:
        for col in common_cols:
            if col not in df.columns:
                df[col] = None

    # Select only common columns for each dataframe
    dfs_selected = [df[common_cols] for df in dfs]

    # Combine
    combined = pd.concat(dfs_selected, ignore_index=True)
    print(f"  Combined: {len(combined)} total rows")
    print(f"    - Volvo Selekt: {len(dfs_selected[0])} rows")
    print(f"    - Bilia: {len(dfs_selected[1])} rows")
    if df_rejmes is not None:
        print(f"    - Rejmes: {len(dfs_selected[2])} rows")

    return combined


def check_duplicates(df):
    """Check for duplicate registration numbers across sources."""
    print("\n" + "="*60)
    print("DUPLICATE ANALYSIS")
    print("="*60)

    # Normalize registration numbers for comparison
    df["reg_normalized"] = df["registration_number"].str.upper().str.strip()

    # Find duplicates
    dup_mask = df.duplicated(subset=["reg_normalized"], keep=False)
    duplicates = df[dup_mask].sort_values("reg_normalized")

    if len(duplicates) > 0:
        n_dup_records = len(duplicates)
        n_dup_regs = duplicates["reg_normalized"].nunique()
        print(f"Found {n_dup_records} records with {n_dup_regs} duplicate registration numbers")

        # Show cross-source duplicates
        cross_source = duplicates.groupby("reg_normalized")["source"].nunique()
        cross_source_regs = cross_source[cross_source > 1].index.tolist()

        if cross_source_regs:
            print(f"\n{len(cross_source_regs)} cars appear on MULTIPLE sites:")
            print("-" * 60)

            for reg in cross_source_regs[:10]:  # Show first 10
                car_data = df[df["reg_normalized"] == reg]
                sources_list = car_data["source"].tolist()
                print(f"\n  {reg} (on {', '.join(sources_list)}):")
                for _, row in car_data.iterrows():
                    price = f"{row['price']:,.0f}" if pd.notna(row['price']) else "N/A"
                    print(f"    [{row['source']:12}] Price: {price} SEK | Year: {row['model_year']}")

            if len(cross_source_regs) > 10:
                print(f"\n  ... and {len(cross_source_regs) - 10} more")
    else:
        print("No duplicate registration numbers found")

    # Clean up temp column
    df.drop("reg_normalized", axis=1, inplace=True)

    return duplicates


def remove_duplicates(df, keep="first"):
    """Remove duplicate registration numbers, keeping specified occurrence.

    keep: 'first' keeps first occurrence, 'volvo_selekt' prefers that source
    """
    print("\nRemoving duplicates...")

    initial_count = len(df)

    # Normalize for comparison
    df["reg_normalized"] = df["registration_number"].str.upper().str.strip()

    # Count duplicates before removal for detailed reporting
    dup_mask = df.duplicated(subset=["reg_normalized"], keep=False)
    n_dup_records = dup_mask.sum()
    n_unique_dups = df.loc[dup_mask, "reg_normalized"].nunique()

    if keep == "volvo_selekt":
        # Priority: volvo_selekt > bilia > rejmes
        df["source_priority"] = df["source"].map({
            "volvo_selekt": 0,
            "bilia": 1,
            "rejmes": 2
        })
        df = df.sort_values(["reg_normalized", "source_priority"])
        df = df.drop_duplicates(subset=["reg_normalized"], keep="first")
        df = df.drop("source_priority", axis=1)
    else:
        df = df.drop_duplicates(subset=["reg_normalized"], keep=keep)

    df = df.drop("reg_normalized", axis=1)

    final_count = len(df)
    removed = initial_count - final_count

    print(f"  Found {n_unique_dups} registration numbers appearing multiple times ({n_dup_records} total records)")
    print(f"  Removed {removed} duplicate records")
    print(f"  Final count: {final_count} unique cars")

    return df, removed


def clean_combined_data(df):
    """Apply cleaning transformations to combined dataset."""
    print("\nCleaning combined data...")

    cleaned = pd.DataFrame()

    # Keep identifiers
    cleaned["registration_number"] = df["registration_number"]

    # Target variable
    cleaned["price"] = df["price"]

    # Numeric features
    cleaned["model_year"] = df["model_year"]
    cleaned["mileage"] = df["mileage"]
    cleaned["horsepower"] = df["engine_power"].apply(extract_horsepower)

    # Calculate car age (years from current year)
    current_year = 2026
    cleaned["age"] = current_year - cleaned["model_year"]

    # Extract engine code from model variant
    cleaned["engine_code"] = df["model_variant"].apply(extract_engine_code)

    # Fill missing engine codes by inferring from horsepower
    missing_engine = cleaned["engine_code"].isna()
    if missing_engine.any():
        inferred = cleaned.loc[missing_engine, "horsepower"].apply(infer_engine_from_horsepower)
        cleaned.loc[missing_engine, "engine_code"] = inferred
        print(f"  Inferred {(~cleaned['engine_code'].isna() & missing_engine).sum()} engine codes from horsepower")

    # Clean fuel type (using electric_type from Bilia if available)
    cleaned["fuel_type"] = df.apply(
        lambda row: clean_fuel_type(row["fuel_type"], row.get("electric_type")),
        axis=1
    )

    cleaned["transmission"] = df["transmission"].apply(clean_transmission)
    cleaned["driving_type"] = df["driving_type"].apply(clean_driving_type)
    cleaned["color"] = df["color"]
    cleaned["location"] = df["location"].apply(normalize_location)

    # Keep source for analysis
    cleaned["source"] = df["source"]

    # Keep franchise approval status (Volvo Selekt only, others will be NaN)
    cleaned["franchise_approved"] = df["franchise_approved"]

    # Keep equipment data (Volvo Selekt only, others will be NaN)
    cleaned["standard_equipment"] = df.get("standard_equipment", pd.Series([""]*len(df)))
    cleaned["extras"] = df.get("extras", pd.Series([""]*len(df)))

    # Keep original model variant for reference
    cleaned["model_variant_original"] = df["model_variant"]

    # Keep URL for reference
    cleaned["url"] = df["detail_url"]

    return cleaned


def print_summary(df, title="Data Summary"):
    """Print summary statistics."""
    print(f"\n{'='*60}")
    print(title)
    print("="*60)
    print(f"Total rows: {len(df)}")

    if "price" in df.columns:
        print(f"Price range: {df['price'].min():,.0f} - {df['price'].max():,.0f} SEK")
        print(f"Average price: {df['price'].mean():,.0f} SEK")

    if "model_year" in df.columns:
        print(f"Model years: {df['model_year'].min()} - {df['model_year'].max()}")

    if "mileage" in df.columns and df["mileage"].notna().any():
        print(f"Mileage range: {df['mileage'].min():,.0f} - {df['mileage'].max():,.0f} km")

    if "source" in df.columns:
        print("\nBy source:")
        print(df["source"].value_counts().to_string())

    if "engine_code" in df.columns:
        print("\nEngine code distribution:")
        print(df["engine_code"].value_counts().to_string())

    if "fuel_type" in df.columns:
        print("\nFuel type distribution:")
        print(df["fuel_type"].value_counts().to_string())

    if "driving_type" in df.columns:
        print("\nDriving type distribution:")
        print(df["driving_type"].value_counts().to_string())

    # Missing values
    print("\nMissing values:")
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    if len(missing) > 0:
        print(missing.to_string())
    else:
        print("  None")


def main():
    # Load all datasets
    df_selekt = load_volvo_selekt()
    df_bilia = load_bilia()
    df_rejmes = load_rejmes()

    # Combine datasets
    combined = combine_datasets(df_selekt, df_bilia, df_rejmes)

    # Check for duplicates
    duplicates = check_duplicates(combined)

    # Remove duplicates (prefer Volvo Selekt data, then Bilia, then Rejmes)
    deduped, n_removed = remove_duplicates(combined.copy(), keep="volvo_selekt")

    # Clean the data
    cleaned = clean_combined_data(deduped)

    # Print summary
    print_summary(cleaned, "CLEANED DATA SUMMARY")

    # Save cleaned data
    cleaned.to_csv(OUTPUT_FILE, index=False, encoding='utf-8')
    print(f"\nSaved cleaned data to: {OUTPUT_FILE}")

    # Final duplicate summary
    print(f"\n{'='*60}")
    print("DUPLICATE REMOVAL SUMMARY")
    print("="*60)
    print(f"  Total duplicates removed: {n_removed}")

    return cleaned


if __name__ == "__main__":
    main()

"""Analyze location data quality after fixes."""
import pandas as pd

# Load cleaned data with UTF-8 encoding
df = pd.read_csv('data/volvo_xc60_cleaned.csv', encoding='utf-8')

print('Location Analysis:')
print('=' * 60)
print(f'Total cars: {len(df)}')
print(f'Cars with location: {df["location"].notna().sum()}')
print(f'Missing locations: {df["location"].isna().sum()}')
print()

print('Checking for dealer names in locations:')
print('-' * 60)
dealer_names = [
    'BILBOLAGET PERSONBILAR',
    'VOLVO CAR',
    'BRANDT',
    'BILIA PERSONBILAR AB',
    'BILIA OUTLET',
    'BILIA PERSONBILAR'
]

for dealer in dealer_names:
    count = df[df['location'].str.contains(dealer, na=False, case=False)].shape[0]
    if count > 0:
        print(f'  FAIL - {dealer}: {count} instances')
        # Show examples
        examples = df[df['location'].str.contains(dealer, na=False, case=False)]['location'].head(3).tolist()
        for ex in examples:
            print(f'      Example: {ex}')
    else:
        print(f'  PASS - {dealer}: 0 (CLEAN)')

print()
print('Most common locations (top 20):')
print('-' * 60)
print(df['location'].value_counts().head(20))

print()
print('Sample of missing locations:')
print('-' * 60)
missing = df[df['location'].isna()][['registration_number', 'url']].head(10)
if not missing.empty:
    for idx, row in missing.iterrows():
        print(f'  {row["registration_number"]}: {row["url"]}')
else:
    print('  No missing locations!')

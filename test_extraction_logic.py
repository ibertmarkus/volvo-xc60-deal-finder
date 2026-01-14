"""Test the extraction logic directly"""
import sys
sys.path.insert(0, '.')
from scraper import parse_city_from_volvo_text, is_valid_swedish_city

# Test data from actual page
test_strings = [
    "Volvo Car - Upplands Väsby",
    "Volvo Car - Upplands V�sby",  # With encoding issue
    "UPPLANDS VÄSBY",
    "UPPLANDS V�SBY",  # With encoding issue
]

print("Testing parse_city_from_volvo_text:")
print("="*60)
for test in test_strings:
    result = parse_city_from_volvo_text(test)
    print(f"Input:  '{test}'")
    print(f"Result: '{result}'")
    print()

print("\nTesting is_valid_swedish_city:")
print("="*60)
test_cities = [
    "UPPLANDS VÄSBY",
    "UPPLANDS V�SBY",
    "UPPLANDS VASBY",  # Without special char
]
for test in test_cities:
    result = is_valid_swedish_city(test)
    print(f"Input:  '{test}' → {result}")

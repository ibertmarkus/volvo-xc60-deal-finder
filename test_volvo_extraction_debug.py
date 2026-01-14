"""Debug Volvo Selekt extraction step by step"""
import sys
sys.path.insert(0, '.')
from scraper import parse_city_from_volvo_text, is_valid_swedish_city, normalize_swedish_text
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time

# Setup driver
options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# Test URL
url = "https://selekt.volvocars.se/sv-se/store/all/vehicles/1MjEyYmZmZTctNGM3OS00OWJkLWE1YjMtMTA5MjRkZDlhNWE1fENvZGV3ZWF2ZXJzU3RvY2tJZHxDYXI1?pageNumber=11&models=XC60"

print(f"Loading: {url}")
driver.get(url)
time.sleep(5)

print("\n" + "="*80)
print("STEP 1: Extract headings with JavaScript")
print("="*80)

headings_text = driver.execute_script("""
    var headings = document.querySelectorAll('h2, h3, h4');
    for (var h of headings) {
        var text = h.textContent;
        if (text.toLowerCase().includes('volvo') && text.includes(' - ')) {
            return text.trim();
        }
    }
    return null;
""")

print(f"JavaScript returned: '{headings_text}'")
print(f"Type: {type(headings_text)}")

if headings_text:
    print("\n" + "="*80)
    print("STEP 2: Normalize text")
    print("="*80)
    normalized = normalize_swedish_text(headings_text)
    print(f"After normalize: '{normalized}'")

    print("\n" + "="*80)
    print("STEP 3: Parse city")
    print("="*80)
    city = parse_city_from_volvo_text(headings_text)
    print(f"parse_city_from_volvo_text result: '{city}'")

    if city:
        print("\n" + "="*80)
        print("STEP 4: Validate city")
        print("="*80)
        is_valid = is_valid_swedish_city(city)
        print(f"is_valid_swedish_city result: {is_valid}")
    else:
        print("\n[X] parse_city_from_volvo_text returned None")

        # Debug why parsing failed
        print("\nDEBUG: Checking parsing logic manually")
        print(f"  Contains 'volvo car -': {'volvo car -' in headings_text.lower()}")
        print(f"  Contains 'volvo - ': {'volvo - ' in headings_text.lower()}")

        if 'volvo car -' in headings_text.lower():
            parts = headings_text.split(' - ', 1)
            print(f"  Split parts: {parts}")
            if len(parts) == 2:
                city_part = parts[1].strip().upper()
                print(f"  City part: '{city_part}'")
                print(f"  Is valid: {is_valid_swedish_city(city_part)}")
else:
    print("[X] JavaScript returned None - no heading found")

driver.quit()

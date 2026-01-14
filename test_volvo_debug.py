"""Debug Volvo Selekt location extraction"""
import sys
sys.path.insert(0, '.')
import scraper
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

# Test URL from earlier test
url = "https://selekt.volvocars.se/sv-se/store/all/vehicles/1MjEyYmZmZTctNGM3OS00OWJkLWE1YjMtMTA5MjRkZDlhNWE1fENvZGV3ZWF2ZXJzU3RvY2tJZHxDYXI1?pageNumber=11&models=XC60"

print(f"Loading: {url}")
driver.get(url)
time.sleep(5)

# Get page text
page_text = driver.find_element(By.TAG_NAME, "body").text
lines = [l.strip() for l in page_text.split("\n") if l.strip()]

print("\n" + "="*80)
print("SEARCHING FOR LOCATION PATTERNS")
print("="*80)

# Search for patterns
found_any = False
for i, line in enumerate(lines):
    line_lower = line.lower()
    # Look for "Volvo Car" or "Volvo -"
    if 'volvo' in line_lower and (' - ' in line or 'car' in line_lower):
        print(f"\nLine {i}: {line}")
        found_any = True
        # Print context
        for j in range(max(0, i-2), min(len(lines), i+3)):
            print(f"  {j}: {lines[j]}")

if not found_any:
    print("\nNO 'Volvo Car -' OR 'Volvo -' patterns found!")
    print("\nShowing all lines with 'volvo':")
    for i, line in enumerate(lines):
        if 'volvo' in line.lower():
            print(f"  {i}: {line}")

print("\n" + "="*80)
print("Testing JavaScript heading extraction...")
print("="*80)

headings = driver.execute_script("""
    var headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
    var result = [];
    for (var h of headings) {
        result.push(h.textContent.trim());
    }
    return result;
""")

print(f"\nFound {len(headings)} headings:")
for i, h in enumerate(headings[:20]):  # Show first 20
    print(f"  {i}: {h}")
    if 'volvo' in h.lower():
        print(f"    ^^^ CONTAINS 'VOLVO'")

driver.quit()

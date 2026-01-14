"""Quick test to inspect Volvo Selekt page for location data."""
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# Setup visible browser
options = Options()
options.add_argument("--window-size=1920,1080")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# Test URL from CSV
url = "https://selekt.volvocars.se/sv-se/store/all/vehicles/1MjEyYmZmZTctNGM3OS00OWJkLWE1YjMtMTA5MjRkZDlhNWE1fENvZGV3ZWF2ZXJzU3RvY2tJZHxDYXI1?pageNumber=11&models=XC60&quoteReference=ea5acae1-31d2-4e64-83a8-fdd4d9bc9c46&vehicleReference=95ea6e0f-4777-42b0-96bf-955fe1037bf4"

print(f"Loading: {url}")
driver.get(url)
time.sleep(5)  # Wait for page to fully load

# Get all text
page_text = driver.find_element(By.TAG_NAME, "body").text
lines = [l.strip() for l in page_text.split("\n") if l.strip()]

print("\n" + "="*80)
print("SEARCHING FOR LOCATION-RELATED TEXT")
print("="*80)

# Search for Swedish location/dealer keywords
keywords = ["återförsäljare", "butik", "säljare", "anläggning", "dealer", "store", "retailer",
            "kontakta", "besök", "adress", "address", "lokation", "plats"]

for i, line in enumerate(lines):
    line_lower = line.lower()
    for keyword in keywords:
        if keyword in line_lower:
            # Print context: 2 lines before, the line, and 3 lines after
            start = max(0, i-2)
            end = min(len(lines), i+4)
            print(f"\nFound '{keyword}' at line {i}:")
            print("-" * 80)
            for j in range(start, end):
                prefix = ">>> " if j == i else "    "
                print(f"{prefix}{lines[j]}")
            print("-" * 80)
            break

# Also try JavaScript selectors
print("\n" + "="*80)
print("TESTING JAVASCRIPT SELECTORS")
print("="*80)

selectors_to_try = [
    ('document.querySelector(".seller")', 'Seller class'),
    ('document.querySelector("[data-dealer]")', 'Data-dealer attribute'),
    ('document.querySelector(".retailer-info")', 'Retailer info class'),
    ('document.querySelector(".store-location")', 'Store location class'),
    ('document.querySelector(".dealer-name")', 'Dealer name class'),
    ('document.querySelectorAll("h2, h3")', 'All headings (check for dealer name)'),
]

for selector, description in selectors_to_try:
    try:
        result = driver.execute_script(f"""
            var el = {selector};
            if (el) {{
                if (el.length !== undefined) {{  // NodeList
                    var texts = [];
                    for (var i = 0; i < Math.min(el.length, 5); i++) {{
                        texts.push(el[i].textContent.trim().substring(0, 100));
                    }}
                    return texts.join(' | ');
                }} else {{
                    return el.textContent.trim().substring(0, 200);
                }}
            }}
            return null;
        """)
        print(f"\n{description}: {selector}")
        if result:
            print(f"  FOUND: {result}")
        else:
            print(f"  NOT FOUND")
    except Exception as e:
        print(f"\n{description}: ERROR - {e}")

print("\n" + "="*80)
print("SEARCH COMPLETE - Check output above for location data")
print("="*80)

input("\nPress Enter to close browser...")
driver.quit()

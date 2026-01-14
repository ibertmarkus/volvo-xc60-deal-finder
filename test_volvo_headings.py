"""Check what headings exist on Volvo pages without location"""
import sys
sys.path.insert(0, '.')
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

# Test URL that returned None
url = "https://selekt.volvocars.se/sv-se/store/all/vehicles/1ZGU5NzIzMjQtODVjNi00ZjdlLWI5Y2UtMGU2MGZmZDRjNWIzfENvZGV3ZWF2ZXJzU3RvY2tJZHxDYXI1?models=XC60"

print(f"Loading: {url}")
driver.get(url)
time.sleep(5)

print("\n" + "="*80)
print("ALL HEADINGS ON PAGE")
print("="*80)

headings = driver.execute_script("""
    var headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
    var result = [];
    for (var h of headings) {
        result.push(h.textContent.trim());
    }
    return result;
""")

for i, h in enumerate(headings):
    print(f"{i}: {h}")

print("\n" + "="*80)
print("SEARCH FOR 'VOLVO' OR 'DEALER' OR LOCATION KEYWORDS")
print("="*80)

page_text = driver.find_element(By.TAG_NAME, "body").text
lines = [l.strip() for l in page_text.split("\n") if l.strip()]

found = []
for i, line in enumerate(lines):
    line_lower = line.lower()
    if any(keyword in line_lower for keyword in ['volvo', 'dealer', 'återförsäljare', 'butik', 'anläggning']):
        found.append((i, line))

print(f"Found {len(found)} lines with keywords:")
for i, line in found[:20]:  # First 20
    print(f"  {i}: {line}")

driver.quit()

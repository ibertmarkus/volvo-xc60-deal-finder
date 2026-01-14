"""Check what's on pages missing location"""
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

# Test failing URL
url = "https://selekt.volvocars.se/sv-se/store/all/vehicles/1ODM3ZjYwZmYtNzU0Zi00MTRhLWE4OWYtZTczNmIxZjAyZTM1fENvZGV3ZWF2ZXJzU3RvY2tJZHxDYXI1?models=XC60"

print(f"Loading: {url}")
driver.get(url)
time.sleep(5)

print("\n" + "="*80)
print("ALL HEADINGS")
print("="*80)

headings = driver.execute_script("""
    var headings = document.querySelectorAll('h1, h2, h3, h4');
    var result = [];
    for (var h of headings) {
        var text = h.textContent.trim();
        if (text) result.push(text);
    }
    return result;
""")

for i, h in enumerate(headings[:20]):
    dash_marker = " <- HAS DASH" if " - " in h else ""
    print(f"{i}: {h}{dash_marker}")

print("\n" + "="*80)
print("PAGE TEXT (first 100 lines)")
print("="*80)

page_text = driver.find_element(By.TAG_NAME, "body").text
lines = [l.strip() for l in page_text.split("\n") if l.strip()]

for i, line in enumerate(lines[:100]):
    if 'volvo' in line.lower() or 'dealer' in line.lower() or ' - ' in line:
        print(f"{i}: {line}")

driver.quit()

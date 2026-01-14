"""Test single Volvo Selekt URL with debug output"""
import sys
sys.path.insert(0, '.')
import scraper
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Setup driver
options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

# Test single URL
url = "https://selekt.volvocars.se/sv-se/store/all/vehicles/1MjEyYmZmZTctNGM3OS00OWJkLWE1YjMtMTA5MjRkZDlhNWE1fENvZGV3ZWF2ZXJzU3RvY2tJZHxDYXI1?pageNumber=11&models=XC60"

print(f"Testing: {url}")
car_data = scraper.scrape_detail_page_full(driver, url)

print(f"\nResult:")
print(f"  Registration: {car_data.get('registration_number', '')}")
print(f"  Location: {car_data.get('location', '[NONE]')}")

driver.quit()

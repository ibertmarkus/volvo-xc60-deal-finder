"""Quick test to check what's on a car detail page"""
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# Setup headless browser
options = Options()
options.add_argument("--headless=new")
options.add_argument("--window-size=1920,1080")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

try:
    # Test URL - we'll need to find one from the scraper
    # For now, let's just get the first car from the listing page
    driver.get("https://selekt.volvocars.se/sv-se/store/all/vehicles?models=XC60")
    time.sleep(3)
    
    # Get all car links
    links = driver.find_elements(By.TAG_NAME, "a")
    car_urls = []
    for link in links:
        url = link.get_attribute("href")
        if url and "/vehicles/" in url and "vehicleReference=" in url:
            car_urls.append(url)
    
    # Visit the 25th car (where it crashed)
    if len(car_urls) >= 25:
        test_url = car_urls[24]  # 0-indexed
        print(f"Testing car #25: {test_url}\n")
        
        driver.get(test_url)
        time.sleep(2)
        
        page_text = driver.find_element(By.TAG_NAME, "body").text
        lines = [l.strip() for l in page_text.split("\n") if l.strip()]
        
        # Look for price-related lines
        print("Lines containing 'pris' (case insensitive):")
        for i, line in enumerate(lines):
            if "pris" in line.lower():
                print(f"  Line {i}: '{line}'")
                if i + 1 < len(lines):
                    print(f"  Line {i+1}: '{lines[i+1]}'")
                print()
        
        # Show first 50 lines
        print("\n" + "="*60)
        print("First 50 lines of page text:")
        print("="*60)
        for i, line in enumerate(lines[:50]):
            print(f"{i:3d}: {line}")
            
finally:
    driver.quit()

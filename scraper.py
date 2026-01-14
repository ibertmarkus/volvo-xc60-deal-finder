"""
Volvo XC60 Scraper - Scrapes used Volvo XC60 listings from Volvo Selekt Sweden.

Usage:
    python scraper.py           # Run in headless mode (default)
    python scraper.py --visible # Run with visible browser
"""

import sys
# Force unbuffered output so we can see progress
sys.stdout.reconfigure(line_buffering=True)

import argparse
import csv
import os
import re
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

# Configuration
BASE_URL = "https://selekt.volvocars.se/sv-se/store/all/vehicles?models=XC60"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "volvo_xc60_listings.csv")
WAIT_TIMEOUT = 15


def setup_driver(headless=False):
    """Initialize Chrome WebDriver with appropriate options."""
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # Avoid detection
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    # Disable images to speed up scraping
    prefs = {
        'profile.managed_default_content_settings.images': 2,
        'profile.default_content_setting_values': {'images': 2}
    }
    options.add_experimental_option('prefs', prefs)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(3)
    return driver


def accept_cookies(driver):
    """Accept cookie consent if present."""
    try:
        wait = WebDriverWait(driver, 5)
        # Common cookie button patterns
        cookie_selectors = [
            "//button[contains(text(), 'Acceptera')]",
            "//button[contains(text(), 'Godkänn')]",
            "//button[contains(@id, 'accept')]",
            "//button[contains(@class, 'accept')]",
        ]
        for selector in cookie_selectors:
            try:
                btn = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                btn.click()
                print("Accepted cookies")
                time.sleep(1)
                return
            except:
                continue
    except:
        pass


def wait_for_listings(driver):
    """Wait for car listings to load."""
    wait = WebDriverWait(driver, WAIT_TIMEOUT)
    # Try various selectors that might contain car cards
    selectors = [
        (By.CSS_SELECTOR, "[data-testid='vehicle-card']"),
        (By.CSS_SELECTOR, ".vehicle-card"),
        (By.CSS_SELECTOR, "[class*='card-container']"),
        (By.CSS_SELECTOR, "article"),
        (By.XPATH, "//a[contains(@href, '/vehicle/')]"),
    ]
    for by, selector in selectors:
        try:
            wait.until(EC.presence_of_all_elements_located((by, selector)))
            print(f"Found listings using selector: {selector}")
            return True
        except:
            continue
    return False


def get_car_cards(driver):
    """Find all car card elements on the current page."""
    selectors = [
        (By.CSS_SELECTOR, "[data-testid='vehicle-card']"),
        (By.CSS_SELECTOR, ".vehicle-card"),
        (By.CSS_SELECTOR, "[class*='card-container']"),
        (By.XPATH, "//a[contains(@href, '/vehicle/')]//ancestor::div[contains(@class, 'card')]"),
    ]
    for by, selector in selectors:
        cards = driver.find_elements(by, selector)
        if cards:
            print(f"Found {len(cards)} car cards using: {selector}")
            return cards
    return []


def extract_text_safe(element, selector, by=By.CSS_SELECTOR):
    """Safely extract text from a child element."""
    try:
        el = element.find_element(by, selector)
        return el.text.strip()
    except:
        return ""


def parse_price(text):
    """Extract numeric price from Swedish format like '614 900,00 kr' or '614 900 kr'."""
    if not text:
        return None
    # Swedish format: space as thousands separator, comma as decimal
    # Remove "kr", spaces, and everything after comma (öre/cents)
    cleaned = text.lower().replace("kr", "").replace(" ", "")
    # Remove decimal part (after comma)
    if "," in cleaned:
        cleaned = cleaned.split(",")[0]
    # Extract just digits
    numbers = re.findall(r'\d+', cleaned)
    if numbers:
        return int("".join(numbers))
    return None


def parse_mileage(text):
    """Extract mileage from text like '5 230 mil' or '52 300 km'."""
    if not text:
        return None
    text_lower = text.lower()
    numbers = re.findall(r'\d+', text.replace(" ", ""))
    if numbers:
        value = int("".join(numbers))
        # Convert mil to km if needed (1 mil = 10 km in Swedish)
        if "mil" in text_lower and "km" not in text_lower:
            value = value * 10
        return value
    return None


def scrape_listing_page(driver):
    """Extract basic data from all cars on the current listing page."""
    cars = []
    cards = get_car_cards(driver)

    for i, card in enumerate(cards):
        try:
            car_data = {
                "registration_number": "",
                "price": None,
                "model_year": None,
                "fuel_type": "",
                "engine_power": "",
                "transmission": "",
                "color": "",
                "mileage": None,
                "detail_url": "",
            }

            # Try to get the detail link
            try:
                link = card.find_element(By.XPATH, ".//a[contains(@href, '/vehicle/')]")
                car_data["detail_url"] = link.get_attribute("href")
            except:
                pass

            # Extract visible text - the structure varies, so we parse all text
            card_text = card.text
            lines = [l.strip() for l in card_text.split("\n") if l.strip()]

            for line in lines:
                line_lower = line.lower()
                # Price detection
                if "kr" in line_lower or re.search(r'\d{3}\s*\d{3}', line):
                    if not car_data["price"]:
                        car_data["price"] = parse_price(line)
                # Mileage detection
                elif "mil" in line_lower or "km" in line_lower:
                    if not car_data["mileage"]:
                        car_data["mileage"] = parse_mileage(line)
                # Fuel type
                elif any(f in line_lower for f in ["bensin", "diesel", "el", "hybrid", "laddhybrid"]):
                    if not car_data["fuel_type"]:
                        car_data["fuel_type"] = line
                # Transmission
                elif any(t in line_lower for t in ["automat", "manuell", "aut.", "man."]):
                    if not car_data["transmission"]:
                        car_data["transmission"] = line
                # Registration number pattern (ABC123 or ABC12A)
                elif re.match(r'^[A-Z]{3}\s*\d{2,3}\s*[A-Z0-9]?$', line.upper()):
                    car_data["registration_number"] = line.upper().replace(" ", "")
                # Model year (4 digits that look like a year)
                elif re.match(r'^20[0-2]\d$', line):
                    car_data["model_year"] = int(line)
                # Engine power (hk or kW)
                elif "hk" in line_lower or "kw" in line_lower:
                    if not car_data["engine_power"]:
                        car_data["engine_power"] = line

            cars.append(car_data)
            print(f"  Card {i+1}: Price={car_data['price']}, Mileage={car_data['mileage']}")

        except Exception as e:
            print(f"  Error parsing card {i+1}: {e}")
            continue

    return cars


def scrape_detail_page(driver, url):
    """Scrape additional details from a car's detail page."""
    details = {
        "model_year": None,
        "color": "",
        "registration_number": "",
        "engine_power": "",
    }

    try:
        driver.get(url)
        time.sleep(2)  # Wait for page to load

        page_text = driver.find_element(By.TAG_NAME, "body").text
        lines = [l.strip() for l in page_text.split("\n") if l.strip()]

        for i, line in enumerate(lines):
            line_lower = line.lower()
            # Model year
            if "årsmodell" in line_lower or "modellår" in line_lower:
                # Next line might have the value
                if i + 1 < len(lines):
                    year_match = re.search(r'20[0-2]\d', lines[i+1])
                    if year_match:
                        details["model_year"] = int(year_match.group())
            elif re.match(r'^20[0-2]\d$', line) and not details["model_year"]:
                details["model_year"] = int(line)
            # Color
            if "färg" in line_lower:
                if i + 1 < len(lines):
                    details["color"] = lines[i+1]
            # Registration
            if "reg" in line_lower and "nummer" in line_lower:
                if i + 1 < len(lines):
                    reg_match = re.match(r'^[A-Z]{3}\s*\d{2,3}\s*[A-Z0-9]?$', lines[i+1].upper())
                    if reg_match:
                        details["registration_number"] = lines[i+1].upper().replace(" ", "")

    except Exception as e:
        print(f"  Error scraping detail page: {e}")

    return details


def scroll_to_load_all(driver, max_scrolls=30):
    """Scroll down to load all cars (handles infinite scroll or lazy loading)."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_count = 0

    while scroll_count < max_scrolls:
        # Scroll to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)

        # Check for "Load more" button
        try:
            load_more_selectors = [
                "//button[contains(text(), 'Visa fler')]",
                "//button[contains(text(), 'Ladda fler')]",
                "//button[contains(text(), 'Load more')]",
                "//a[contains(text(), 'Visa fler')]",
            ]
            for selector in load_more_selectors:
                try:
                    btn = driver.find_element(By.XPATH, selector)
                    if btn.is_displayed():
                        btn.click()
                        print(f"  Clicked 'Load more' button")
                        time.sleep(2)
                        break
                except:
                    continue
        except:
            pass

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            # No more content loaded
            break
        last_height = new_height
        scroll_count += 1
        print(f"  Scrolled {scroll_count} times, page height: {new_height}")

    # Scroll back to top
    driver.execute_script("window.scrollTo(0, 0);")
    time.sleep(1)


def click_pagination(driver, page_num):
    """Click pagination button to go to specific page."""
    try:
        # Look for pagination buttons with the page number
        selectors = [
            f"//button[normalize-space()='{page_num}']",
            f"//a[normalize-space()='{page_num}']",
            f"//*[contains(@class, 'pagination')]//button[normalize-space()='{page_num}']",
            f"//*[contains(@class, 'pagination')]//a[normalize-space()='{page_num}']",
        ]
        for selector in selectors:
            try:
                btn = driver.find_element(By.XPATH, selector)
                if btn.is_displayed() and btn.is_enabled():
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(0.5)
                    btn.click()
                    print(f"  Clicked page {page_num}")
                    time.sleep(2)
                    return True
            except:
                continue
    except Exception as e:
        print(f"  Could not click page {page_num}: {e}")
    return False


def get_total_cars_count(driver):
    """Get total number of cars from page text."""
    try:
        body_text = driver.find_element(By.TAG_NAME, "body").text
        # Look for patterns like "113 bilar" or "Visar 23 av 113"
        match = re.search(r'(\d+)\s*(?:bilar|fordon|resultat)', body_text.lower())
        if match:
            return int(match.group(1))
        match = re.search(r'av\s*(\d+)', body_text)
        if match:
            return int(match.group(1))
    except:
        pass
    return None


def get_urls_from_page(driver):
    """Extract unique vehicle URLs from current page."""
    urls = set()
    links = driver.find_elements(By.TAG_NAME, "a")
    for link in links:
        url = link.get_attribute("href")
        if url and "/vehicles/" in url and "vehicleReference=" in url:
            base_url = url.split("?")[0]
            if base_url and len(base_url) > 60:
                urls.add(url)
    return urls


def collect_all_detail_urls(driver):
    """Collect all unique detail page URLs by paginating through all pages."""
    detail_urls = set()

    print(f"Loading: {BASE_URL}")
    driver.get(BASE_URL)
    time.sleep(3)

    accept_cookies(driver)

    if not wait_for_listings(driver):
        print("ERROR: Could not find any car listings.")
        with open(os.path.join(OUTPUT_DIR, "debug_page.html"), "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        return []

    total_count = get_total_cars_count(driver)
    print(f"Total cars available: {total_count or 'unknown'}")

    # Get URLs from page 1
    page1_urls = get_urls_from_page(driver)
    detail_urls.update(page1_urls)
    print(f"Page 1: Found {len(page1_urls)} URLs (Total: {len(detail_urls)})")

    # Navigate through all pages by clicking numbered buttons
    max_pages = 30
    for page in range(2, max_pages + 1):
        try:
            # Scroll to bottom to make pagination visible
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.5)

            # Find and click the button with the page number
            # Use JavaScript for reliable clicking
            click_script = f"""
            var buttons = document.querySelectorAll('button');
            for (var btn of buttons) {{
                if (btn.textContent.trim() === '{page}') {{
                    btn.scrollIntoView({{block: 'center'}});
                    btn.click();
                    return true;
                }}
            }}
            return false;
            """

            clicked = driver.execute_script(click_script)

            if not clicked:
                # Page button not found - we've reached the end or need to click "next"
                # Try clicking the last arrow button (next page)
                next_script = """
                var arrows = document.querySelectorAll('button');
                var lastArrow = null;
                for (var btn of arrows) {
                    if (btn.className && btn.className.includes('arrow')) {
                        lastArrow = btn;
                    }
                }
                if (lastArrow) {
                    lastArrow.scrollIntoView({block: 'center'});
                    lastArrow.click();
                    return true;
                }
                return false;
                """
                clicked = driver.execute_script(next_script)

            if not clicked:
                print(f"  Could not find page {page} button, stopping pagination")
                break

            # Wait for new content to load
            time.sleep(2)

            # Collect URLs from this page
            page_urls = get_urls_from_page(driver)
            new_urls = page_urls - detail_urls
            detail_urls.update(page_urls)

            print(f"Page {page}: Found {len(new_urls)} new URLs (Total: {len(detail_urls)})")

            if len(new_urls) == 0:
                print("  No new URLs found, reached last page")
                break

            # Stop if we have all cars
            if total_count and len(detail_urls) >= total_count:
                print(f"  Collected all {total_count} cars!")
                break

        except Exception as e:
            print(f"  Error on page {page}: {e}")
            break

    return list(detail_urls)


def normalize_swedish_text(text):
    """Normalize text to handle encoding issues with Swedish characters."""
    if not text:
        return text
    # Handle common encoding issues where Swedish chars become �
    # This is a heuristic approach - try to fix common patterns
    import re
    text = text.replace('\ufffd', 'Ä')  # Unicode replacement char
    text = text.replace('�', 'Ä')  # Common encoding issue
    return text


def is_valid_swedish_city(text):
    """Validate if text is a known Swedish city."""
    SWEDISH_CITIES = {
        # Major cities
        'STOCKHOLM', 'GÖTEBORG', 'MALMÖ', 'UPPSALA', 'VÄSTERÅS', 'ÖREBRO',
        'LINKÖPING', 'HELSINGBORG', 'NORRKÖPING', 'JÖNKÖPING', 'UMEÅ',
        'LUND', 'BORÅS', 'ESKILSTUNA', 'GÄVLE', 'SÖDERTÄLJE', 'KARLSTAD',
        'HALMSTAD', 'VÄXJÖ', 'SUNDSVALL', 'TROLLHÄTTAN', 'ÖSTERSUND',
        'FALUN', 'SKELLEFTEÅ', 'KRISTIANSTAD', 'KALMAR', 'KUNGÄLV',
        'TIMRÅ', 'ARÖD', 'LIDKÖPING', 'SKÖVDE', 'UDDEVALLA',
        # Medium cities
        'MOTALA', 'TRELLEBORG', 'KARLSKRONA', 'VARBERG', 'ÄNGELHOLM',
        'NYKÖPING', 'SANDVIKEN', 'LIDINGÖ', 'BOLLNÄS', 'ÖRNSKÖLDSVIK',
        'LANDSKRONA', 'YSTAD', 'ÖSTHAMMAR', 'ARVIKA', 'SALA',
        'VARA', 'LAHOLM', 'ENKÖPING', 'VIMMERBY', 'LJUSDAL',
        'HUDIKSVALL', 'VALLENTUNA', 'ESLÖV', 'KRISTINEHAMN',
        # Stockholm area
        'UPPLANDS VÄSBY', 'TÄBY', 'SOLLENTUNA', 'SOLNA', 'NACKA',
        'HANINGE', 'HUDDINGE', 'MÄRSTA', 'UPPLANDS BRO', 'KISTA',
        'SEGELTORP', 'KUNGSÄNGEN', 'HAMMARBY SJÖSTAD',
        # Other dealer locations
        'LINDESBERG', 'FINSPÅNG', 'MJÖLBY', 'HALLSBERG', 'ÅTVIDABERG',
        'JÄGERSRO', 'SISJÖN'
    }
    if not text:
        return False
    # Normalize encoding issues before checking
    text_normalized = normalize_swedish_text(text)
    text_upper = text_normalized.upper().strip()
    return text_upper in SWEDISH_CITIES


def parse_city_from_volvo_text(text):
    """Extract city from Volvo Selekt text with comprehensive strategies.

    Handles patterns like:
    - 'Volvo Car - Upplands Väsby'
    - 'BILBOLAGET PERSONBILAR - TIMRÅ'
    - 'Dealer - City'
    """
    if not text:
        return None

    # Normalize encoding issues first
    text = normalize_swedish_text(text)
    text_upper = text.upper()

    # Get multi-word cities dynamically from is_valid_swedish_city
    MULTI_WORD_CITIES = ['UPPLANDS VÄSBY', 'UPPLANDS BRO', 'HAMMARBY SJÖSTAD']

    # Strategy 1: Check multi-word cities first (sorted by length, longest first)
    for city in sorted(MULTI_WORD_CITIES, key=lambda x: -len(x)):
        if city in text_upper:
            return city

    # Strategy 2: Handle " - " separator - try SECOND part first (the city)
    if ' - ' in text:
        parts = [p.strip() for p in text.split(' - ')]
        if len(parts) >= 2:
            # Try second part first (usually the city)
            second_part = parts[1].upper()
            if is_valid_swedish_city(second_part):
                return second_part
            # Fallback to first part only if it's a valid city
            first_part = parts[0].upper()
            if is_valid_swedish_city(first_part):
                return first_part
            # If second part is not validated but exists, return it anyway
            # (handles new cities not yet in list)
            if second_part:
                return second_part

    # Strategy 3: Word-by-word search for any known city
    for word in text.split():
        word_clean = word.strip(',-()').upper()
        if is_valid_swedish_city(word_clean):
            return word_clean

    return None


def scrape_detail_page_full(driver, url):
    """Scrape all details from a car's detail page."""
    car_data = {
        "registration_number": "",
        "price": None,
        "model_year": None,
        "model_variant": "",  # e.g., "T8 Plus Dark Nordic Edition"
        "fuel_type": "",
        "engine_power": "",
        "transmission": "",
        "driving_type": "",  # Körning (e.g., Fyrhjulsdrift)
        "color": "",
        "mileage": None,
        "location": "",  # Dealer location city
        "standard_equipment": "",  # Standardutrustning
        "extras": "",  # Extrautrustning
        "franchise_approved": False,  # Franchise-godkänd
        "detail_url": url,
    }

    try:
        driver.get(url)
        time.sleep(2)

        page_text = driver.find_element(By.TAG_NAME, "body").text
        lines = [l.strip() for l in page_text.split("\n") if l.strip()]

        for i, line in enumerate(lines):
            line_lower = line.lower()

            # Model variant - appears after "Volvo XC60" or "XC60"
            if line.strip() in ["Volvo XC60", "XC60"] and not car_data["model_variant"]:
                if i + 1 < len(lines):
                    variant = lines[i + 1].strip()
                    # Make sure it's not a navigation element
                    if variant and not any(x in variant.lower() for x in ["föregående", "nästa", "meny", "tillbaka"]):
                        car_data["model_variant"] = variant

            # Model year - look for "Årsmodell" label, next line has the year
            if "årsmodell" in line_lower:
                if i + 1 < len(lines):
                    year_match = re.search(r'20[0-2]\d', lines[i+1])
                    if year_match:
                        car_data["model_year"] = int(year_match.group())

            # Registration number - look for "Registreringsnummer" label
            if "registreringsnummer" in line_lower:
                if i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    reg_match = re.match(r'^[A-Z]{3}\d{2,3}[A-Z0-9]?$', next_line.upper())
                    if reg_match:
                        car_data["registration_number"] = next_line.upper()

            # Price - look for "Pris:" label (not just "Pris" to avoid other uses)
            if line_lower == "pris:" and not car_data["price"]:
                if i + 1 < len(lines):
                    price = parse_price(lines[i+1])
                    if price:  # Removed minimum price check - all prices are valid
                        car_data["price"] = price

            # Mileage - look for "Miltal" label
            if line_lower == "miltal" and not car_data["mileage"]:
                if i + 1 < len(lines):
                    car_data["mileage"] = parse_mileage(lines[i+1])

            # Fuel type - look for "Bränsle" label
            if line_lower == "bränsle" and not car_data["fuel_type"]:
                if i + 1 < len(lines):
                    car_data["fuel_type"] = lines[i+1].strip()

            # Transmission - look for "Växellåda" label
            if line_lower == "växellåda" and not car_data["transmission"]:
                if i + 1 < len(lines):
                    car_data["transmission"] = lines[i+1].strip()

            # Engine power - look for "Motoreffekt" label
            if line_lower == "motoreffekt" and not car_data["engine_power"]:
                if i + 1 < len(lines):
                    car_data["engine_power"] = lines[i+1].strip()

            # Driving type - look for "Körning" label
            if line_lower == "körning" and not car_data["driving_type"]:
                if i + 1 < len(lines):
                    car_data["driving_type"] = lines[i+1].strip()

            # Color - look for "Färg" label
            if line_lower == "färg" and not car_data["color"]:
                if i + 1 < len(lines):
                    car_data["color"] = lines[i+1].strip()

            # Location - PRIMARY: look for "Tillgänglig på" (Available at) label
            if not car_data["location"] and "tillgänglig på" in line_lower:
                if i + 1 < len(lines):
                    location_text = lines[i+1].strip()
                    # Try to extract city from the location text
                    city = parse_city_from_volvo_text(location_text)
                    if city:
                        car_data["location"] = city
                    elif location_text:
                        # If we can't parse it, just use the raw text (cleaned up)
                        car_data["location"] = location_text.upper()

            # Location - FALLBACK: look for "Volvo Car - [CITY]" pattern
            if not car_data["location"] and ('volvo car -' in line.lower() or 'volvo - ' in line.lower()):
                city = parse_city_from_volvo_text(line)
                if city:
                    car_data["location"] = city

            # Volvo Selekt certification - look for "Volvo Selekt Fördelar" section
            # Handle various encodings: fördelar, fordelar, f�rdelar
            if "volvo selekt" in line_lower:
                if "fördelar" in line_lower or "fordelar" in line_lower or "rdelar" in line_lower:
                    car_data["franchise_approved"] = True

        # Click "Standardutrustning" tab to get standard equipment
        try:
            standard_clicked = driver.execute_script("""
                var buttons = document.querySelectorAll('button, [role="tab"]');
                for (var btn of buttons) {
                    if (btn.textContent.toLowerCase().includes('standardutrustning')) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            """)

            if standard_clicked:
                time.sleep(1)

                # Click "Visa mer" if present
                try:
                    visa_mer_clicked = driver.execute_script("""
                        var buttons = document.querySelectorAll('button');
                        for (var btn of buttons) {
                            var text = btn.textContent.toLowerCase();
                            if (text.includes('visa mer') || text.includes('show more')) {
                                btn.click();
                                return true;
                            }
                        }
                        return false;
                    """)
                    if visa_mer_clicked:
                        time.sleep(0.5)  # Brief wait for expansion
                except:
                    pass

                # Extract standard equipment
                page_text_standard = driver.find_element(By.TAG_NAME, "body").text
                lines_standard = [l.strip() for l in page_text_standard.split("\n") if l.strip()]

                standard_list = []
                in_standard = False
                for line in lines_standard:
                    if "standardutrustning" in line.lower():
                        in_standard = True
                        continue
                    if in_standard:
                        # Stop at next section
                        if line.lower() in ["extrautrustning", "specifikationer", "finansiering",
                                           "kontakta", "boka", "om fordonet", "historik", "dela"]:
                            break
                        # Skip navigation/button text
                        if any(x in line.lower() for x in ["visa alla", "visa färre", "visa mer",
                                                           "föregående", "nästa"]):
                            continue
                        # Skip section headers (short, all caps)
                        if len(line) < 50 and not any(c.islower() for c in line):
                            continue
                        if line and len(line) > 2:
                            standard_list.append(line)

                if standard_list:
                    car_data["standard_equipment"] = " | ".join(standard_list)
        except Exception as e:
            pass  # Standard equipment is optional, don't fail if we can't get it

        # Click "Extrautrustning" tab to get extras
        try:
            extras_clicked = driver.execute_script("""
                var buttons = document.querySelectorAll('button, [role="tab"]');
                for (var btn of buttons) {
                    if (btn.textContent.toLowerCase().includes('extrautrustning')) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            """)

            if extras_clicked:
                time.sleep(1)

                # Click "Visa mer" if present
                try:
                    visa_mer_clicked = driver.execute_script("""
                        var buttons = document.querySelectorAll('button');
                        for (var btn of buttons) {
                            var text = btn.textContent.toLowerCase();
                            if (text.includes('visa mer') || text.includes('show more')) {
                                btn.click();
                                return true;
                            }
                        }
                        return false;
                    """)
                    if visa_mer_clicked:
                        time.sleep(0.5)
                except:
                    pass

                # Get the extras content
                page_text_after = driver.find_element(By.TAG_NAME, "body").text
                lines_after = [l.strip() for l in page_text_after.split("\n") if l.strip()]

                # Find the extras section - collect lines after "Extrautrustning"
                extras_list = []
                in_extras = False
                for line in lines_after:
                    if "extrautrustning" in line.lower():
                        in_extras = True
                        continue
                    if in_extras:
                        # Stop at next section header or navigation elements
                        if line.lower() in ["specifikationer", "finansiering", "kontakta", "boka",
                                           "om fordonet", "historik", "pris:", "dela"]:
                            break
                        # Skip navigation/button text
                        if any(x in line.lower() for x in ["visa alla", "visa färre", "visa mer",
                                                           "föregående", "nästa"]):
                            continue
                        # Skip if it looks like a section header
                        if len(line) < 50 and not any(c.islower() for c in line):
                            continue
                        if line and len(line) > 2:
                            extras_list.append(line)

                if extras_list:
                    car_data["extras"] = " | ".join(extras_list)  # No limit - get all features
        except Exception as e:
            pass  # Extras are optional, don't fail if we can't get them

        # JavaScript fallback for location extraction
        if not car_data["location"]:
            try:
                # Search for "Tillgänglig på" text followed by location
                location_text = driver.execute_script("""
                    var allText = document.body.innerText;
                    var lines = allText.split('\\n');
                    for (var i = 0; i < lines.length; i++) {
                        var line = lines[i].trim().toLowerCase();
                        if (line.includes('tillgänglig på')) {
                            // Get the next non-empty line
                            for (var j = i + 1; j < lines.length && j < i + 3; j++) {
                                var nextLine = lines[j].trim();
                                if (nextLine && nextLine.length > 2 && nextLine.length < 50) {
                                    return nextLine;
                                }
                            }
                        }
                    }

                    // Fallback: Search headings for patterns like "Volvo Car - [CITY]"
                    var headings = document.querySelectorAll('h2, h3, h4');
                    for (var h of headings) {
                        var text = h.textContent.trim();
                        if (text.toLowerCase().includes('volvo') && text.includes(' - ')) {
                            return text;
                        }
                        if (text.includes(' - ')) {
                            return text;
                        }
                    }
                    return null;
                """)
                if location_text:
                    city = parse_city_from_volvo_text(location_text)
                    if city:
                        car_data["location"] = city
                    elif location_text:
                        car_data["location"] = location_text.upper()
            except:
                pass  # Location is optional

    except Exception as e:
        print(f"  Error scraping detail page: {e}")

    return car_data


def scrape_all_listings(driver, scrape_details=True):
    """Scrape all car listings by visiting each detail page."""
    all_cars = []
    seen_registrations = set()

    # First, collect all unique detail URLs
    detail_urls = collect_all_detail_urls(driver)
    print(f"\nCollected {len(detail_urls)} unique car URLs")

    if not detail_urls:
        return []

    # Now visit each detail page
    print(f"\nScraping details from {len(detail_urls)} car pages...")
    for i, url in enumerate(detail_urls):
        print(f"  [{i+1}/{len(detail_urls)}] Scraping: {url.split('/')[-1][:30]}...")

        car_data = scrape_detail_page_full(driver, url)

        # Deduplicate by registration number
        reg = car_data.get("registration_number", "")
        if reg and reg in seen_registrations:
            print(f"    Skipping duplicate: {reg}")
            continue
        if reg:
            seen_registrations.add(reg)

        # Only add if we got meaningful data
        # Debug: Log if price is missing
        if not car_data.get("price"):
            print(f"    WARNING: No price found for {car_data.get('registration_number', 'unknown')} at {url[:60]}")

        if car_data.get("price") or car_data.get("registration_number"):
            all_cars.append(car_data)
            variant = car_data.get('model_variant', '')[:30] or 'N/A'
            price = car_data.get('price')
            price_str = f"{price:,}" if price else "N/A"
            print(f"    {car_data.get('registration_number', 'N/A')} | "
                  f"{price_str} SEK | "
                  f"{car_data.get('model_year', 'N/A')} | {variant}")

        # Small delay to be polite
        time.sleep(0.5)

    return all_cars


def save_to_csv(cars, filepath):
    """Save car data to CSV file."""
    if not cars:
        print("No cars to save")
        return

    # Ensure output directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    # Add scrape date
    scrape_date = datetime.now().strftime("%Y-%m-%d")
    for car in cars:
        car["scrape_date"] = scrape_date

    fieldnames = [
        "registration_number", "price", "model_year", "model_variant",
        "fuel_type", "engine_power", "transmission", "driving_type",
        "color", "mileage", "location", "standard_equipment", "extras",
        "franchise_approved", "detail_url", "scrape_date"
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cars)

    print(f"\nSaved {len(cars)} cars to: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Scrape Volvo XC60 listings")
    parser.add_argument("--visible", action="store_true", help="Run with visible browser (default: headless)")
    args = parser.parse_args()

    print("=" * 60)
    print("Volvo XC60 Scraper")
    print("=" * 60)

    driver = setup_driver(headless=not args.visible)

    try:
        cars = scrape_all_listings(driver)
        save_to_csv(cars, OUTPUT_FILE)

        # Print summary
        if cars:
            prices = [c["price"] for c in cars if c.get("price")]
            years = [c["model_year"] for c in cars if c.get("model_year")]
            if prices:
                print(f"\nSummary:")
                print(f"  Total unique cars: {len(cars)}")
                print(f"  Price range: {min(prices):,} - {max(prices):,} SEK")
                print(f"  Average price: {sum(prices)//len(prices):,} SEK")
            if years:
                print(f"  Model years: {min(years)} - {max(years)}")

    finally:
        driver.quit()
        print("\nDone!")


if __name__ == "__main__":
    main()

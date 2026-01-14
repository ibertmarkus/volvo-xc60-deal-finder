"""
Bilia Volvo XC60 Scraper - Scrapes used Volvo XC60 listings from Bilia.se.

Usage:
    python scraper_bilia.py           # Run with visible browser
    python scraper_bilia.py --headless # Run in headless mode
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
BASE_URL = "https://www.bilia.se/bilar/sok-bil/?brand=volvo&model=xc60"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "bilia_xc60_listings.csv")
WAIT_TIMEOUT = 15

# Comprehensive Swedish cities list - matches clean_data.py
SWEDISH_CITIES = {
    # Major cities (population > 50k)
    'STOCKHOLM', 'GÖTEBORG', 'MALMÖ', 'UPPSALA', 'VÄSTERÅS', 'ÖREBRO',
    'LINKÖPING', 'HELSINGBORG', 'NORRKÖPING', 'JÖNKÖPING', 'UMEÅ',
    'LUND', 'BORÅS', 'ESKILSTUNA', 'GÄVLE', 'SÖDERTÄLJE', 'KARLSTAD',
    'HALMSTAD', 'VÄXJÖ', 'SUNDSVALL', 'TROLLHÄTTAN', 'ÖSTERSUND',
    'FALUN', 'SKELLEFTEÅ', 'KRISTIANSTAD', 'KALMAR', 'KUNGÄLV',
    # Medium cities (population 20k-50k)
    'LIDKÖPING', 'SKÖVDE', 'UDDEVALLA', 'MOTALA', 'TRELLEBORG',
    'KARLSKRONA', 'VARBERG', 'ÄNGELHOLM', 'NYKÖPING', 'SANDVIKEN',
    'LIDINGÖ', 'BOLLNÄS', 'ÖRNSKÖLDSVIK', 'LANDSKRONA', 'YSTAD',
    # Dealership cities identified in data
    'LINDESBERG', 'FINSPÅNG', 'MJÖLBY', 'HALLSBERG', 'ÅTVIDABERG',
    'UPPLANDS VÄSBY', 'TÄBY', 'SOLLENTUNA', 'SOLNA', 'NACKA',
    'JÄGERSRO', 'KUNGSÄNGEN', 'HANINGE', 'SISJÖN', 'KISTA',
    'SEGELTORP', 'HUDDINGE', 'MÄRSTA', 'UPPLANDS BRO', 'TIMRÅ',
    'ARÖD', 'ÖSTHAMMAR', 'ARVIKA', 'SALA', 'VARA',
    'LAHOLM', 'ENKÖPING', 'HAMMARBY SJÖSTAD', 'VIMMERBY', 'LJUSDAL',
    'HUDIKSVALL', 'VALLENTUNA', 'ESLÖV', 'KRISTINEHAMN',
    'ALINGSÅS', 'ÅMÅL', 'DINGLE', 'FALKÖPING', 'LYSEKIL',
    'MARIESTAD', 'MELLERUD', 'STRÖMSTAD', 'VÄNERSBORG',
    'HÄRNÖSAND', 'KALIX', 'STRÖMSUND', 'NORRTÄLJE',
    'SANDVIKEN', 'SÖDERHAMN', 'VISBY', 'KÖPING', 'STRÄNGNÄS',
    'KUNGSBACKA', 'STENUNGSUND', 'BRO', 'VÄRNHEM', 'KUNGENS KURVA',
    'SÄVEDALEN'
}


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
        # Common cookie button patterns for Swedish sites
        cookie_selectors = [
            "//button[contains(text(), 'Acceptera')]",
            "//button[contains(text(), 'Godkänn')]",
            "//button[contains(text(), 'Tillåt')]",
            "//button[contains(text(), 'Accept')]",
            "//button[contains(@id, 'accept')]",
            "//button[contains(@class, 'accept')]",
            "//*[@id='onetrust-accept-btn-handler']",
            "//button[contains(@class, 'cookie')]//button",
            "//*[@id='CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll']",
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
    selectors = [
        (By.CSS_SELECTOR, ".car-card"),
        (By.CSS_SELECTOR, "[class*='car-card']"),
        (By.CSS_SELECTOR, ".listlayout__item"),
        (By.XPATH, "//a[contains(@href, '/bilar/sok-bil/volvo/xc60/')]"),
    ]
    for by, selector in selectors:
        try:
            wait.until(EC.presence_of_all_elements_located((by, selector)))
            print(f"Found listings using selector: {selector}")
            return True
        except:
            continue
    return False


def load_all_cars(driver, max_clicks=50):
    """Scroll and click 'Ladda fler' button until all cars are loaded."""
    click_count = 0
    last_url_count = 0
    no_change_count = 0

    while click_count < max_clicks:
        # Count current car URLs
        current_urls = get_car_detail_urls(driver, verbose=False)
        current_count = len(current_urls)

        if current_count == last_url_count:
            no_change_count += 1
            if no_change_count >= 3:
                print(f"No new cars for 3 iterations. Total: {current_count}")
                break
        else:
            no_change_count = 0
            last_url_count = current_count

        print(f"Current car URL count: {current_count}")

        # Scroll to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)

        # Try to find and click "Ladda fler" button using JavaScript
        clicked = driver.execute_script("""
            // Look for buttons with "ladda fler" or "visa fler" text
            var buttons = document.querySelectorAll('button, a.g-button');
            for (var btn of buttons) {
                var text = btn.textContent.toLowerCase();
                if ((text.includes('ladda fler') || text.includes('visa fler')) &&
                    btn.offsetParent !== null) {
                    btn.scrollIntoView({block: 'center'});
                    btn.click();
                    return true;
                }
            }

            // Also check for load more elements by class
            var loadMore = document.querySelector('.car-list__load button, [class*="load-more"] button');
            if (loadMore && loadMore.offsetParent !== null) {
                loadMore.scrollIntoView({block: 'center'});
                loadMore.click();
                return true;
            }

            return false;
        """)

        if clicked:
            click_count += 1
            print(f"Clicked 'Ladda fler' ({click_count})")
            time.sleep(2)  # Wait for new cars to load
        else:
            # No button found, try scrolling more
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)

    # Final count
    final_urls = get_car_detail_urls(driver, verbose=False)
    print(f"Total cars loaded: {len(final_urls)}")
    return len(final_urls)


def get_car_detail_urls(driver, verbose=True):
    """Extract all unique car detail page URLs."""
    urls = set()

    # Get all links with the specific pattern for XC60 detail pages
    # Pattern: /bilar/sok-bil/volvo/xc60/[id]/
    all_links = driver.find_elements(By.TAG_NAME, "a")

    for link in all_links:
        try:
            href = link.get_attribute("href")
            if href:
                # Match the specific pattern for XC60 detail pages
                # e.g., /bilar/sok-bil/volvo/xc60/afs27t/
                if re.search(r'/bilar/sok-bil/volvo/xc60/[a-z0-9]+/?$', href, re.IGNORECASE):
                    urls.add(href.rstrip('/') + '/')
        except:
            continue

    if verbose:
        print(f"Found {len(urls)} unique car detail URLs")
        if urls and len(urls) <= 5:
            print("Sample URLs:")
            for url in list(urls)[:5]:
                print(f"  {url}")

    return list(urls)


def parse_price(text):
    """Extract numeric price from Swedish format like '614 900 kr'."""
    if not text:
        return None
    # Swedish format: space as thousands separator
    cleaned = text.lower().replace("kr", "").replace(" ", "").replace("\xa0", "").replace(".", "")
    # Remove decimal part
    if "," in cleaned:
        cleaned = cleaned.split(",")[0]
    numbers = re.findall(r'\d+', cleaned)
    if numbers:
        return int("".join(numbers))
    return None


def parse_mileage(text):
    """Extract mileage from text like '5 230 mil' or '52 300 km'."""
    if not text:
        return None
    text_lower = text.lower()
    numbers = re.findall(r'\d+', text.replace(" ", "").replace("\xa0", ""))
    if numbers:
        value = int("".join(numbers))
        # Convert mil to km if needed (1 mil = 10 km in Swedish)
        if "mil" in text_lower and "km" not in text_lower:
            value = value * 10
        return value
    return None


def is_valid_swedish_city(text):
    """Validate if text is a known Swedish city."""
    if not text:
        return False
    text_upper = text.upper().strip()
    return text_upper in SWEDISH_CITIES


def parse_city_from_dealer_text(text):
    """Extract city from Bilia dealer name with comprehensive strategies.

    Handles patterns like:
    - 'Bilia Södertälje Volvo'
    - 'Bilia Outlet Bilhall Hisingen Aröd' (extracts 'ARÖD')
    - 'Bilia [CITY] - Volvo'
    """
    if not text:
        return None

    import re
    text_upper = text.upper()

    # Strategy 1: Check multi-word cities first (e.g., UPPLANDS VÄSBY)
    for city in sorted(SWEDISH_CITIES, key=lambda x: -len(x)):  # Longest first
        if ' ' in city and city in text_upper:
            return city

    # Strategy 2: Try "Bilia [CITY] Volvo" pattern
    match = re.search(r'Bilia\s+([A-ZÅÄÖa-zåäö\s]+?)\s+(?:-\s*)?Volvo', text, re.IGNORECASE)
    if match:
        city = match.group(1).strip().upper()
        if is_valid_swedish_city(city):
            return city

    # Strategy 3: Handle " - " splitting
    if ' - ' in text:
        parts = [p.strip() for p in text.split(' - ')]
        for part in parts:
            part_upper = part.upper()
            if is_valid_swedish_city(part_upper):
                return part_upper

    # Strategy 4: Extract last word (handles "Bilia Outlet Bilhall Hisingen Aröd")
    words = text_upper.split()
    if words:
        # Try last word
        last_word = words[-1].strip(',-()').upper()
        if is_valid_swedish_city(last_word):
            return last_word

        # Try second-to-last word (in case last is "VOLVO")
        if len(words) >= 2:
            second_last = words[-2].strip(',-()').upper()
            if is_valid_swedish_city(second_last):
                return second_last

    # Strategy 5: Word-by-word search for any known city
    for word in words:
        word_clean = word.strip(',-()').upper()
        if is_valid_swedish_city(word_clean):
            return word_clean

    return None


def scrape_detail_page(driver, url, debug=False):
    """Scrape all details from a car's detail page."""
    # Extract registration number from URL (e.g., "xzr02s" from ".../xzr02s/")
    url_parts = url.rstrip('/').split('/')
    registration_from_url = url_parts[-1].upper() if url_parts else ""

    car_data = {
        "url": url,
        "price": None,
        "mileage": None,
        "model_year": None,
        "version": "",        # Model variant (e.g., "Recharge T6 Plus Bright")
        "color": "",          # Färg
        "fuel_type": "",      # Bränsle
        "drive_wheels": "",   # Drivhjul (e.g., Fyrhjulsdrift)
        "electric_type": "",  # Typ av elbil (e.g., Laddhybrid)
        "transmission": "",   # Växellåda
        "engine_power": "",   # Motoreffekt
        "engine_name": "",    # Motornamn (full engine spec)
        "body_type": "",      # Karosstyp (e.g., SUV)
        "location": "",       # Dealer location
        "registration": registration_from_url,  # From URL
    }

    try:
        driver.get(url)
        time.sleep(2)

        page_text = driver.find_element(By.TAG_NAME, "body").text
        lines = [l.strip() for l in page_text.split("\n") if l.strip()]

        # Debug: print first 100 lines to understand structure
        if debug:
            print("DEBUG - First 100 lines of page:")
            for i, line in enumerate(lines[:100]):
                print(f"  {i}: {line}")

        # Parse key-value pairs from the page
        for i, line in enumerate(lines):
            line_lower = line.lower()

            # Version - look for patterns like "Recharge T6 Plus Bright" after "Volvo XC60"
            if "volvo xc60" in line_lower and not car_data["version"]:
                # Check the next few lines for the variant
                for j in range(i+1, min(i+4, len(lines))):
                    next_line = lines[j].strip()
                    # Skip navigation elements
                    if next_line and not any(x in next_line.lower() for x in
                            ["föregående", "nästa", "meny", "tillbaka", "kr", "sälj", "köp"]):
                        # Look for version patterns (T6, T8, B5, etc.)
                        if re.search(r'(recharge|t[4568]|b[456]|d[345]|plus|core|inscription|ultimate)',
                                    next_line, re.IGNORECASE):
                            car_data["version"] = next_line
                            break

            # Price - look for "Kontantpris" or price patterns
            if ("kontantpris" in line_lower or "pris" in line_lower) and not car_data["price"]:
                # Check same line for price
                price_match = re.search(r'(\d[\d\s]*\d)\s*kr', line, re.IGNORECASE)
                if price_match:
                    car_data["price"] = parse_price(price_match.group(1) + " kr")
                elif i + 1 < len(lines):
                    price = parse_price(lines[i+1])
                    if price and price > 50000:
                        car_data["price"] = price

            # Model year - Modellår or Årsmodell
            if ("modellår" in line_lower or "årsmodell" in line_lower) and not car_data["model_year"]:
                year_match = re.search(r'20[0-2]\d', line)
                if year_match:
                    car_data["model_year"] = int(year_match.group())
                elif i + 1 < len(lines):
                    year_match = re.search(r'20[0-2]\d', lines[i+1])
                    if year_match:
                        car_data["model_year"] = int(year_match.group())

            # Mileage - Miltal or Mätarställning, or standalone "XXX mil"
            if ("miltal" in line_lower or "mätarställning" in line_lower) and not car_data["mileage"]:
                # Check same line
                mileage_match = re.search(r'(\d[\d\s]*)\s*(mil|km)', line, re.IGNORECASE)
                if mileage_match:
                    car_data["mileage"] = parse_mileage(mileage_match.group(0))
                elif i + 1 < len(lines):
                    car_data["mileage"] = parse_mileage(lines[i+1])

            # Also check for standalone mileage format like "25479 mil"
            # Only match "mil" to avoid confusion with electric range (e.g., "82 km")
            if car_data["mileage"] is None:
                standalone_mileage = re.match(r'^(\d[\d\s]*)\s*mil$', line.strip(), re.IGNORECASE)
                if standalone_mileage:
                    car_data["mileage"] = parse_mileage(line)

            # Fuel type - Bränsle
            if line_lower == "bränsle" and not car_data["fuel_type"]:
                if i + 1 < len(lines):
                    car_data["fuel_type"] = lines[i+1].strip()

            # Color - Färg
            if line_lower == "färg" and not car_data["color"]:
                if i + 1 < len(lines):
                    car_data["color"] = lines[i+1].strip()

            # Drive wheels - Drivhjul
            if line_lower == "drivhjul" and not car_data["drive_wheels"]:
                if i + 1 < len(lines):
                    car_data["drive_wheels"] = lines[i+1].strip()

            # Electric type - Typ av elbil / Motortyp / Hybrid type
            if ("typ av elbil" in line_lower or "motortyp" in line_lower or
                "hybridtyp" in line_lower) and not car_data["electric_type"]:
                if i + 1 < len(lines):
                    car_data["electric_type"] = lines[i+1].strip()

            # Also detect electric type from fuel type
            if not car_data["electric_type"]:
                if "laddhybrid" in line_lower:
                    car_data["electric_type"] = "Laddhybrid"
                elif "elbil" in line_lower and "mildhybrid" not in line_lower:
                    car_data["electric_type"] = "Elbil"
                elif "mildhybrid" in line_lower:
                    car_data["electric_type"] = "Mildhybrid"

            # Transmission - Växellåda
            if line_lower == "växellåda" and not car_data["transmission"]:
                if i + 1 < len(lines):
                    car_data["transmission"] = lines[i+1].strip()

            # Engine power - Motoreffekt / Effekt / Hästkrafter
            if (line_lower in ["motoreffekt", "effekt", "hästkrafter"] and
                not car_data["engine_power"]):
                if i + 1 < len(lines):
                    car_data["engine_power"] = lines[i+1].strip()

            # Body type - Karosstyp
            if line_lower == "karosstyp" and not car_data["body_type"]:
                if i + 1 < len(lines):
                    car_data["body_type"] = lines[i+1].strip()

            # Registration number pattern (ABC123 or ABC12A) - look for it near "Registreringsnummer" label
            # Skip common placeholders like "ABC 123"
            if "registreringsnummer" in line_lower or "reg.nr" in line_lower or "regnr" in line_lower:
                if i + 1 < len(lines):
                    next_line = lines[i+1].strip().upper().replace(" ", "")
                    # Valid Swedish registration: 3 letters + 2-3 digits + optional letter/digit
                    if re.match(r'^[A-Z]{3}\d{2,3}[A-Z0-9]?$', next_line) and next_line != "ABC123":
                        car_data["registration"] = next_line

        # Try to extract price from JavaScript data if not found
        if not car_data["price"]:
            try:
                price_js = driver.execute_script("""
                    // Look for price in various places
                    var priceEl = document.querySelector('[class*="price"], [class*="Price"]');
                    if (priceEl) return priceEl.textContent;

                    // Check for data attributes
                    var carCard = document.querySelector('[data-price]');
                    if (carCard) return carCard.dataset.price;

                    return null;
                """)
                if price_js:
                    car_data["price"] = parse_price(price_js)
            except:
                pass

        # Enhanced location extraction - multi-strategy approach
        try:
            # Strategy 1: Look for "Anläggning" field (PRIMARY METHOD for Bilia)
            page_text = driver.find_element(By.TAG_NAME, "body").text
            lines = [l.strip() for l in page_text.split("\n") if l.strip()]
            for i, line in enumerate(lines):
                if "anläggning" in line.lower():
                    # Next line should have the location
                    if i + 1 < len(lines):
                        location_text = lines[i+1].strip()
                        # Only accept if it contains "Bilia" (to avoid navigation menu matches)
                        if "bilia" in location_text.lower():
                            city = parse_city_from_dealer_text(location_text)
                            if city:
                                car_data["location"] = city
                                if debug:
                                    print(f"  Location from Anläggning field: {city}")
                                break
                            elif location_text:
                                # If we can't parse it, just use the raw text
                                car_data["location"] = location_text.upper()
                                if debug:
                                    print(f"  Location from Anläggning field (raw): {location_text.upper()}")
                                break

            # Strategy 2: Extract from H2 heading containing "Bilia"
            if not car_data["location"]:
                dealer_heading = driver.execute_script("""
                    var headings = document.querySelectorAll('h2, h3');
                    for (var h of headings) {
                        var text = h.textContent;
                        if (text.toLowerCase().includes('bilia') && text.toLowerCase().includes('volvo')) {
                            return text.trim();
                        }
                    }
                    return null;
                """)
                if dealer_heading:
                    city = parse_city_from_dealer_text(dealer_heading)
                    if city:
                        car_data["location"] = city
                        if debug:
                            print(f"  Location from heading: {city}")

            # Strategy 3: Extract from branch block elements
            if not car_data["location"]:
                branch_location = driver.execute_script("""
                    var selectors = [
                        '[class*="branch"]',
                        '[id*="branch"]',
                        '[class*="anlaggning"]'
                    ];
                    for (var sel of selectors) {
                        var el = document.querySelector(sel);
                        if (el) {
                            // Try to find heading within branch block
                            var heading = el.querySelector('h2, h3, h4');
                            if (heading) return heading.textContent.trim();
                            // Or return full text
                            return el.textContent.trim().substring(0, 200);
                        }
                    }
                    return null;
                """)
                if branch_location:
                    city = parse_city_from_dealer_text(branch_location)
                    if city:
                        car_data["location"] = city
                        if debug:
                            print(f"  Location from branch block: {city}")

            # Strategy 4: Extract from JSON-LD schema (seller.address.addressLocality)
            if not car_data["location"]:
                schema_location = driver.execute_script("""
                    var scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    for (var script of scripts) {
                        try {
                            var data = JSON.parse(script.textContent);
                            if (data.seller && data.seller.address && data.seller.address.addressLocality) {
                                return data.seller.address.addressLocality;
                            }
                            // Also check if seller.name contains city
                            if (data.seller && data.seller.name) {
                                return data.seller.name;
                            }
                        } catch(e) {}
                    }
                    return null;
                """)
                if schema_location:
                    city = parse_city_from_dealer_text(schema_location)
                    if not city:
                        # Try direct validation if it's just a city name
                        if is_valid_swedish_city(schema_location):
                            city = schema_location.upper()
                    if city:
                        car_data["location"] = city
                        if debug:
                            print(f"  Location from JSON-LD: {city}")
        except Exception as e:
            if debug:
                print(f"  Could not extract location: {e}")

        # Extract engine power and transmission from JSON-LD schema data
        try:
            schema_data = driver.execute_script("""
                var scripts = document.querySelectorAll('script[type="application/ld+json"]');
                for (var script of scripts) {
                    try {
                        var data = JSON.parse(script.textContent);
                        if (data['@type'] === 'Car' || data['@type'] === 'Vehicle') {
                            return {
                                enginePower: data.vehicleEngine?.enginePower?.value || null,
                                transmission: data.vehicleTransmission || null
                            };
                        }
                    } catch(e) {}
                }
                return null;
            """)
            if schema_data:
                if schema_data.get('enginePower') and not car_data["engine_power"]:
                    car_data["engine_power"] = f"{schema_data['enginePower']} hk"
                if schema_data.get('transmission') and not car_data["transmission"]:
                    trans = schema_data['transmission'].lower()
                    if 'auto' in trans:
                        car_data["transmission"] = "Automat"
                    elif 'manu' in trans:
                        car_data["transmission"] = "Manuell"
                    else:
                        car_data["transmission"] = schema_data['transmission']
        except Exception as e:
            if debug:
                print(f"  Could not extract schema data: {e}")

        # Also look for transmission/gearbox in the page summary text
        if not car_data["transmission"]:
            for line in lines:
                line_clean = line.strip()
                if line_clean.lower() in ["automat", "automatväxellåda", "automatlåda"]:
                    car_data["transmission"] = "Automat"
                    break
                elif line_clean.lower() in ["manuell", "manuellväxellåda"]:
                    car_data["transmission"] = "Manuell"
                    break

        # Click "Motor och miljö" tab to get transmission and engine details
        try:
            clicked = driver.execute_script("""
                var tabs = document.querySelectorAll('button, [role="tab"], a');
                for (var tab of tabs) {
                    var text = tab.textContent.toLowerCase();
                    if (text.includes('motor och milj') || text.includes('motor & milj')) {
                        tab.scrollIntoView({block: 'center'});
                        tab.click();
                        return true;
                    }
                }
                return false;
            """)

            if clicked:
                time.sleep(1)  # Wait for tab content to load

                # Get the updated page text
                motor_text = driver.find_element(By.TAG_NAME, "body").text
                motor_lines = [l.strip() for l in motor_text.split("\n") if l.strip()]

                for i, line in enumerate(motor_lines):
                    line_lower = line.lower()

                    # Transmission - Automatlåda or Växellåda
                    if ("automatlåda" in line_lower or "växellåda" in line_lower) and not car_data["transmission"]:
                        if i + 1 < len(motor_lines):
                            next_val = motor_lines[i+1].strip()
                            # Check if value is on same line
                            if ":" in line:
                                next_val = line.split(":")[-1].strip()
                            if next_val and next_val.lower() not in ["ja", "nej", "yes", "no"]:
                                car_data["transmission"] = next_val
                            elif next_val.lower() == "ja":
                                car_data["transmission"] = "Automat"

                    # Engine name - Motornamn
                    if "motornamn" in line_lower and not car_data["engine_name"]:
                        if i + 1 < len(motor_lines):
                            next_val = motor_lines[i+1].strip()
                            if ":" in line:
                                next_val = line.split(":")[-1].strip()
                            if next_val:
                                car_data["engine_name"] = next_val

                    # Also look for Hästkrafter (horsepower) if engine_power not set
                    if ("hästkrafter" in line_lower or "effekt" in line_lower) and not car_data["engine_power"]:
                        if i + 1 < len(motor_lines):
                            next_val = motor_lines[i+1].strip()
                            if ":" in line:
                                next_val = line.split(":")[-1].strip()
                            # Look for number followed by hk or hp
                            hp_match = re.search(r'(\d+)\s*(hk|hp|hästkrafter)?', next_val, re.IGNORECASE)
                            if hp_match:
                                car_data["engine_power"] = next_val

        except Exception as e:
            if debug:
                print(f"  Could not click Motor och miljö tab: {e}")

    except Exception as e:
        print(f"  Error scraping {url}: {e}")

    return car_data


def scrape_all_listings(driver):
    """Scrape all car listings."""
    all_cars = []

    print(f"Loading: {BASE_URL}")
    driver.get(BASE_URL)
    time.sleep(3)

    accept_cookies(driver)

    if not wait_for_listings(driver):
        print("ERROR: Could not find any car listings.")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(os.path.join(OUTPUT_DIR, "debug_bilia_page.html"), "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("Saved debug HTML to debug_bilia_page.html")
        return []

    # Load all cars by clicking "Ladda fler"
    print("\nLoading all cars...")
    load_all_cars(driver)

    # Save listing page HTML for debugging
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "debug_bilia_listing.html"), "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("Saved listing page HTML for debugging")

    # Get all detail URLs
    print("\nCollecting detail URLs...")
    detail_urls = get_car_detail_urls(driver)

    if not detail_urls:
        print("No car detail URLs found!")
        return []

    # Visit each detail page
    print(f"\nScraping {len(detail_urls)} car detail pages...")
    for i, url in enumerate(detail_urls):
        car_id = url.rstrip('/').split('/')[-1]
        print(f"  [{i+1}/{len(detail_urls)}] {car_id}...")

        # Debug first car to see page structure
        car_data = scrape_detail_page(driver, url, debug=(i == 0))

        # Only add if we got meaningful data
        if car_data.get("price") or car_data.get("version") or car_data.get("model_year"):
            all_cars.append(car_data)
            price_str = f"{car_data.get('price', 0):,}" if car_data.get('price') else 'N/A'
            print(f"    Price: {price_str} | "
                  f"Year: {car_data.get('model_year', 'N/A')} | "
                  f"Version: {car_data.get('version', 'N/A')[:25]}")
        else:
            print(f"    [No data extracted]")

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
        "registration", "price", "mileage", "model_year", "version",
        "color", "fuel_type", "drive_wheels", "electric_type",
        "transmission", "engine_power", "engine_name", "body_type",
        "location", "url", "scrape_date"
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cars)

    print(f"\nSaved {len(cars)} cars to: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Scrape Bilia Volvo XC60 listings")
    parser.add_argument("--headless", action="store_true", default=True, help="Run in headless mode (default)")
    parser.add_argument("--visible", action="store_true", help="Run with visible browser")
    args = parser.parse_args()

    print("=" * 60)
    print("Bilia Volvo XC60 Scraper")
    print("=" * 60)

    # Use headless by default, --visible overrides
    headless = not args.visible
    driver = setup_driver(headless=headless)

    try:
        cars = scrape_all_listings(driver)
        save_to_csv(cars, OUTPUT_FILE)

        # Print summary
        if cars:
            prices = [c["price"] for c in cars if c.get("price")]
            years = [c["model_year"] for c in cars if c.get("model_year")]
            fuel_types = set(c["fuel_type"] for c in cars if c.get("fuel_type"))
            electric_types = set(c["electric_type"] for c in cars if c.get("electric_type"))

            print(f"\n{'='*60}")
            print("SUMMARY")
            print("="*60)
            print(f"  Total cars scraped: {len(cars)}")
            if prices:
                print(f"  Price range: {min(prices):,} - {max(prices):,} SEK")
                print(f"  Average price: {sum(prices)//len(prices):,} SEK")
            if years:
                print(f"  Model years: {min(years)} - {max(years)}")
            if fuel_types:
                print(f"  Fuel types: {', '.join(sorted(fuel_types))}")
            if electric_types:
                print(f"  Electric types: {', '.join(sorted(electric_types))}")

    finally:
        driver.quit()
        print("\nDone!")


if __name__ == "__main__":
    main()

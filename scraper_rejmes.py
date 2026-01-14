"""
Rejmes Volvo XC60 Scraper - Scrapes used Volvo XC60 listings from Rejmes.se.

Usage:
    python scraper_rejmes.py           # Run with visible browser
    python scraper_rejmes.py --headless # Run in headless mode
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
BASE_URL = "https://rejmes.se/bilar/begagnade-bilar/begagnade-volvo/begagnade-volvo-xc60/?brandName=Volvo&modelName=XC60&statusName=Begagnade"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "rejmes_xc60_listings.csv")
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
        # Common cookie button patterns for Swedish sites
        cookie_selectors = [
            "//button[contains(text(), 'Acceptera')]",
            "//button[contains(text(), 'Godkänn')]",
            "//button[contains(text(), 'Tillåt')]",
            "//button[contains(text(), 'Accept')]",
            "//button[contains(@id, 'accept')]",
            "//button[contains(@class, 'accept')]",
            "//*[@id='onetrust-accept-btn-handler']",
            "//*[@id='CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll']",
            "//button[contains(@class, 'cookie')]",
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
        (By.CSS_SELECTOR, "[class*='vehicle-card']"),
        (By.CSS_SELECTOR, "[class*='CarCard']"),
        (By.CSS_SELECTOR, "article"),
        (By.XPATH, "//a[contains(@href, '/bilar/') and contains(@href, 'volvo')]"),
    ]
    for by, selector in selectors:
        try:
            wait.until(EC.presence_of_all_elements_located((by, selector)))
            print(f"Found listings using selector: {selector}")
            return True
        except:
            continue
    return False


def load_all_cars(driver, max_clicks=20):
    """Click 'Visa fler bilar' button until all cars are loaded."""
    click_count = 0
    last_car_count = 0
    no_change_count = 0

    while click_count < max_clicks:
        # Count current car cards
        current_cards = driver.find_elements(By.CSS_SELECTOR,
            "[class*='car-card'], [class*='vehicle-card'], [class*='CarCard'], article[class*='car']")
        current_count = len(current_cards)

        if current_count == last_car_count:
            no_change_count += 1
            if no_change_count >= 3:
                print(f"No new cars for 3 iterations. Total: {current_count}")
                break
        else:
            no_change_count = 0
            last_car_count = current_count

        print(f"Current car count: {current_count}")

        # Scroll to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1.5)

        # Try to find and click "Visa fler bilar" button
        clicked = driver.execute_script("""
            // Look for buttons with "visa fler" text
            var buttons = document.querySelectorAll('button, a');
            for (var btn of buttons) {
                var text = btn.textContent.toLowerCase().trim();
                if ((text.includes('visa fler') || text.includes('ladda fler') ||
                     text.includes('load more') || text.includes('fler bilar')) &&
                    btn.offsetParent !== null) {
                    btn.scrollIntoView({block: 'center'});
                    btn.click();
                    return true;
                }
            }

            // Also look for any clickable element with "visa fler"
            var all = document.querySelectorAll('*');
            for (var el of all) {
                if (el.onclick || el.tagName === 'BUTTON' || el.tagName === 'A') {
                    var text = el.textContent.toLowerCase().trim();
                    if (text === 'visa fler bilar' || text === 'visa fler') {
                        el.scrollIntoView({block: 'center'});
                        el.click();
                        return true;
                    }
                }
            }

            return false;
        """)

        if clicked:
            click_count += 1
            print(f"Clicked 'Visa fler bilar' ({click_count})")
            time.sleep(2)  # Wait for new cars to load
        else:
            # Check if there's no more button (all loaded)
            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            if "visa fler" not in page_text:
                print("No 'Visa fler' button found - all cars loaded")
                break
            # Try scrolling more
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)

    # Final count
    final_cards = driver.find_elements(By.CSS_SELECTOR,
        "[class*='car-card'], [class*='vehicle-card'], [class*='CarCard'], article[class*='car']")
    print(f"Total cars loaded: {len(final_cards)}")
    return len(final_cards)


def get_car_detail_urls(driver, verbose=True):
    """Extract all unique car detail page URLs."""
    urls = set()

    # Get all links that look like car detail pages
    all_links = driver.find_elements(By.TAG_NAME, "a")

    for link in all_links:
        try:
            href = link.get_attribute("href")
            if href:
                # Match patterns for detail pages
                # e.g., /bilar/begagnade-bilar/.../[id]/ or /bil/[id]/
                if re.search(r'/bilar?/[^/]+/[^/]+/[^/]+/[a-z0-9-]+/?$', href, re.IGNORECASE):
                    urls.add(href.rstrip('/') + '/')
                # Also try simpler pattern
                elif '/bilar/' in href and re.search(r'/[a-z]{3}[0-9]{2,3}[a-z0-9]?/?$', href, re.IGNORECASE):
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
    cleaned = text.lower().replace("kr", "").replace("sek", "").replace(" ", "").replace("\xa0", "").replace(".", "")
    # Remove decimal part
    if "," in cleaned:
        cleaned = cleaned.split(",")[0]
    numbers = re.findall(r'\d+', cleaned)
    if numbers:
        result = int("".join(numbers))
        # Sanity check for car prices
        if result > 50000:
            return result
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


def scrape_from_listing_cards(driver):
    """Try to extract data directly from listing cards on the main page."""
    cars = []

    # Try various card selectors
    card_selectors = [
        "[class*='car-card']",
        "[class*='vehicle-card']",
        "[class*='CarCard']",
        "article[class*='car']",
        ".car-listing-item",
        "[data-testid*='car']",
    ]

    cards = []
    for selector in card_selectors:
        cards = driver.find_elements(By.CSS_SELECTOR, selector)
        if cards:
            print(f"Found {len(cards)} cards with selector: {selector}")
            break

    if not cards:
        # Fallback: find all links that look like car details and extract parent containers
        links = driver.find_elements(By.XPATH, "//a[contains(@href, '/bilar/')]")
        print(f"Found {len(links)} potential car links")

    return cars


def extract_car_data_from_text(page_text, url=""):
    """Extract car data from page text using pattern matching."""
    car_data = {
        "url": url,
        "price": None,
        "mileage": None,
        "model_year": None,
        "version": "",
        "color": "",
        "fuel_type": "",
        "drive_wheels": "",
        "electric_type": "",
        "transmission": "",
        "engine_power": "",
        "body_type": "",
        "location": "",
        "registration": "",
    }

    lines = [l.strip() for l in page_text.split("\n") if l.strip()]

    for i, line in enumerate(lines):
        line_lower = line.lower()

        # Registration number - standalone Swedish format (ABC123 or ABC12D)
        # Check early in parsing as it often appears near the top
        if not car_data["registration"]:
            reg_match = re.match(r'^([A-Z]{3}\d{2,3}[A-Z0-9]?)$', line.strip().upper())
            if reg_match and line.strip().upper() != "ABC123":
                car_data["registration"] = reg_match.group(1)

        # Version - look for XC60 variant patterns
        if "xc60" in line_lower and not car_data["version"]:
            # Check next lines for variant
            for j in range(i, min(i+5, len(lines))):
                next_line = lines[j].strip()
                if re.search(r'(recharge|t[4568]|b[456]|d[345]|plus|core|inscription|ultimate|momentum|r-design)',
                            next_line, re.IGNORECASE):
                    car_data["version"] = next_line
                    # Location often appears right after version
                    if j + 1 < len(lines) and not car_data["location"]:
                        loc_line = lines[j + 1].strip()
                        # Validate it's a city using helper function
                        city = parse_city_from_text(loc_line)
                        if city:
                            car_data["location"] = city
                    break

        # Scan for location in all lines (fallback strategy)
        if not car_data["location"] and len(line) > 3 and not any(char.isdigit() for char in line):
            # Skip lines that are clearly not locations
            if not any(x in line_lower for x in ["kr", "köp", "pris", "sälj", "mil", "bränsle", "växellåda"]):
                city = parse_city_from_text(line)
                if city:
                    car_data["location"] = city

        # Price patterns
        if not car_data["price"]:
            # Look for "XXX XXX kr" pattern
            price_match = re.search(r'(\d[\d\s]{4,}\d)\s*kr', line, re.IGNORECASE)
            if price_match:
                car_data["price"] = parse_price(price_match.group(0))
            # Look for label-value pairs
            elif "pris" in line_lower and i + 1 < len(lines):
                car_data["price"] = parse_price(lines[i+1])

        # Model year
        if ("modellår" in line_lower or "årsmodell" in line_lower or "år" == line_lower) and not car_data["model_year"]:
            year_match = re.search(r'20[0-2]\d', line)
            if year_match:
                car_data["model_year"] = int(year_match.group())
            elif i + 1 < len(lines):
                year_match = re.search(r'20[0-2]\d', lines[i+1])
                if year_match:
                    car_data["model_year"] = int(year_match.group())

        # Standalone year (4 digits on own line, 2015-2026)
        if not car_data["model_year"] and re.match(r'^20[12]\d$', line.strip()):
            car_data["model_year"] = int(line.strip())

        # Mileage
        if ("mil" in line_lower or "mätarställning" in line_lower) and not car_data["mileage"]:
            mileage_match = re.search(r'(\d[\d\s]*)\s*(mil|km)', line, re.IGNORECASE)
            if mileage_match:
                car_data["mileage"] = parse_mileage(mileage_match.group(0))
            elif i + 1 < len(lines):
                car_data["mileage"] = parse_mileage(lines[i+1])

        # Standalone mileage "XXXX mil"
        if not car_data["mileage"]:
            standalone_mileage = re.match(r'^(\d[\d\s]*)\s*mil$', line.strip(), re.IGNORECASE)
            if standalone_mileage:
                car_data["mileage"] = parse_mileage(line)

        # Fuel type
        if (line_lower == "bränsle" or line_lower == "drivmedel") and not car_data["fuel_type"]:
            if i + 1 < len(lines):
                car_data["fuel_type"] = lines[i+1].strip()
        # Direct fuel type detection
        elif not car_data["fuel_type"]:
            for fuel in ["diesel", "bensin", "el", "hybrid", "laddhybrid"]:
                if line_lower == fuel or line_lower.startswith(fuel + " "):
                    car_data["fuel_type"] = line.strip()
                    break

        # Electric type
        if "laddhybrid" in line_lower and not car_data["electric_type"]:
            car_data["electric_type"] = "Laddhybrid"
        elif "elbil" in line_lower and "mildhybrid" not in line_lower and not car_data["electric_type"]:
            car_data["electric_type"] = "Elbil"
        elif "mildhybrid" in line_lower and not car_data["electric_type"]:
            car_data["electric_type"] = "Mildhybrid"

        # Color
        if line_lower == "färg" and not car_data["color"]:
            if i + 1 < len(lines):
                car_data["color"] = lines[i+1].strip()

        # Transmission
        if (line_lower == "växellåda" or line_lower == "transmission") and not car_data["transmission"]:
            if i + 1 < len(lines):
                car_data["transmission"] = lines[i+1].strip()
        elif not car_data["transmission"]:
            if line_lower in ["automat", "automatväxellåda"]:
                car_data["transmission"] = "Automat"
            elif line_lower in ["manuell", "manuellväxellåda"]:
                car_data["transmission"] = "Manuell"

        # Drive wheels
        if line_lower == "drivhjul" and not car_data["drive_wheels"]:
            if i + 1 < len(lines):
                car_data["drive_wheels"] = lines[i+1].strip()
        elif "fyrhjulsdrift" in line_lower or "awd" in line_lower:
            car_data["drive_wheels"] = "Fyrhjulsdrift"
        elif "framhjulsdrift" in line_lower or "fwd" in line_lower:
            car_data["drive_wheels"] = "Framhjulsdrift"

        # Engine power
        if (line_lower in ["motoreffekt", "effekt", "hästkrafter"]) and not car_data["engine_power"]:
            if i + 1 < len(lines):
                car_data["engine_power"] = lines[i+1].strip()
        elif not car_data["engine_power"]:
            hp_match = re.match(r'^(\d{2,3})\s*(hk|hp|hästkrafter)$', line.strip(), re.IGNORECASE)
            if hp_match:
                car_data["engine_power"] = line.strip()

        # Registration number (Swedish format: ABC123 or ABC12D) from label
        if "reg" in line_lower and ("nummer" in line_lower or "nr" in line_lower):
            if i + 1 < len(lines):
                next_line = lines[i+1].strip().upper().replace(" ", "")
                if re.match(r'^[A-Z]{3}\d{2,3}[A-Z0-9]?$', next_line) and next_line != "ABC123":
                    if not car_data["registration"]:
                        car_data["registration"] = next_line

        # Body type - Kaross
        if line_lower == "kaross" and not car_data["body_type"]:
            if i + 1 < len(lines):
                car_data["body_type"] = lines[i+1].strip()

    return car_data


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
    text_upper = text.upper().strip()
    return text_upper in SWEDISH_CITIES


def parse_city_from_text(text):
    """Extract city from dealer name or address with comprehensive strategies.

    Handles patterns like:
    - 'DEALER - CITY'
    - 'Upplands Väsby' (multi-word cities)
    - Single city names
    """
    if not text:
        return None

    text_upper = text.upper()

    # Get multi-word cities
    MULTI_WORD_CITIES = ['UPPLANDS VÄSBY', 'UPPLANDS BRO', 'HAMMARBY SJÖSTAD']

    # Strategy 1: Check multi-word cities first (sorted by length, longest first)
    for city in sorted(MULTI_WORD_CITIES, key=lambda x: -len(x)):
        if city in text_upper:
            return city

    # Strategy 2: Handle " - " separator - try SECOND part first (the city)
    if ' - ' in text:
        parts = [p.strip() for p in text.split(' - ')]
        if len(parts) >= 2:
            # Try second part first (usually the city in "DEALER - CITY")
            second_part = parts[1].upper()
            if is_valid_swedish_city(second_part):
                return second_part
            # Fallback to first part only if it's a valid city (handles "CITY - STREET")
            first_part = parts[0].upper()
            if is_valid_swedish_city(first_part):
                return first_part
            # If second part is not validated but exists, return it anyway
            if second_part:
                return second_part

    # Strategy 3: Try full text as city name
    text_stripped = text_upper.strip()
    if is_valid_swedish_city(text_stripped):
        return text_stripped

    # Strategy 4: Word-by-word search for any known city
    for word in text.split():
        word_clean = word.strip(',-()').upper()
        if is_valid_swedish_city(word_clean):
            return word_clean

    return None


def scrape_detail_page(driver, url, debug=False):
    """Scrape all details from a car's detail page."""
    # Extract registration from URL if possible
    # Rejmes URL pattern: /bil/volvo-xc60-...-bez888
    registration_from_url = ""
    url_path = url.rstrip('/').split('/')[-1]  # Get last path segment
    if url_path:
        # Registration is the last part after final hyphen
        parts = url_path.split('-')
        if parts:
            last_part = parts[-1].upper()
            if re.match(r'^[A-Z]{3}\d{2,3}[A-Z0-9]?$', last_part):
                registration_from_url = last_part

    try:
        driver.get(url)
        time.sleep(2)

        page_text = driver.find_element(By.TAG_NAME, "body").text

        # Debug: print first 100 lines to understand structure
        if debug:
            lines = [l.strip() for l in page_text.split("\n") if l.strip()]
            print("DEBUG - First 100 lines of page:")
            for i, line in enumerate(lines[:100]):
                print(f"  {i}: {line}")

        car_data = extract_car_data_from_text(page_text, url)

        # Use registration from URL if not found in page
        if registration_from_url and not car_data["registration"]:
            car_data["registration"] = registration_from_url

        # Try to extract additional data from JavaScript/JSON
        try:
            schema_data = driver.execute_script("""
                var scripts = document.querySelectorAll('script[type="application/ld+json"]');
                for (var script of scripts) {
                    try {
                        var data = JSON.parse(script.textContent);
                        if (data['@type'] === 'Car' || data['@type'] === 'Vehicle' || data['@type'] === 'Product') {
                            return {
                                name: data.name || null,
                                price: data.offers?.price || data.price || null,
                                mileage: data.mileageFromOdometer?.value || null,
                                color: data.color || null,
                                year: data.modelDate || data.vehicleModelDate || null,
                                fuelType: data.fuelType || null,
                                transmission: data.vehicleTransmission || null
                            };
                        }
                    } catch(e) {}
                }
                return null;
            """)
            if schema_data:
                if schema_data.get('price') and not car_data["price"]:
                    car_data["price"] = parse_price(str(schema_data['price']))
                if schema_data.get('mileage') and not car_data["mileage"]:
                    car_data["mileage"] = parse_mileage(str(schema_data['mileage']))
                if schema_data.get('color') and not car_data["color"]:
                    car_data["color"] = schema_data['color']
                if schema_data.get('year') and not car_data["model_year"]:
                    year_match = re.search(r'20[0-2]\d', str(schema_data['year']))
                    if year_match:
                        car_data["model_year"] = int(year_match.group())
                if schema_data.get('fuelType') and not car_data["fuel_type"]:
                    car_data["fuel_type"] = schema_data['fuelType']
                if schema_data.get('transmission') and not car_data["transmission"]:
                    trans = schema_data['transmission'].lower()
                    if 'auto' in trans:
                        car_data["transmission"] = "Automat"
                    elif 'manu' in trans:
                        car_data["transmission"] = "Manuell"
        except Exception as e:
            if debug:
                print(f"  Could not extract schema data: {e}")

        # Enhanced location extraction - multi-strategy approach
        if not car_data["location"]:
            try:
                # Strategy 1: Extract from .seller div (visible DOM)
                location_from_dom = driver.execute_script("""
                    var seller = document.querySelector('.seller p');
                    if (seller) return seller.textContent.trim();
                    return null;
                """)
                if location_from_dom:
                    city = parse_city_from_text(location_from_dom)
                    if city:
                        car_data["location"] = city
                        if debug:
                            print(f"  Location from DOM: {city}")

                # Strategy 2: Extract from JSON-LD schema (seller.name)
                if not car_data["location"]:
                    seller_location = driver.execute_script("""
                        var scripts = document.querySelectorAll('script[type="application/ld+json"]');
                        for (var script of scripts) {
                            try {
                                var data = JSON.parse(script.textContent);
                                if (data.seller && data.seller.name) {
                                    return data.seller.name;
                                }
                            } catch(e) {}
                        }
                        return null;
                    """)
                    if seller_location:
                        city = parse_city_from_text(seller_location)
                        if city:
                            car_data["location"] = city
                            if debug:
                                print(f"  Location from JSON-LD: {city}")
            except Exception as e:
                if debug:
                    print(f"  Could not extract location: {e}")

    except Exception as e:
        print(f"  Error scraping {url}: {e}")
        car_data = extract_car_data_from_text("", url)

    return car_data


def scrape_all_listings(driver):
    """Scrape all car listings."""
    all_cars = []

    print(f"Loading: {BASE_URL}")
    driver.get(BASE_URL)
    time.sleep(3)

    accept_cookies(driver)
    time.sleep(2)

    # Wait for initial listings to appear
    wait_for_listings(driver)

    # Load all cars by clicking "Visa fler bilar"
    print("\nLoading all cars by clicking 'Visa fler bilar'...")
    load_all_cars(driver)

    # Save listing page HTML for debugging
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, "debug_rejmes_listing.html"), "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("Saved listing page HTML for debugging")

    # Get all detail URLs
    print("\nCollecting detail URLs...")
    detail_urls = get_car_detail_urls(driver)

    # If no detail URLs found, try alternative approach - scrape from listing page directly
    if not detail_urls:
        print("No detail URLs found, trying to extract data from listing page...")

        # Get all text and try to find car cards
        page_source = driver.page_source
        page_text = driver.find_element(By.TAG_NAME, "body").text

        # Save for debugging
        with open(os.path.join(OUTPUT_DIR, "debug_rejmes_text.txt"), "w", encoding="utf-8") as f:
            f.write(page_text)
        print("Saved page text for debugging")

        # Try to find any links to car pages
        all_links = driver.find_elements(By.TAG_NAME, "a")
        print(f"\nAll links on page ({len(all_links)}):")
        car_links = []
        for link in all_links:
            try:
                href = link.get_attribute("href")
                if href and "volvo" in href.lower() and "xc60" in href.lower():
                    print(f"  {href}")
                    car_links.append(href)
            except:
                continue

        detail_urls = list(set(car_links))
        print(f"\nFiltered to {len(detail_urls)} potential car URLs")

    if not detail_urls:
        print("Could not find car detail URLs!")
        return []

    # Visit each detail page
    print(f"\nScraping {len(detail_urls)} car detail pages...")
    for i, url in enumerate(detail_urls):
        url_short = url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]
        print(f"  [{i+1}/{len(detail_urls)}] {url_short}...")

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
        "transmission", "engine_power", "body_type",
        "location", "url", "scrape_date"
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cars)

    print(f"\nSaved {len(cars)} cars to: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Scrape Rejmes Volvo XC60 listings")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--visible", action="store_true", default=True, help="Run with visible browser (default)")
    args = parser.parse_args()

    print("=" * 60)
    print("Rejmes Volvo XC60 Scraper")
    print("=" * 60)

    # Use visible by default, --headless overrides
    headless = args.headless
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

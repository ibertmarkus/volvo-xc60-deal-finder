"""
Quick validation test for location extraction across all three scrapers.
Tests 5 cars from each site to verify location extraction is working.
"""
import sys
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver():
    """Setup Chrome driver."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(3)
    return driver

def test_rejmes():
    """Test Rejmes location extraction on 5 cars."""
    print("\n" + "="*80)
    print("TESTING REJMES LOCATION EXTRACTION")
    print("="*80)

    # Import the scraper functions
    sys.path.insert(0, '.')
    import scraper_rejmes

    driver = setup_driver()
    try:
        print("Reading URLs from existing CSV...")
        import pandas as pd

        # Read URLs from existing CSV file
        try:
            df = pd.read_csv("data/rejmes_xc60_listings.csv")
            urls = df['url'].head(5).tolist()
            print(f"Found {len(urls)} URLs to test from CSV")
        except:
            print("No existing CSV found, trying to scrape URLs...")
            driver.get("https://rejmes.se/bilar/begagnade-bilar/begagnade-volvo/begagnade-volvo-xc60/?brandName=Volvo&modelName=XC60&statusName=Begagnade")
            time.sleep(3)
            urls = scraper_rejmes.get_car_detail_urls(driver)
            urls = urls[:5]  # Take only first 5
            print(f"Found {len(urls)} URLs to test")

        results = []
        for i, url in enumerate(urls[:5], 1):
            print(f"\nTesting car {i}/5: {url}")
            car_data = scraper_rejmes.scrape_detail_page(driver, url, debug=True)
            location = car_data.get("location", "")
            registration = car_data.get("registration", "")
            print(f"  Registration: {registration}")
            print(f"  Location: {location if location else '[X] NO LOCATION'}")
            results.append({
                "url": url,
                "registration": registration,
                "location": location
            })

        # Summary
        with_location = sum(1 for r in results if r["location"])
        success_rate = (with_location / len(results)) * 100 if results else 0

        print(f"\n{'='*80}")
        print(f"REJMES RESULTS: {with_location}/{len(results)} ({success_rate:.1f}%)")
        print(f"{'='*80}")

        for r in results:
            status = "[OK]" if r["location"] else "[X]"
            print(f"{status} {r['registration']}: {r['location']}")

        return success_rate >= 80

    finally:
        driver.quit()

def test_bilia():
    """Test Bilia location extraction on 5 cars."""
    print("\n" + "="*80)
    print("TESTING BILIA LOCATION EXTRACTION")
    print("="*80)

    # Import the scraper functions
    sys.path.insert(0, '.')
    import scraper_bilia

    driver = setup_driver()
    try:
        print("Collecting detail URLs...")
        driver.get("https://www.bilia.se/bilar/sok-bil/?brand=volvo&model=xc60")
        time.sleep(3)

        # Accept cookies
        try:
            scraper_bilia.accept_cookies(driver)
        except:
            pass

        # Get first 5 car URLs
        urls = scraper_bilia.get_car_detail_urls(driver, verbose=False)
        print(f"Found {len(urls)} URLs to test")

        results = []
        for i, url in enumerate(urls[:5], 1):
            print(f"\nTesting car {i}/5: {url}")
            car_data = scraper_bilia.scrape_detail_page(driver, url, debug=True)
            location = car_data.get("location", "")
            registration = car_data.get("registration", "")
            print(f"  Registration: {registration}")
            print(f"  Location: {location if location else '[X] NO LOCATION'}")
            results.append({
                "url": url,
                "registration": registration,
                "location": location
            })

        # Summary
        with_location = sum(1 for r in results if r["location"])
        success_rate = (with_location / len(results)) * 100 if results else 0

        print(f"\n{'='*80}")
        print(f"BILIA RESULTS: {with_location}/{len(results)} ({success_rate:.1f}%)")
        print(f"{'='*80}")

        for r in results:
            status = "[OK]" if r["location"] else "[X]"
            print(f"{status} {r['registration']}: {r['location']}")

        return success_rate >= 80

    finally:
        driver.quit()

def test_volvo_selekt():
    """Test Volvo Selekt location extraction on 5 cars."""
    print("\n" + "="*80)
    print("TESTING VOLVO SELEKT LOCATION EXTRACTION")
    print("="*80)

    # Import the scraper functions
    sys.path.insert(0, '.')
    import scraper

    driver = setup_driver()
    try:
        print("Collecting detail URLs...")

        # Collect URLs from first page
        urls = []
        driver.get("https://selekt.volvocars.se/sv-se/store/all/vehicles?models=XC60")
        time.sleep(5)

        # Accept cookies
        try:
            scraper.accept_cookies(driver)
            time.sleep(1)
        except:
            pass

        # Get URLs from page
        page_urls = scraper.get_urls_from_page(driver)
        urls.extend(list(page_urls)[:5])

        print(f"Found {len(urls)} URLs to test")

        results = []
        for i, url in enumerate(urls[:5], 1):
            print(f"\nTesting car {i}/5: {url}")
            car_data = scraper.scrape_detail_page_full(driver, url)
            location = car_data.get("location", "")
            registration = car_data.get("registration_number", "")
            print(f"  Registration: {registration}")
            print(f"  Location: {location if location else '[X] NO LOCATION'}")
            results.append({
                "url": url,
                "registration": registration,
                "location": location
            })

        # Summary
        with_location = sum(1 for r in results if r["location"])
        success_rate = (with_location / len(results)) * 100 if results else 0

        print(f"\n{'='*80}")
        print(f"VOLVO SELEKT RESULTS: {with_location}/{len(results)} ({success_rate:.1f}%)")
        print(f"{'='*80}")

        for r in results:
            status = "[OK]" if r["location"] else "[X]"
            print(f"{status} {r['registration']}: {r['location']}")

        return success_rate >= 80

    finally:
        driver.quit()

def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("LOCATION EXTRACTION VALIDATION TEST")
    print("Testing 5 cars from each site (Rejmes, Bilia, Volvo Selekt)")
    print("="*80)

    results = {}

    try:
        results["rejmes"] = test_rejmes()
    except Exception as e:
        print(f"\n[X] REJMES TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["rejmes"] = False

    try:
        results["bilia"] = test_bilia()
    except Exception as e:
        print(f"\n[X] BILIA TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["bilia"] = False

    try:
        results["volvo"] = test_volvo_selekt()
    except Exception as e:
        print(f"\n[X] VOLVO SELEKT TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        results["volvo"] = False

    # Final summary
    print("\n\n" + "="*80)
    print("FINAL TEST SUMMARY")
    print("="*80)
    print(f"Rejmes:       {'[OK] PASS (>=80%)' if results.get('rejmes') else '[X] FAIL (<80%)'}")
    print(f"Bilia:        {'[OK] PASS (>=80%)' if results.get('bilia') else '[X] FAIL (<80%)'}")
    print(f"Volvo Selekt: {'[OK] PASS (>=80%)' if results.get('volvo') else '[X] FAIL (<80%)'}")
    print("="*80)

    if all(results.values()):
        print("\n[SUCCESS] ALL TESTS PASSED! Location extraction is working across all scrapers.")
    else:
        print("\n[WARNING] Some tests failed. Review the output above for details.")

if __name__ == "__main__":
    main()

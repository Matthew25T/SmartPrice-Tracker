"""
Multi-site Product Price Scraper
=================================
Searches 7 e-commerce sites for an electronics product and visualizes results.
ENHANCED: currency normalization (EGP), alerts, network graph, 3D plot, dashboard, price history.
ADDED: User registration/login with Telegram/Email alerts on login.
"""

import logging
import time
import sys
import undetected_chromedriver as uc

from scrapers.jumia_scraper import JumiaScraper
from scrapers.noon_scraper import NoonScraper
from scrapers.amazon_scraper import AmazonScraper
from scrapers.ebay_scraper import EbayScraper
from scrapers.newegg_scraper import NeweggScraper
from scrapers.bestbuy_scraper import BestBuyScraper
from scrapers.walmart_scraper import WalmartScraper

# New modules
from currency import to_egp
from alerts import send_telegram, send_email  # we'll use raw send functions
from price_history import get_previous_price, update_price
from network_viz import draw_price_network
from viz3d import draw_3d_scatter
from cli_dashboard import show_dashboard
from user_manager import register, login  # NEW

# Original visualizer
from visualizer import create_visualizations
import PythonProject14.scrapers.bestbuy_scraper as best_buy

# ─── Logging Setup ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scraper.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ─── Scraper Registry ─────────────────────────────────────────────────────────
SCRAPERS = [
    (JumiaScraper, 3),
    (NoonScraper, 5),
    (AmazonScraper, 4),
    (EbayScraper, 4),
    (NeweggScraper, 3),
    (BestBuyScraper, 4),
    (WalmartScraper, 4),
]


# ─── Driver Factory ───────────────────────────────────────────────────────────
def build_driver() -> uc.Chrome:
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    driver = uc.Chrome(options=options, version_main=147)
    driver.set_page_load_timeout(30)
    return driver


# ─── Safe scraper wrapper ─────────────────────────────────────────────────────
def safe_scrape(scraper_class, driver, product_name, delay):
    try:
        scraper = scraper_class(driver)
        results = scraper.scrape(product_name)
        if results:
            logger.info(f"[{scraper_class.SITE}] Found {len(results)} result(s)")
            return results
        else:
            logger.warning(f"[{scraper_class.SITE}] No results")
            return []
    except Exception as e:
        logger.error(f"[{scraper_class.SITE}] Scraping error: {e}", exc_info=True)
        return []
    finally:
        time.sleep(delay)


# ─── User authentication flow (NEW) ───────────────────────────────────────────
def authenticate_user():
    """Ask user to register or login. Returns username if successful, else None."""
    print("\n" + "=" * 50)
    print("  🔐 USER AUTHENTICATION")
    print("=" * 50)
    print("1. Login")
    print("2. Register")
    choice = input("Choose (1 or 2): ").strip()

    if choice == "1":
        username = input("Username: ").strip()
        password = input("Password: ").strip()
        if login(username, password):
            # Send alert to admin (Telegram + Email)
            msg = f"✅ User *{username}* logged in successfully at {time.strftime('%Y-%m-%d %H:%M:%S')}"
            send_telegram(msg)
            send_email("User Login Alert", f"User '{username}' logged in to the price scraper.")
            return username
        else:
            print("❌ Invalid credentials. Exiting.")
            return None
    elif choice == "2":
        username = input("Choose a username: ").strip()
        password = input("Choose a password: ").strip()
        if register(username, password):
            print(f"✅ User '{username}' registered successfully!")
            # Send alert for new registration
            msg = f"🆕 New user registered: *{username}*"
            send_telegram(msg)
            send_email("New User Registration", f"User '{username}' registered.")
            # Auto-login after registration
            return username
        else:
            print("❌ Username already exists. Try logging in.")
            return None
    else:
        print("Invalid choice. Exiting.")
        return None


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    # ---- User authentication first ----
    username = authenticate_user()
    if not username:
        sys.exit(1)

    search_item = input("Enter the electronic product to search for: ").strip()
    if not search_item:
        print("No product entered. Exiting.")
        sys.exit(1)

    logger.info(f"Starting search for: '{search_item}' (user: {username})")
    print("\n" + "=" * 60)
    print(f"  Product: {search_item}")
    print("=" * 60 + "\n")

    driver = build_driver()
    all_results = []

    try:
        for ScraperClass, delay in SCRAPERS:
            results = safe_scrape(ScraperClass, driver, search_item, delay)
            all_results.extend(results)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        try:
            driver.quit()
            time.sleep(0.5)
        except Exception:
            pass
        logger.info("Browser closed.")

    if not all_results:
        print("  No data was scraped. Check debug screenshots for blocked sites.")
        logger.error("All scrapers failed — no results to visualize.")
        return

    # Normalize prices to EGP
    for r in all_results:
        r["Price_EGP"] = to_egp(r["Price"], r["Currency"])
        r["Currency"] = "EGP"
        r["Price"] = r["Price_EGP"]

    # Price drop alerts (existing)
    try:
        min_price_current = min([x["Price_EGP"] for x in all_results])
        for r in all_results:
            prev_price = get_previous_price(r["Site"], r["Product"])
            is_new_lowest = (r["Price_EGP"] == min_price_current)
            # Import send_alert from alerts.py (we'll reuse)
            from alerts import send_alert
            send_alert(search_item, r["Site"], r["Price_EGP"], prev_price, is_new_lowest)
            update_price(r["Site"], r["Product"], r["Price_EGP"])
    except Exception as e:
        logger.warning(f"Alert/price history failed: {e}")

    # Visualizations
    create_visualizations(all_results, search_item)
    try:
        import pandas as pd
        best_buy._draw_heatmap(pd.DataFrame(all_results), search_item)
    except Exception as e:
        logger.error(f"Heatmap failed: {e}")
    try:
        draw_price_network(all_results, search_item)
    except Exception as e:
        logger.error(f"Network graph failed: {e}")
    try:
        draw_3d_scatter(all_results, search_item)
    except Exception as e:
        logger.error(f"3D plot failed: {e}")
    try:
        show_dashboard(all_results, search_item)
    except Exception as e:
        logger.error(f"Dashboard failed: {e}")

    print("\n✅ All tasks completed!")


if __name__ == "__main__":
    main()
"""
noon_scraper.py — Noon Egypt (API + Selenium)
"""

import re
import time
import requests
import urllib.parse
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from scrapers.scraper_utils import _is_relevant, is_price_sane, is_junk_listing

MAX_CANDIDATES = 5
_API_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "x-cms": "v2",
    "x-locale": "en-eg",
    "Accept": "application/json",
    "Origin": "https://www.noon.com",
    "x-country-code": "EG",
}
_API_URLS = [
    "https://www.noon.com/_svc/catalog/api/search?q={q}&limit=20",
    "https://api.noon.com/catalog/v1/search?q={q}&limit=20&country=EG&lang=en",
]

class NoonScraper:
    SITE = "Noon"

    def __init__(self, driver):
        self.driver = driver

    def _api_scrape(self, product_name: str) -> list[dict]:
        encoded = urllib.parse.quote(product_name)
        for url_tpl in _API_URLS:
            try:
                resp = requests.get(url_tpl.format(q=encoded), headers=_API_HEADERS, timeout=12)
                resp.raise_for_status()
                data = resp.json()
            except Exception:
                continue
            hits = data.get("hits") or data.get("results") or data.get("products") or []
            candidates = []
            for item in hits:
                if len(candidates) >= MAX_CANDIDATES:
                    break
                title = (item.get("name") or item.get("title") or "").strip()
                if not title:
                    continue
                price_val = item.get("sale_price") or item.get("price") or 0
                try:
                    price = float(price_val)
                except:
                    continue
                if is_junk_listing(title) or not any(token in title.lower() for token in product_name.lower().split()):
                    continue
                if not is_price_sane(price, "EGP", product_name):
                    continue
                rating_obj = item.get("product_rating") or item.get("rating") or {}
                rating = float(rating_obj.get("average", 0)) if rating_obj.get("average") else 0.0
                reviews = int(rating_obj.get("count", 0)) if rating_obj.get("count") else 0
                url_suffix = item.get("url", "")
                link = f"https://www.noon.com/egypt-en/{url_suffix}" if url_suffix else ""
                candidates.append({
                    "Product_URL": link,
                    "Site": self.SITE,
                    "Product": title[:80],
                    "Price": price,
                    "Currency": "EGP",
                    "Rating": rating,
                    "Reviews": reviews,
                })
            if candidates:
                return candidates
        return []

    def _selenium_scrape(self, product_name: str) -> list[dict]:
        query = urllib.parse.quote_plus(product_name)
        self.driver.get(f"https://www.noon.com/egypt-en/search/?q={query}")
        self.driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(3)
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-qa='product-block'], div.productContainer"))
            )
        except:
            pass
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        items = soup.select("div[data-qa='product-block']") or soup.select("div.productContainer") or soup.find_all("div", class_=re.compile(r"\bproduct\b", re.I))
        candidates = []
        for item in items[:MAX_CANDIDATES]:
            title_elem = item.find("div", class_=re.compile(r"name|title", re.I)) or item.find(["h2", "h3"])
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            # الرابط
            a_tag = item.find("a")
            link = ""
            if a_tag and a_tag.get("href"):
                href = a_tag["href"]
                link = href if href.startswith("http") else "https://www.noon.com" + href
            # السعر
            price_text = ""
            price_elem = item.find(class_=re.compile(r"price|amount", re.I))
            if price_elem:
                price_text = price_elem.get_text()
            if not price_text:
                continue
            m_price = re.search(r"[\d,]+", price_text)
            if not m_price:
                continue
            price = float(m_price.group().replace(",", ""))
            if is_junk_listing(title):
                continue
            if not any(token in title.lower() for token in product_name.lower().split()):
                continue
            if not is_price_sane(price, "EGP", product_name):
                continue
            # التقييمات
            rating, reviews = 0.0, 0
            rating_elem = item.find(attrs={"aria-label": re.compile(r"[\d.]+\s*out of", re.I)})
            if rating_elem:
                m_r = re.search(r"([\d.]+)\s*out of", rating_elem["aria-label"])
                if m_r:
                    rating = float(m_r.group(1))
            rev_elem = item.find(string=re.compile(r"\(\d+\)"))
            if rev_elem:
                m_rev = re.search(r"\((\d+)\)", rev_elem)
                if m_rev:
                    reviews = int(m_rev.group(1))
            candidates.append({
                "Product_URL": link,
                "Site": self.SITE,
                "Product": title[:80],
                "Price": price,
                "Currency": "EGP",
                "Rating": rating,
                "Reviews": reviews,
            })
        return candidates

    def scrape(self, product_name: str) -> list[dict]:
        candidates = self._api_scrape(product_name)
        if not candidates:
            candidates = self._selenium_scrape(product_name)
        if not candidates:
            return []
        best = min(candidates, key=lambda x: x["Price"])
        return [best]
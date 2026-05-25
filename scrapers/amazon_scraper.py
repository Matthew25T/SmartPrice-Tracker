"""
amazon_scraper.py — Amazon via SerpAPI (no Selenium needed)
"""

import os
import re
import requests
from dotenv import load_dotenv, find_dotenv
from scrapers.scraper_utils import is_junk_listing

load_dotenv(find_dotenv())

MAX_CANDIDATES = 5
_SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")


class AmazonScraper:
    SITE = "Amazon"

    def __init__(self, driver=None):
        self.api_key = _SERPAPI_KEY

    def scrape(self, product_name: str) -> list[dict]:
        params = {
            "engine":        "amazon",
            "k":             product_name,
            "amazon_domain": "amazon.eg",
            "api_key":       self.api_key,
            "condition":     "new",
        }
        try:
            resp = requests.get("https://serpapi.com/search", params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[Amazon] SerpAPI error: {e}")
            return []

        candidates = []
        for item in data.get("organic_results", []):
            if len(candidates) >= MAX_CANDIDATES:
                break
            title = item.get("title", "").strip()
            if not title or item.get("is_sponsored"):
                continue
            if is_junk_listing(title):
                continue

            price = self._extract_price(item)
            if not price or price < 1000 or price > 200000:
                continue

            candidates.append({
                "Product_URL": item.get("link", ""),
                "Site":     self.SITE,
                "Product":  title[:80],
                "Price":    price,
                "Currency": "EGP",
                "Rating":   self._extract_rating(item),
                "Reviews":  self._extract_reviews(item),
            })

        if not candidates:
            return []

        return [min(candidates, key=lambda x: x["Price"])]

    @staticmethod
    def _extract_price(item):
        for key in ("price", "extracted_price"):
            val = item.get(key)
            if isinstance(val, dict):
                extracted = val.get("extracted") or val.get("value")
                if extracted:
                    try:
                        return float(extracted)
                    except Exception:
                        pass
            if val and not isinstance(val, dict):
                clean = re.sub(r"[^\d.]", "", str(val))
                try:
                    return float(clean)
                except Exception:
                    pass
        return 0.0

    @staticmethod
    def _extract_rating(item):
        for key in ("rating", "stars"):
            val = item.get(key)
            if val:
                try:
                    r = float(val)
                    if 0 < r <= 5:
                        return r
                except Exception:
                    pass
        return 0.0

    @staticmethod
    def _extract_reviews(item):
        for key in ("reviews", "ratings"):
            val = item.get(key)
            if isinstance(val, dict):
                count = val.get("total") or val.get("amount")
                if count:
                    try:
                        return int(str(count).replace(",", ""))
                    except Exception:
                        pass
            if val and not isinstance(val, dict):
                try:
                    return int(str(val).replace(",", ""))
                except Exception:
                    pass
        return 0
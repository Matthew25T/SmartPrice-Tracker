"""
ebay_scraper.py — eBay via SerpAPI
"""

import os
import re
import requests
from dotenv import load_dotenv
from scrapers.scraper_utils import _is_relevant, is_price_sane, is_junk_listing

load_dotenv()

MAX_CANDIDATES = 5
_SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")


class EbayScraper:
    SITE = "eBay"

    def __init__(self, driver=None):
        self.api_key = _SERPAPI_KEY

    @staticmethod
    def _parse_price(item: dict) -> float:
        raw = item.get("price")
        if isinstance(raw, dict):
            val = raw.get("extracted") or raw.get("value") or raw.get("raw")
            if val:
                try:
                    return float(re.sub(r"[^\d.]", "", str(val)))
                except ValueError:
                    pass
        if raw:
            try:
                return float(re.sub(r"[^\d.]", "", str(raw)))
            except ValueError:
                pass
        for key in ("extracted_price", "current_price"):
            val = item.get(key)
            if val:
                try:
                    return float(re.sub(r"[^\d.]", "", str(val)))
                except ValueError:
                    pass
        return 0.0

    @staticmethod
    def _parse_rating(item: dict) -> float:
        rev_data = item.get("reviews") or {}
        if isinstance(rev_data, dict):
            r = float(rev_data.get("rating") or 0)
        else:
            r = float(item.get("rating") or 0)
        return r if 0 < r <= 5 else 0.0

    @staticmethod
    def _parse_reviews(item: dict) -> int:
        rev_data = item.get("reviews") or {}
        if isinstance(rev_data, dict):
            count = rev_data.get("amount") or rev_data.get("count") or rev_data.get("total") or 0
        else:
            count = item.get("reviews") or 0
        try:
            return int(str(count).replace(",", ""))
        except (TypeError, ValueError):
            return 0

    def scrape(self, product_name: str) -> list[dict]:
        params = {
            "engine":           "ebay",
            "_nkw":             product_name,
            "api_key":          self.api_key,
            "LH_ItemCondition": "1000",
            "LH_BIN":           "1",
            "LH_PrefLoc":       "1",
            "LH_TitleDesc":     "0",
        }

        candidates: list[dict] = []
        try:
            resp = requests.get("https://serpapi.com/search", params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("organic_results", []):
                if len(candidates) >= MAX_CANDIDATES:
                    break
                title = (item.get("title") or "").strip()
                if not title:
                    continue
                if is_junk_listing(title):
                    continue
                if not _is_relevant(title, product_name):
                    continue
                price = self._parse_price(item)
                if not price or not is_price_sane(price, "USD", product_name):
                    continue
                candidates.append({
                    "Product_URL": item.get("link", ""),
                    "Site":     self.SITE,
                    "Product":  title[:80],
                    "Price":    price,
                    "Currency": "USD",
                    "Rating":   self._parse_rating(item),
                    "Reviews":  self._parse_reviews(item),
                })
        except Exception:
            pass

        if not candidates:
            return []

        return [max(candidates, key=lambda x: (x["Reviews"], x["Rating"]))]
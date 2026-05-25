"""
walmart_scraper.py — Walmart via SerpAPI
"""

import os
import re
import requests
from dotenv import load_dotenv, find_dotenv
from scrapers.scraper_utils import _is_relevant, is_price_sane, is_junk_listing

load_dotenv(find_dotenv())

MAX_CANDIDATES = 5
_SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")


class WalmartScraper:
    SITE = "Walmart"

    def __init__(self, driver=None):
        self.api_key = _SERPAPI_KEY

    @staticmethod
    def _extract_price(item: dict) -> float:
        try:
            val = item.get("primary_offer", {}).get("offer_price")
            if val:
                return float(val)
        except (TypeError, ValueError):
            pass
        for key in ("price", "sale_price", "regular_price"):
            val = item.get(key)
            if val:
                try:
                    return float(re.sub(r"[^\d.]", "", str(val)))
                except ValueError:
                    pass
        return 0.0

    @staticmethod
    def _is_new(item: dict) -> bool:
        condition = (item.get("item_condition") or "").strip().lower()
        return condition in ("new", "")

    def scrape(self, product_name: str) -> list[dict]:
        params = {
            "engine":  "walmart",
            "query":   product_name,
            "api_key": self.api_key,
            "sort":    "best_seller",
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
                if not self._is_new(item):
                    continue
                if is_junk_listing(title):
                    continue
                if not _is_relevant(title, product_name):
                    continue
                price = self._extract_price(item)
                if not price or not is_price_sane(price, "USD", product_name):
                    continue
                try:
                    rating = float(item.get("rating") or 0)
                    rating = rating if 0 < rating <= 5 else 0.0
                except (TypeError, ValueError):
                    rating = 0.0
                try:
                    reviews = int(str(item.get("reviews") or 0).replace(",", ""))
                except (TypeError, ValueError):
                    reviews = 0
                product_url = item.get("product_page_url") or item.get("link") or ""
                if product_url.startswith("/"):
                    product_url = "https://www.walmart.com" + product_url
                candidates.append({
                    "Product_URL": product_url,
                    "Site":     self.SITE,
                    "Product":  title[:80],
                    "Price":    price,
                    "Currency": "USD",
                    "Rating":   rating,
                    "Reviews":  reviews,
                })
        except Exception:
            pass

        if not candidates:
            return []

        return [max(candidates, key=lambda x: (x["Reviews"], x["Rating"]))]
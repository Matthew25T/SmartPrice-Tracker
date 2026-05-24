"""
jumia_scraper.py — Jumia Egypt
================================
Tool Choice: Requests + BeautifulSoup (primary) → Selenium fallback
Rationale: Jumia's search results page is largely server-rendered HTML,
meaning a plain HTTP GET with proper browser headers returns the full
product grid without JavaScript execution. Requests is ~5× faster than
Selenium for this.  Selenium is only used if Requests returns a redirect /
CAPTCHA / empty product list.

Pipeline
--------
1. [Tier 1] requests.Session GET → BS4 parse <article.prd>
2. [Tier 2] If tier 1 yields nothing → Selenium page load → BS4 parse
3. Both tiers apply the triple gate; collect ≤ MAX_CANDIDATES=5.
4. Return highest-review (then highest-rating) candidate.
"""

import re
import time
import requests
import urllib.parse
from bs4 import BeautifulSoup

from scrapers.scraper_utils import _is_relevant, is_price_sane, is_junk_listing

MAX_CANDIDATES = 5

_SESSION_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer":         "https://www.jumia.com.eg/",
}


class JumiaScraper:
    SITE = "Jumia"

    def __init__(self, driver):
        self.driver = driver
        self._session = requests.Session()
        self._session.headers.update(_SESSION_HEADERS)

    # ------------------------------------------------------------------ #
    # Shared parser — works on any BeautifulSoup object
    # ------------------------------------------------------------------ #

    def _parse_soup(self, soup: BeautifulSoup, product_name: str) -> list[dict]:
        candidates: list[dict] = []
        products = soup.select("article.prd")

        for prod in products:
            if len(candidates) >= MAX_CANDIDATES:
                break

            title_elem = prod.select_one(".name")
            price_elem = prod.select_one(".prc")
            if not (title_elem and price_elem):
                continue

            title = title_elem.get_text(strip=True)
            raw_price = (
                price_elem.get_text()
                .replace("EGP", "")
                .replace(",", "")
                .strip()
            )
            try:
                price = float(re.search(r"[\d.]+", raw_price).group())
            except (AttributeError, ValueError):
                continue

            # ── Triple gate ──────────────────────────────────────────────
            if is_junk_listing(title):
                continue
            if not _is_relevant(title, product_name):
                continue
            if not is_price_sane(price, "EGP", product_name):
                continue

            # Rating + reviews
            rating, reviews = 0.0, 0
            rev_elem = prod.select_one(".stars._s, .rev, [data-catalog='rating']")
            if rev_elem:
                text = rev_elem.get_text(" ", strip=True)
                m_rat = re.search(r"([\d.]+)\s*out of", text, re.I)
                if m_rat:
                    r = float(m_rat.group(1))
                    rating = r if 0 < r <= 5 else 0.0
                m_rev = re.search(r"\((\d+)\)", text)
                if m_rev:
                    reviews = int(m_rev.group(1))

            # Jumia also stores star count as a CSS class e.g. "stars-4"
            if not rating:
                star_elem = prod.find(class_=re.compile(r"\bstars-(\d)\b"))
                if star_elem:
                    m = re.search(r"stars-(\d)", " ".join(star_elem.get("class", [])))
                    if m:
                        r = float(m.group(1))
                        rating = r if 0 < r <= 5 else 0.0
            a_tag = prod.select_one("a.core")
            link = "https://www.jumia.com.eg" + a_tag["href"] if a_tag and "href" in a_tag.attrs else ""
            candidates.append({
                "Product_URL": link,
                "Site":     self.SITE,
                "Product":  title[:80],
                "Price":    price,
                "Currency": "EGP",
                "Rating":   rating,
                "Reviews":  reviews,
            })

        return candidates

    # ------------------------------------------------------------------ #
    # Tier 1 — plain Requests (fast, no browser needed)
    # ------------------------------------------------------------------ #

    def _requests_scrape(self, product_name: str) -> list[dict]:
        query = urllib.parse.quote_plus(product_name)
        url = f"https://www.jumia.com.eg/catalog/?q={query}"
        try:
            resp = self._session.get(url, timeout=12, allow_redirects=True)
            resp.raise_for_status()
            # Jumia sometimes returns a soft CAPTCHA page — detect it
            if "captcha" in resp.url.lower() or "challenge" in resp.text.lower()[:500]:
                return []
            soup = BeautifulSoup(resp.text, "html.parser")
            return self._parse_soup(soup, product_name)
        except Exception:
            return []

    # ------------------------------------------------------------------ #
    # Tier 2 — Selenium fallback
    # ------------------------------------------------------------------ #

    def _selenium_scrape(self, product_name: str) -> list[dict]:
        query = urllib.parse.quote_plus(product_name)
        self.driver.get(f"https://www.jumia.com.eg/catalog/?q={query}")
        time.sleep(4)
        try:
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            return self._parse_soup(soup, product_name)
        except Exception:
            return []

    # ------------------------------------------------------------------ #
    # Public scrape
    # ------------------------------------------------------------------ #

    def scrape(self, product_name: str) -> list[dict]:
        candidates = self._requests_scrape(product_name)
        if not candidates:
            candidates = self._selenium_scrape(product_name)
        if not candidates:
            return []

        best = max(candidates, key=lambda x: (x["Reviews"], x["Rating"]))
        return [best]
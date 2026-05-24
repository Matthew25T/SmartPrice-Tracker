"""
scraper_utils.py
================
Shared validation helpers for all scrapers.
Fixes the core accuracy problem: loose relevance matching returned
garbage prices (e.g. iPhone 15 at $15 because it matched the "15"
in a $15 accessory listing).
"""

import re

# ---------------------------------------------------------------------------
# Relevance scoring
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Lower-case, strip punctuation, split into tokens."""
    return re.sub(r"[^\w\s]", "", text.lower()).split()


def _is_relevant(title: str, query: str, threshold: float = 0.75) -> bool:
    """
    Strict relevance check.

    Rules
    -----
    1. At least `threshold` fraction of query tokens must appear in the title.
    2. Every *numeric* token in the query (model numbers, generations) MUST
       appear in the title — these are the biggest source of wrong results.
       Example: query "iPhone 15" must NOT match "iPhone 6" or
       "15W USB-C charger".
    3. Short queries (≤ 2 tokens) use a tighter 100 % match to avoid
       broad accidental matches.
    """
    q_tokens = _tokenize(query)
    t_tokens = set(_tokenize(title))

    if not q_tokens:
        return False

    # Rule 3 — very short queries need perfect match
    if len(q_tokens) <= 2:
        threshold = 1.0

    # Rule 2 — every numeric/model token in the query must be in the title
    numeric_q = [t for t in q_tokens if re.search(r"\d", t)]
    for num in numeric_q:
        if num not in t_tokens:
            return False

    # Rule 1 — overall overlap fraction
    overlap = sum(1 for t in q_tokens if t in t_tokens)
    return overlap / len(q_tokens) >= threshold


# ---------------------------------------------------------------------------
# Price sanity
# ---------------------------------------------------------------------------

# (min, max) bounds per currency
PRICE_BOUNDS: dict[str, tuple[float, float]] = {
    "EGP": (200.0,   600_000.0),
    "USD": (5.0,     15_000.0),
    "GBP": (5.0,     12_000.0),
    "EUR": (5.0,     13_000.0),
    "SAR": (20.0,    60_000.0),
    "AED": (20.0,    60_000.0),
}

# Electronics-specific lower bound: items under these amounts are almost
# certainly accessories / partial listings, not the device itself.
# Keys are substrings that might appear in the search query (lower-cased).
_CATEGORY_MIN_USD: list[tuple[re.Pattern, float]] = [
    (re.compile(r"laptop|macbook|notebook|chromebook"),       300.0),
    (re.compile(r"iphone|samsung|pixel|galaxy|smartphone"),   150.0),
    (re.compile(r"ipad|tablet"),                              100.0),
    (re.compile(r"tv|television|monitor|display"),             80.0),
    (re.compile(r"gpu|graphics card|rtx|rx\s?\d"),            150.0),
    (re.compile(r"cpu|processor|ryzen|intel core"),            50.0),
    (re.compile(r"playstation|xbox|ps\d|nintendo switch"),    150.0),
    (re.compile(r"airpods|headphone|earphone|earbuds"),        10.0),
    (re.compile(r"watch|smartwatch"),                          20.0),
]

# Rough EGP/USD rate used only for category-floor cross-checks
_USD_TO_EGP = 49.0


def _category_min_usd(query: str) -> float:
    """Return a minimum USD price for the detected product category."""
    q_low = query.lower()
    for pattern, min_usd in _CATEGORY_MIN_USD:
        if pattern.search(q_low):
            return min_usd
    return 5.0  # generic electronics fallback


def is_price_sane(price: float, currency: str, query: str) -> bool:
    """
    Return True only if the price is within sane bounds for the currency
    AND above the category-specific minimum.
    """
    currency = currency.upper()
    lo, hi = PRICE_BOUNDS.get(currency, (1.0, 1_000_000.0))
    if not (lo <= price <= hi):
        return False

    # Category floor — convert to USD for a uniform comparison
    if currency == "EGP":
        price_usd = price / _USD_TO_EGP
    elif currency == "USD":
        price_usd = price
    else:
        return True  # skip category check for exotic currencies

    cat_min = _category_min_usd(query)
    return price_usd >= cat_min


# ---------------------------------------------------------------------------
# Junk-listing filter (shared across eBay / Walmart)
# ---------------------------------------------------------------------------

JUNK_RE = re.compile(
    r"\b(parts?|broken|cracked|repair|for parts|not working|untested|"
    r"as[- ]is|incomplete|faulty|damaged|spares?|"
    r"restored|used|refurbished|open[- ]box|pre[- ]owned|"
    r"renewed|remanufactured|case|cover|screen protector|"
    r"charger only|cable only|adapter only|replacement)\b",
    re.I,
)


def is_junk_listing(title: str) -> bool:
    return bool(JUNK_RE.search(title))
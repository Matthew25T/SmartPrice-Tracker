"""
Currency conversion: USD → EGP using live exchange rate.
Fallback to approximate rate if API fails.
"""
import json
import urllib.request
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

CACHE_FILE = "exchange_rate_cache.json"
DEFAULT_USD_TO_EGP = 49.0  # approximate fallback

def get_usd_to_egp() -> float:
    """Get latest USD to EGP exchange rate (cached for 1 hour)."""
    try:
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
            cached_time = datetime.fromisoformat(cache["timestamp"])
            if datetime.now() - cached_time < timedelta(hours=1):
                return cache["rate"]
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        pass

    try:
        # Free API from exchangerate-api.com (no key required)
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            rate = data["rates"]["EGP"]
            with open(CACHE_FILE, "w") as f:
                json.dump({"timestamp": datetime.now().isoformat(), "rate": rate}, f)
            logger.info(f"Updated USD/EGP rate: {rate}")
            return rate
    except Exception as e:
        logger.warning(f"Failed to fetch live exchange rate: {e}. Using fallback.")
        return DEFAULT_USD_TO_EGP

def to_egp(price: float, currency: str) -> float:
    """Convert price to EGP. If currency is already EGP, return as-is."""
    if currency.upper() == "EGP":
        return price
    elif currency.upper() == "USD":
        return price * get_usd_to_egp()
    else:
        logger.warning(f"Unknown currency {currency}, returning price unchanged")
        return price
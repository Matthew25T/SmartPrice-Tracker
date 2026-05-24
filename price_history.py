"""
Save and compare historical prices to detect drops.
"""
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
HISTORY_FILE = "price_history.json"

def _load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}

def _save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def get_previous_price(site: str, product: str):
    """Return last known price (EGP) for a site-product combo."""
    history = _load_history()
    key = f"{site}|{product}"
    return history.get(key, {}).get("price")

def update_price(site: str, product: str, price_egp: float):
    """Store current price with timestamp."""
    history = _load_history()
    key = f"{site}|{product}"
    history[key] = {
        "price": price_egp,
        "last_seen": datetime.now().isoformat()
    }
    _save_history(history)

def get_all_time_lowest(all_results_egp: list):
    """Return the absolute lowest price and site across all history and current."""
    # Not needed for alerts, but used in CLI dashboard
    if not all_results_egp:
        return None, None
    best = min(all_results_egp, key=lambda x: x["Price_EGP"])
    return best["Price_EGP"], best["Site"]
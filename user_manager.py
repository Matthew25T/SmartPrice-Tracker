"""
User management: register, login, save/load users.
Passwords are hashed using SHA256 (you can upgrade to bcrypt later).
"""
import json
import hashlib
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
USERS_FILE = "users.json"

def _hash_password(password: str) -> str:
    """Return SHA256 hash of password."""
    return hashlib.sha256(password.encode()).hexdigest()

def _load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def _save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def register(username: str, password: str) -> bool:
    """Register a new user. Returns True if success, False if username exists."""
    users = _load_users()
    if username in users:
        logger.warning(f"Registration failed: username '{username}' already exists.")
        return False
    users[username] = {
        "password_hash": _hash_password(password),
        "created_at": datetime.now().isoformat()
    }
    _save_users(users)
    logger.info(f"User '{username}' registered successfully.")
    return True

def login(username: str, password: str) -> bool:
    """Verify credentials. Returns True if correct."""
    users = _load_users()
    if username not in users:
        logger.warning(f"Login failed: username '{username}' not found.")
        return False
    expected_hash = users[username]["password_hash"]
    if _hash_password(password) == expected_hash:
        logger.info(f"User '{username}' logged in successfully.")
        return True
    else:
        logger.warning(f"Login failed: wrong password for '{username}'.")
        return False
"""
telegram_bot.py  —  PriceScout Telegram Bot
============================================
Commands:
  /start          — Welcome message
  /search <item>  — Scrape prices for a product
  /history        — Show your last 5 searches
  /best           — Best deal from last search
  /send_email <email> — Send last results to your email
  /login user pass       — Login to your account
  /register user pass    — Create an account
  /help           — Command reference
"""

import logging
import os
import threading
import time
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
FLASK_BASE_URL     = "http://localhost:5000"

_user_sessions: dict[int, dict] = {}
_offset = 0


def _tg(method: str, **kwargs) -> dict:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    try:
        resp = requests.post(url, json=kwargs, timeout=10)
        return resp.json()
    except Exception as e:
        logger.error(f"Telegram API error ({method}): {e}")
        return {}


def send(chat_id: str | int, text: str, parse_mode: str = "HTML"):
    _tg("sendMessage", chat_id=chat_id, text=text, parse_mode=parse_mode)


def send_typing(chat_id):
    _tg("sendChatAction", chat_id=chat_id, action="typing")


def _api(endpoint: str, payload: dict, token: str) -> dict | None:
    try:
        r = requests.post(
            f"{FLASK_BASE_URL}{endpoint}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        return r.json()
    except Exception as e:
        logger.error(f"Internal API error ({endpoint}): {e}")
        return None


def _api_get(endpoint: str, token: str) -> dict | None:
    try:
        r = requests.get(
            f"{FLASK_BASE_URL}{endpoint}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        return r.json()
    except Exception as e:
        logger.error(f"Internal GET error ({endpoint}): {e}")
        return None


def _login_bot_user(username: str, password: str) -> str | None:
    try:
        r = requests.post(
            f"{FLASK_BASE_URL}/api/login",
            json={"username": username, "password": password},
            timeout=10,
        )
        return r.json().get("token")
    except Exception as e:
        logger.error(f"Bot login failed: {e}")
        return None


def _register_bot_user(username: str, password: str) -> str | None:
    try:
        r = requests.post(
            f"{FLASK_BASE_URL}/api/register",
            json={"username": username, "password": password},
            timeout=10,
        )
        return r.json().get("token")
    except Exception as e:
        logger.error(f"Bot register failed: {e}")
        return None


def handle_start(chat_id: int, session: dict):
    send(chat_id,
         "Welcome to <b>PriceScout Bot</b>!\n\n"
         "Search for the best electronics prices across 5 platforms.\n\n"
         "<b>Commands:</b>\n"
         "  /search &lt;product&gt; — Find best price\n"
         "  /history               — Your last 5 searches\n"
         "  /best                  — Best deal from last search\n"
         "  /send_email &lt;email&gt; — Send last results to your email\n"
         "  /login user pass       — Login to your account\n"
         "  /register user pass    — Create an account\n"
         "  /help                  — Show this menu\n\n"
         "<i>Tip: Login first to save your search history!</i>")


def handle_help(chat_id: int):
    send(chat_id,
         "<b>PriceScout Bot — Help</b>\n\n"
         "<b>/search</b> &lt;product name&gt;\n"
         "  → Searches 5 sites and returns ranked prices\n\n"
         "<b>/best</b>\n"
         "  → Repeats the best deal from your last search\n\n"
         "<b>/history</b>\n"
         "  → Shows your last 5 saved searches\n\n"
         "<b>/send_email</b> &lt;email&gt;\n"
         "  → Sends the results of your last search to the specified email\n\n"
         "<b>/login</b> &lt;username&gt; &lt;password&gt;\n"
         "  → Login to save history & get alerts\n\n"
         "<b>/register</b> &lt;username&gt; &lt;password&gt;\n"
         "  → Create a new account\n\n"
         "<b>/logout</b>\n"
         "  → Clear your session")


def handle_login(chat_id: int, parts: list[str], sessions: dict):
    if len(parts) < 3:
        send(chat_id, "Usage: /login &lt;username&gt; &lt;password&gt;")
        return
    username, password = parts[1], parts[2]
    token = _login_bot_user(username, password)
    if token:
        sessions[chat_id] = {"token": token, "username": username,
                             "last_results": [], "last_query": ""}
        send(chat_id, f"Logged in as <b>{username}</b>!")
    else:
        send(chat_id, "Invalid credentials. Try /register if you're new.")


def handle_register(chat_id: int, parts: list[str], sessions: dict):
    if len(parts) < 3:
        send(chat_id, "Usage: /register &lt;username&gt; &lt;password&gt;")
        return
    username, password = parts[1], parts[2]
    token = _register_bot_user(username, password)
    if token:
        sessions[chat_id] = {"token": token, "username": username,
                             "last_results": [], "last_query": ""}
        send(chat_id, f"Account created & logged in as <b>{username}</b>!")
    else:
        send(chat_id, "Username already taken. Try /login instead.")


def handle_logout(chat_id: int, sessions: dict):
    if chat_id in sessions:
        name = sessions.pop(chat_id).get("username", "")
        send(chat_id, f"Logged out{' ' + name if name else ''}. Use /login to reconnect.")
    else:
        send(chat_id, "You're not logged in.")


def handle_search(chat_id: int, parts: list[str], sessions: dict):
    if len(parts) < 2:
        send(chat_id, "Usage: /search &lt;product name&gt;\nExample: /search iPhone 15 Pro")
        return

    query   = " ".join(parts[1:])
    session = sessions.get(chat_id, {})
    token   = session.get("token")

    if not token:
        guest_user = f"tg_{chat_id}"
        guest_pass = f"tgpass_{chat_id}"
        token = _login_bot_user(guest_user, guest_pass)
        if not token:
            token = _register_bot_user(guest_user, guest_pass)
        if token:
            sessions[chat_id] = {"token": token, "username": guest_user,
                                 "last_results": [], "last_query": ""}
            session = sessions[chat_id]

    if not token:
        send(chat_id, "Could not authenticate. Please use /login or /register.")
        return

    send_typing(chat_id)
    send(chat_id, f"Searching for <b>{query}</b> across 5 platforms...\nThis takes ~10 seconds.")

    data = _api("/api/scrape", {"query": query}, token)
    if not data or "results" not in data:
        send(chat_id, "Scrape failed. The backend may be starting up. Try again in a moment.")
        return

    results = data["results"]
    summary = data.get("summary", {})
    session["last_results"] = results
    session["last_query"]   = query

    _api("/api/history", {"query": query, "results": results, "summary": summary}, token)

    lines = [f"<b>Price Results for: {query}</b>\n"]
    for i, r in enumerate(results):
        medal = ["1.", "2.", "3."][i] if i < 3 else f"  {i+1}."
        lines.append(
            f"{medal} <b>{r['site']}</b>\n"
            f"   {r['price']:,.2f} {r['currency']}  ({r['price_egp']:,.0f} EGP)\n"
            f"   * Rating: {r['rating']} ({r['reviews']:,} reviews)"
        )
    lines.append(
        f"\n<b>Summary</b>\n"
        f"  Best:  {summary.get('best_site')} — {summary.get('best_price', 0):,.0f} EGP\n"
        f"  Avg:   {summary.get('avg_price', 0):,.0f} EGP\n"
        f"  Worst: {summary.get('worst_site')} — {summary.get('worst_price', 0):,.0f} EGP\n\n"
        f"Use /best to recall the top deal, /send_email to get results by email."
    )
    send(chat_id, "\n".join(lines))


def handle_best(chat_id: int, sessions: dict):
    session = sessions.get(chat_id, {})
    results = session.get("last_results", [])
    query   = session.get("last_query", "")
    if not results:
        send(chat_id, "No recent search found. Use /search &lt;product&gt; first.")
        return
    best = results[0]
    send(chat_id,
         f"<b>Best Deal — {query}</b>\n\n"
         f"<b>{best['site']}</b>\n"
         f"  {best['price']:,.2f} {best['currency']}\n"
         f"  = <b>{best['price_egp']:,.0f} EGP</b>\n"
         f"  * Rating: {best['rating']} ({best['reviews']:,} reviews)\n\n"
         f"  {best['product']}")


def handle_history(chat_id: int, sessions: dict):
    session = sessions.get(chat_id, {})
    token   = session.get("token")
    if not token:
        send(chat_id, "Please /login first to view history.")
        return
    data = _api_get("/api/history", token)
    if not data:
        send(chat_id, "No search history yet. Try /search &lt;product&gt;!")
        return
    lines = ["<b>Your Last Searches:</b>\n"]
    for entry in data[:5]:
        ts      = entry.get("timestamp", "")[:16].replace("T", " ")
        summary = entry.get("summary", {})
        lines.append(
            f"<b>{entry['query']}</b>\n"
            f"   {ts}  |  Best: {summary.get('best_site', '—')} "
            f"@ {summary.get('best_price', 0):,.0f} EGP"
        )
    send(chat_id, "\n".join(lines))


def handle_send_email(chat_id: int, parts: list[str], sessions: dict):
    if len(parts) < 2:
        send(chat_id, "Usage: /send_email <your_email@example.com>")
        return
    email   = parts[1].strip()
    session = sessions.get(chat_id)
    if not session or not session.get("last_results"):
        send(chat_id, "No recent search found. Use /search first.")
        return
    token = session.get("token")
    if not token:
        send(chat_id, "You need to be logged in. Use /login or /register.")
        return

    results = session["last_results"]
    query   = session.get("last_query", "")
    if results:
        best  = results[0]
        worst = results[-1]
        avg   = sum(r["price_egp"] for r in results) / len(results)
        summary = {
            "best_price":   best["price_egp"],
            "best_site":    best["site"],
            "worst_price":  worst["price_egp"],
            "worst_site":   worst["site"],
            "avg_price":    round(avg, 2),
            "total_sites":  len(results),
        }
    else:
        summary = {}

    payload = {"email": email, "results": results, "query": query, "summary": summary}
    try:
        r = requests.post(
            f"{FLASK_BASE_URL}/api/send_results",
            json=payload,
            headers={"Authorization": f"Bearer {session['token']}"},
            timeout=20,
        )
        if r.status_code == 200:
            send(chat_id, f"✅ Results sent to {email}!")
        else:
            send(chat_id, f"❌ Failed: {r.json().get('error', 'Unknown error')}")
    except Exception as e:
        send(chat_id, f"❌ Error: {str(e)}")


def process_update(update: dict, sessions: dict):
    msg = update.get("message", {})
    if not msg:
        return
    chat_id = msg["chat"]["id"]
    text    = msg.get("text", "").strip()
    if not text:
        return

    parts = text.split()
    cmd   = parts[0].lower().split("@")[0]

    if   cmd == "/start":      handle_start(chat_id, sessions.get(chat_id, {}))
    elif cmd == "/help":       handle_help(chat_id)
    elif cmd == "/login":      handle_login(chat_id, parts, sessions)
    elif cmd == "/register":   handle_register(chat_id, parts, sessions)
    elif cmd == "/logout":     handle_logout(chat_id, sessions)
    elif cmd == "/search":     handle_search(chat_id, parts, sessions)
    elif cmd == "/best":       handle_best(chat_id, sessions)
    elif cmd == "/history":    handle_history(chat_id, sessions)
    elif cmd == "/send_email": handle_send_email(chat_id, parts, sessions)
    else:
        if not text.startswith("/"):
            handle_search(chat_id, ["/search"] + text.split(), sessions)
        else:
            send(chat_id, "Unknown command. Use /help to see available commands.")


def poll_loop():
    global _offset
    sessions: dict[int, dict] = {}
    logger.info("Telegram bot polling started.")

    while True:
        try:
            resp = requests.get(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates",
                params={"offset": _offset, "timeout": 20},
                timeout=30,
            )
            data = resp.json()
            if not data.get("ok"):
                time.sleep(3)
                continue
            for update in data.get("result", []):
                _offset = update["update_id"] + 1
                try:
                    process_update(update, sessions)
                except Exception as e:
                    logger.error(f"Error processing update: {e}", exc_info=True)
        except requests.exceptions.Timeout:
            pass
        except Exception as e:
            logger.error(f"Poll loop error: {e}")
            time.sleep(5)


def start_bot():
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set in .env — bot not started.")
        return
    t = threading.Thread(target=poll_loop, name="TelegramBot", daemon=True)
    t.start()
    logger.info("Telegram bot thread started.")
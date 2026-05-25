"""
Alert system: Telegram and Email for lowest price / price drop.
"""
import logging
import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")
EMAIL_SENDER       = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD     = os.getenv("EMAIL_PASSWORD", "")
SMTP_SERVER        = "smtp.gmail.com"
SMTP_PORT          = 587


def send_telegram(message: str):
    """Send message via Telegram bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram not configured. Set TELEGRAM_BOT_TOKEN in .env")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code != 200:
            logger.error(f"Telegram error: {resp.text}")
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")


def send_email(subject: str, body: str, recipient: str = None):
    """Send email via SMTP. recipient must be provided."""
    if not recipient:
        logger.warning("No recipient provided. Email not sent.")
        return False
    if not EMAIL_SENDER:
        logger.warning("Email not configured. Set EMAIL_SENDER and EMAIL_PASSWORD in .env")
        return False

    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        logger.info(f"Email alert sent to {recipient}")
        return True
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False


def send_alert(product_name: str, site: str, price_egp: float,
               old_price_egp: float = None, is_new_lowest: bool = False):
    """Send alerts for best price or significant drop (>10%)."""
    subject = f"💰 Price Alert: {product_name}"
    if is_new_lowest:
        body = (f"🏆 NEW LOWEST PRICE!\nSite: {site}\n"
                f"Price: {price_egp:.2f} EGP\nProduct: {product_name}")
    elif old_price_egp and old_price_egp * 0.9 > price_egp:
        drop_percent = (1 - price_egp / old_price_egp) * 100
        body = (f"📉 Price dropped {drop_percent:.1f}%!\nSite: {site}\n"
                f"Old: {old_price_egp:.2f} EGP\nNew: {price_egp:.2f} EGP\n"
                f"Product: {product_name}")
    else:
        return  # no alert needed

    send_telegram(body)
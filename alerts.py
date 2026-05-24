"""
Alert system: Telegram and Email for lowest price / price drop.
Added dynamic recipient for email.
"""
import logging
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

# ========== CONFIGURATION (edit these) ==========
TELEGRAM_BOT_TOKEN = "8713540534:AAHpM_rQUgHDwx7iqI4kYoIy0y858YFHsiY"   # Get from @BotFather
TELEGRAM_CHAT_ID = "1926979947"       # Your Telegram user/group ID

EMAIL_SENDER = "s-omar.hasan@zewailcity.edu.eg"
EMAIL_PASSWORD = "zpaolawixdekyjah"    # Gmail app password
# EMAIL_RECIPIENT is no longer used directly; we pass recipient dynamically
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
# ================================================

def send_telegram(message: str):
    """Send message via Telegram bot."""
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN":
        logger.warning("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
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
    """
    Send email via SMTP.
    If recipient is None, a default warning is issued.
    """
    if not recipient:
        logger.warning("No recipient provided. Email not sent.")
        return False
    if EMAIL_SENDER == "your_email@gmail.com":
        logger.warning("Email not configured. Set EMAIL_SENDER and EMAIL_PASSWORD.")
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

def send_alert(product_name: str, site: str, price_egp: float, old_price_egp: float = None, is_new_lowest: bool = False):
    """Send alerts for best price or significant drop (>10%)."""
    subject = f"💰 Price Alert: {product_name}"
    if is_new_lowest:
        body = f"🏆 NEW LOWEST PRICE!\nSite: {site}\nPrice: {price_egp:.2f} EGP\nProduct: {product_name}"
    elif old_price_egp and old_price_egp * 0.9 > price_egp:  # drop >10%
        drop_percent = (1 - price_egp / old_price_egp) * 100
        body = f"📉 Price dropped {drop_percent:.1f}%!\nSite: {site}\nOld: {old_price_egp:.2f} EGP\nNew: {price_egp:.2f} EGP\nProduct: {product_name}"
    else:
        return  # no alert needed

    send_telegram(body)
    # No default email recipient anymore – we send only when user requests.
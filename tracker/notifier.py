"""
Send Telegram alerts when stock is found.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
# Send alerts to the chat that requested it
# If not set, we'll just log to stdout
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def send_alert(message):
    """Send a Telegram message alert. Returns True on success."""
    if not BOT_TOKEN or not CHAT_ID:
        print(f"[ALERT would send] {message}")
        return False

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            print(f"[Telegram error] {resp.status_code}: {resp.text[:200]}")
            return False
        return True
    except Exception as e:
        print(f"[Telegram exception] {e}")
        return False


def notify_restock(store_chain, store_name, product_name, price=None, store_link=""):
    """Format and send a restock alert."""
    emoji_map = {
        "target": "🎯",
        "bestbuy": "💙",
    }
    emoji = emoji_map.get(store_chain, "🛒")
    price_str = f" — {price}" if price else ""

    msg = (
        f"{emoji} <b>RESTOCK ALERT!</b>\n"
        f"<b>{product_name}</b>{price_str}\n"
        f"📍 {store_name}\n"
    )
    if store_link:
        msg += f"🔗 <a href='{store_link}'>View Product</a>\n"

    return send_alert(msg)

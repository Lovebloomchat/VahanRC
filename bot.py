import os
import re
import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def scrape_rc(vehicle_number: str) -> dict | None:
    """Scrape VahanX for RC details. Returns dict or None on failure."""
    url = f"https://vahanx.in/rc-search/{vehicle_number.upper()}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Request failed: %s", e)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    data = {}

    # Hero section
    for card in soup.select(".hrcd-cardbody"):
        p_tag = card.find("p")
        span_tag = card.find("span")
        if p_tag and span_tag:
            key = span_tag.get_text(strip=True)
            val = p_tag.get_text(strip=True)
            data[key] = val

    # Ownership section
    for col in soup.select(".hrc-details-card .col-sm-6, .hrc-details-card .col-12"):
        span_tag = col.find("span", class_="text-muted")
        p_tag = col.find("p", class_="fw-semibold")
        if span_tag and p_tag:
            key = span_tag.get_text(strip=True)
            val = p_tag.get_text(strip=True)
            data[key] = val

    # Vehicle number heading
    h1 = soup.select_one(".col-12 h1")
    if h1:
        data["Vehicle Number"] = h1.get_text(strip=True)

    return data if data else None


def format_response(data: dict, vehicle_number: str) -> str:
    """Format scraped data into a neat Telegram message."""
    lines = [
        f"🚗 *RC Details — {vehicle_number.upper()}*",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    field_map = [
        ("Vehicle Number",  "🔢 Reg Number"),
        ("Modal Name",      "🚙 Model"),
        ("Owner Name",      "👤 Owner"),
        ("Father's Name",   "👨 Father's Name"),
        ("Owner Serial No", "🔄 Ownership"),
        ("Registered RTO",  "🏛 RTO"),
        ("Code",            "📍 RTO Code"),
        ("City Name",       "🏙 City"),
        ("Address",         "🗺 Address"),
        ("Phone",           "📞 Phone"),
    ]

    found_any = False
    for key, label in field_map:
        val = data.get(key)
        if val:
            lines.append(f"{label}: `{val}`")
            found_any = True

    if not found_any:
        return "❌ Koi details nahi mili. Vehicle number check karo."

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("_Powered by RC Lookup Bot_")
    return "\n".join(lines)


def is_valid_vehicle(text: str) -> bool:
    """Basic Indian vehicle number format check."""
    pattern = r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{1,4}$"
    return bool(re.match(pattern, text.upper().replace(" ", "")))


# ── Handlers ──────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🚘 *RC Lookup Bot*\n\n"
        "Kisi bhi Indian vehicle ka RC detail check karo — bilkul free!\n\n"
        "📌 *Kaise use karein:*\n"
        "Bas vehicle number type karo jaise:\n"
        "`BR05H4963` ya `MH12AB1234`\n\n"
        "Bot turant details fetch kar dega! ✅"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(" ", "").upper()

    if not is_valid_vehicle(text):
        await update.message.reply_text(
            "⚠️ Valid Indian vehicle number daalo.\n"
            "Example: `BR05H4963` ya `MH12AB1234`",
            parse_mode="Markdown",
        )
        return

    wait_msg = await update.message.reply_text("🔍 Searching... thoda wait karo ⏳")

    data = scrape_rc(text)
    await wait_msg.delete()

    if not data:
        await update.message.reply_text(
            "❌ Details fetch nahi ho saki.\n"
            "Vehicle number sahi hai? Ya VahanX temporarily down ho sakta hai."
        )
        return

    response = format_response(data, text)
    await update.message.reply_text(response, parse_mode="Markdown")


# ── Main ──────────────────────────────────────────────────────────

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable set nahi hai!")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("RC Lookup Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
  

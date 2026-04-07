import os
import re
import random
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

proxy_list = []


def get_proxy():
    if not proxy_list:
        return None
    proxy = random.choice(proxy_list)
    return {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}",
    }


def scrape_rc(vehicle_number):
    url = f"https://vahanx.in/rc-search/{vehicle_number.upper()}"
    proxy = get_proxy()
    try:
        resp = requests.get(url, headers=HEADERS, proxies=proxy, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error("Request failed: %s", e)
        if proxy:
            dead = list(proxy.values())[0].replace("http://", "")
            if dead in proxy_list:
                proxy_list.remove(dead)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    data = {}

    for card in soup.select(".hrcd-cardbody"):
        p_tag = card.find("p")
        span_tag = card.find("span")
        if p_tag and span_tag:
            data[span_tag.get_text(strip=True)] = p_tag.get_text(strip=True)

    for col in soup.select(".hrc-details-card .col-sm-6, .hrc-details-card .col-12"):
        span_tag = col.find("span", class_="text-muted")
        p_tag = col.find("p", class_="fw-semibold")
        if span_tag and p_tag:
            data[span_tag.get_text(strip=True)] = p_tag.get_text(strip=True)

    h1 = soup.select_one(".col-12 h1")
    if h1:
        data["Vehicle Number"] = h1.get_text(strip=True)

    return data if data else None


def format_response(data, vehicle_number):
    lines = [
        f"*RC Details — {vehicle_number.upper()}*",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    field_map = [
        ("Vehicle Number",  "Reg Number"),
        ("Modal Name",      "Model"),
        ("Owner Name",      "Owner"),
        ("Father's Name",   "Father's Name"),
        ("Owner Serial No", "Ownership"),
        ("Registered RTO",  "RTO"),
        ("Code",            "RTO Code"),
        ("City Name",       "City"),
        ("Address",         "Address"),
        ("Phone",           "Phone"),
    ]
    found_any = False
    for key, label in field_map:
        val = data.get(key)
        if val:
            lines.append(f"{label}: `{val}`")
            found_any = True

    if not found_any:
        return "Koi details nahi mili. Vehicle number check karo."

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("_RC Lookup Bot_")
    return "\n".join(lines)


def is_valid_vehicle(text):
    pattern = r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{1,4}$"
    return bool(re.match(pattern, text.upper().replace(" ", "")))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "*RC Lookup Bot*\n\n"
        "Vehicle number type karo: `BR05H4963`\n\n"
        "*Proxy Commands:*\n"
        "`/addproxy ip:port` — Proxy add karo\n"
        "`/removeproxy ip:port` — Proxy remove karo\n"
        "`/proxylist` — Sabhi proxies dekho\n"
        "`/testproxy` — Proxies test karo\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def add_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Format: `/addproxy ip:port`",
            parse_mode="Markdown",
        )
        return
    proxy = context.args[0].strip()
    if proxy in proxy_list:
        await update.message.reply_text(f"Proxy already hai: `{proxy}`", parse_mode="Markdown")
        return
    proxy_list.append(proxy)
    await update.message.reply_text(
        f"Proxy add ho gaya: `{proxy}`\nTotal: *{len(proxy_list)}*",
        parse_mode="Markdown",
    )


async def remove_proxy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Format: `/removeproxy ip:port`", parse_mode="Markdown")
        return
    proxy = context.args[0].strip()
    if proxy not in proxy_list:
        await update.message.reply_text(f"Proxy nahi mila: `{proxy}`", parse_mode="Markdown")
        return
    proxy_list.remove(proxy)
    await update.message.reply_text(
        f"Proxy remove ho gaya: `{proxy}`\nTotal: *{len(proxy_list)}*",
        parse_mode="Markdown",
    )


async def proxy_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not proxy_list:
        await update.message.reply_text("Koi proxy nahi hai.\n`/addproxy ip:port` se add karo.", parse_mode="Markdown")
        return
    lines = ["*Active Proxies:*\n"]
    for i, p in enumerate(proxy_list, 1):
        lines.append(f"{i}. `{p}`")
    lines.append(f"\nTotal: *{len(proxy_list)}*")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def test_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not proxy_list:
        await update.message.reply_text("Koi proxy nahi hai. Pehle `/addproxy` se add karo.", parse_mode="Markdown")
        return

    wait_msg = await update.message.reply_text("Testing proxies... thoda wait karo")
    results = []
    dead = []

    for proxy in proxy_list.copy():
        proxies = {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}",
        }
        try:
            r = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=8)
            if r.status_code == 200:
                results.append(f"OK `{proxy}`")
            else:
                results.append(f"FAIL `{proxy}` — {r.status_code}")
                dead.append(proxy)
        except Exception:
            results.append(f"DEAD `{proxy}`")
            dead.append(proxy)

    for d in dead:
        if d in proxy_list:
            proxy_list.remove(d)

    lines = ["*Proxy Test Results:*\n"] + results
    if dead:
        lines.append(f"\n{len(dead)} dead proxy remove ho gaye.")
    lines.append(f"Active proxies: *{len(proxy_list)}*")

    await wait_msg.delete()
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(" ", "").upper()

    if not is_valid_vehicle(text):
        await update.message.reply_text(
            "Valid vehicle number daalo. Example: `BR05H4963`",
            parse_mode="Markdown",
        )
        return

    proxy_status = f"Proxy ON ({len(proxy_list)})" if proxy_list else "Direct (no proxy)"
    wait_msg = await update.message.reply_text(f"Searching... {proxy_status}")

    data = scrape_rc(text)
    await wait_msg.delete()

    if not data:
        await update.message.reply_text(
            "Details fetch nahi ho saki. Vehicle number sahi hai?"
        )
        return

    response = format_response(data, text)
    await update.message.reply_text(response, parse_mode="Markdown")


def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN set nahi hai!")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addproxy", add_proxy))
    app.add_handler(CommandHandler("removeproxy", remove_proxy_cmd))
    app.add_handler(CommandHandler("proxylist", proxy_list_cmd))
    app.add_handler(CommandHandler("testproxy", test_proxy))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
  

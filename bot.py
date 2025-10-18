# bot.py — webhook-ready для PTB 21.4
import os
import json
import logging
import re
from pathlib import Path
from typing import Optional

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

CFG_PATH = Path("config.json")


def load_config():
    if CFG_PATH.exists():
        with CFG_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def extract_city_structured(text: str) -> Optional[str]:
    m = re.search(r"Город[:\s\-–]*([^\n,\\/]+)", text, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def find_city_by_name(text: str, cities_list, ci=True) -> Optional[str]:
    txt = text.lower() if ci else text
    for c in cities_list:
        key = c.lower() if ci else c
        if re.search(rf"\b{re.escape(key)}\b", txt):
            return c
    return None


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None or update.message.text is None:
        return

    cfg = context.bot_data.get("cfg", {})
    allowed = cfg.get("allowed_chat_ids")
    # если allowed пустой или не указан — слушаем все чаты
    if allowed and update.effective_chat.id not in allowed:
        return

    text = update.message.text
    log.info("New msg in %s: %s", update.effective_chat.id, text[:120])

    city = extract_city_structured(text)
    if not city:
        city = find_city_by_name(
            text, list(cfg.get("cities", {}).keys()), cfg.get("match_case_insensitive", True)
        )

    if not city:
        return

    city_key = city.split(",")[0].strip()
    cities_map = cfg.get("cities", {})
    matched_key = None
    for k in cities_map.keys():
        if k.lower() == city_key.lower():
            matched_key = k
            break
    if not matched_key:
        for k in cities_map.keys():
            if city_key.lower() in k.lower():
                matched_key = k
                break
    if not matched_key:
        return

    users = cities_map.get(matched_key, [])
    if not users:
        return

    mention_text = " ".join(users)
    hashtag = f"#{matched_key.replace(' ', '')}"
    reply = f"{mention_text} {hashtag}"

    try:
        await update.message.reply_text(reply)
    except Exception as e:
        log.exception("Failed to reply: %s", e)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Я слежу за объявлениями и буду упоминать людей по городам.")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("Error while handling update: %s", context.error)


def main():
    # Конфиг: либо из файла, либо (рекомендую для Render) из ENV
    cfg = load_config()
    token = os.environ.get("BOT_TOKEN") or cfg.get("bot_token")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set")

    # Build app
    app = ApplicationBuilder().token(token).build()
    app.bot_data["cfg"] = cfg

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), on_message))
    app.add_error_handler(error_handler)

    # webhook settings
    PORT = int(os.environ.get("PORT", 8443))
    # public url - Render выдаёт URL вида https://<service>.onrender.com
    # Зададим путь webhook = /{token} (безопаснее — уникален)
    service_url = os.environ.get("SERVICE_URL")  # optional: явно указать https://...
    if service_url:
        public_url = service_url.rstrip("/")
    else:
        # подставь свой адрес Render, например: https://city-tags-bot.onrender.com
        public_url = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/") or ""

    webhook_path = f"/{token}"
    webhook_url = public_url + webhook_path if public_url else None

    if webhook_url:
        log.info("Using webhook url: %s", webhook_url)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            webhook_url=webhook_url,
            url_path=token
        )
    else:
        # fallback — если публичного URL нет, делаем polling (локально)
        log.warning("No public URL found; falling back to polling (not for Render)")
        app.run_polling()


if __name__ == "__main__":
    main()

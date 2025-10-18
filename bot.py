import json
import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import asyncio

# ---------------------- НАСТРОЙКИ ----------------------
CONFIG_PATH = "config.json"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

config = load_config()
BOT_TOKEN = config["bot_token"]
ALLOWED_CHAT_IDS = set(config["allowed_chat_ids"])
OWNER_ID = 6742361886  # Только ты можешь редактировать города/теги

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ---------------------- ХЭНДЛЕРЫ ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот запущен. Отправь название города или отклик.")

async def add_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("⛔ У тебя нет прав для добавления городов.")
    if len(context.args) < 2:
        return await update.message.reply_text("❗ Используй формат:\n/add <город> <@тег>")
    city, tag = context.args[0], context.args[1]
    config = load_config()
    config["cities"][city] = [tag]
    save_config(config)
    await update.message.reply_text(f"✅ Добавлен город {city} с тегом {tag}")

async def del_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return await update.message.reply_text("⛔ У тебя нет прав для удаления городов.")
    if not context.args:
        return await update.message.reply_text("❗ Используй формат:\n/del <город>")
    city = context.args[0]
    config = load_config()
    if city in config["cities"]:
        del config["cities"][city]
        save_config(config)
        await update.message.reply_text(f"🗑 Удалён город {city}")
    else:
        await update.message.reply_text("❌ Город не найден.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    config = load_config()
    cities = config["cities"]

    for city, tags in cities.items():
        if city.lower() in text.lower():
            mention = " ".join(tags)
            response = f"{mention}\n#{city.replace(' ', '_')}"
            await update.message.reply_text(response, reply_to_message_id=update.message.message_id)
            return
    await update.message.reply_text("⚠️ Город не найден в списке.")

# ---------------------- ЗАПУСК ----------------------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_city))
    app.add_handler(CommandHandler("del", del_city))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    port = int(os.environ.get("PORT", 8443))
    domain = os.environ.get("RENDER_EXTERNAL_URL")

    if domain:
        webhook_url = f"{domain}/webhook"
        logging.info(f"🌐 Устанавливаю webhook: {webhook_url}")
        try:
            await app.run_webhook(
                listen="0.0.0.0",
                port=port,
                webhook_url=webhook_url,
            )
        except Exception as e:
            logging.error(f"❌ Ошибка webhook ({e}), переключаюсь на polling")
            await app.run_polling()
    else:
        logging.info("⚙️ Домен не найден, запускаю polling")
        await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

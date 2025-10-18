import json
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ------------------- ЛОГИРОВАНИЕ -------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------------------- ЗАГРУЗКА КОНФИГА -------------------
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
ALLOWED_CHAT_IDS = config["allowed_chat_ids"]
CITIES = config["cities"]
MATCH_CASE_INSENSITIVE = config.get("match_case_insensitive", True)

# ------------------- ФУНКЦИИ -------------------
def find_city(text: str):
    for city, tags in CITIES.items():
        if (MATCH_CASE_INSENSITIVE and city.lower() in text.lower()) or (city in text):
            return city, tags[0]  # берем первого ответственного
    return None, None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    text = update.message.text

    logger.info(f"Получено сообщение от {user.username} ({chat_id}): {text}")

    if chat_id not in ALLOWED_CHAT_IDS:
        logger.warning(f"Сообщение от запрещенного чата: {chat_id}")
        return

    city, responsible = find_city(text)
    if city and responsible:
        reply = f"{responsible}, #{city}"
        await update.message.reply_text(reply)
        logger.info(f"Ответ отправлен: {reply}")
    else:
        logger.info("Город или ответственный не найден.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот активен и готов отвечать! 🚀")

# ------------------- ЗАПУСК -------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info(f"Webhook URL: https://city-tags-bot.onrender.com/{BOT_TOKEN}")
    logger.info(f"Allowed chat ids: {ALLOWED_CHAT_IDS}")

    app.run_webhook(
        listen="0.0.0.0",
        port=8000,
        webhook_url=f"https://city-tags-bot.onrender.com/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()

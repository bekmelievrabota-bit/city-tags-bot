import logging
import json
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)

# ======================
# Логирование
# ======================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ======================
# Загрузка config.json
# ======================
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
ALLOWED_CHAT_IDS = config.get("allowed_chat_ids", [])
CITIES = config.get("cities", {})
MATCH_CASE_INSENSITIVE = config.get("match_case_insensitive", True)

# ======================
# Команды
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
        return
    logger.info(f"/start вызван пользователем {update.effective_user.id}")
    await update.message.reply_text(
        "Привет! Я бот и теперь работаю в личке и в группах!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
        return
    await update.message.reply_text(
        "Список команд:\n"
        "/start - начать работу\n"
        "/help - показать это сообщение"
    )

# ======================
# Обработка текстовых сообщений
# ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
        return

    user_id = update.effective_user.id
    username = update.effective_user.username
    text = update.message.text
    logger.info(f"Сообщение от {username} ({user_id}): {text}")

    response_tags = []

    # Поиск городов в сообщении
    for city, tags in CITIES.items():
        if MATCH_CASE_INSENSITIVE:
            if city.lower() in text.lower():
                response_tags.extend(tags)
        else:
            if city in text:
                response_tags.extend(tags)

    if response_tags:
        await update.message.reply_text(
            " ".join(response_tags)
        )
    else:
        await update.message.reply_text(f"Вы написали: {text}")

# ======================
# Основная функция
# ======================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Обработка текстовых сообщений
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))

    # Порт для Render
    port = int(os.environ.get("PORT", 8000))

    # Запуск вебхука
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        webhook_url=f"https://city-tags-bot.onrender.com/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()

import logging
import json
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)

# ======================
# Настройка логирования
# ======================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ======================
# Загрузка конфигурации
# ======================
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

TOKEN = config["bot_token"]
ALLOWED_CHAT_IDS = config.get("allowed_chat_ids")  # None = разрешить все чаты
CITIES = config.get("cities", {})
MATCH_CASE_INSENSITIVE = config.get("match_case_insensitive", True)

# ======================
# Команды
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
        logger.warning(f"Доступ запрещён для чата {chat_id}")
        return

    await update.message.reply_text(
        "Привет! Я бот и теперь работаю в личке и в группах!"
    )
    logger.info(f"/start вызван пользователем {update.effective_user.id} в чате {chat_id}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
        return

    commands_text = (
        "Список команд:\n"
        "/start - начать работу\n"
        "/help - показать это сообщение\n\n"
        "Просто напишите название города, и я покажу теги HR."
    )
    await update.message.reply_text(commands_text)

# ======================
# Обработка текстовых сообщений
# ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    username = update.effective_user.username
    text = update.message.text

    # Проверяем доступ
    if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
        logger.warning(f"Сообщение от запрещённого чата {chat_id}")
        return

    logger.info(f"Сообщение от {username} ({user_id}) в чате {chat_id}: {text}")

    # Поиск тегов города
    result = None
    for city, tags in CITIES.items():
        if MATCH_CASE_INSENSITIVE:
            if text.lower() == city.lower():
                result = tags
                break
        else:
            if text == city:
                result = tags
                break

    if result:
        reply = f"Теги HR для города {text}: {', '.join(result)}"
    else:
        reply = f"Не удалось найти город '{text}'. Попробуйте другой."

    await update.message.reply_text(reply)

# ======================
# Основная функция
# ======================
def main():
    PORT = int(os.environ.get("PORT", 8000))
    app = ApplicationBuilder().token(TOKEN).build()

    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Обработчик текстовых сообщений
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    ))

    logger.info(f"Webhook URL: https://city-tags-bot.onrender.com/{TOKEN}")
    logger.info(f"Allowed chat ids: {ALLOWED_CHAT_IDS}")

    # Запуск вебхука
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=f"https://city-tags-bot.onrender.com/{TOKEN}"
    )

if __name__ == "__main__":
    main()

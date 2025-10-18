import json
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ======================
# Логирование
# ======================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ======================
# Загружаем конфиг
# ======================
with open("config.json", encoding="utf-8") as f:
    config = json.load(f)

bot_token = config["bot_token"]
allowed_chat_ids = config["allowed_chat_ids"]
cities = config["cities"]
match_case_insensitive = config.get("match_case_insensitive", True)

logger.info(f"Webhook URL: https://city-tags-bot.onrender.com/{bot_token}")
logger.info(f"Allowed chat ids: {allowed_chat_ids}")

# ======================
# Команды
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in allowed_chat_ids:
        return
    await update.message.reply_text("Привет! Я бот и теперь работаю в группах и личке!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in allowed_chat_ids:
        return
    await update.message.reply_text(
        "Список команд:\n"
        "/start - начать работу\n"
        "/help - показать это сообщение"
    )

# ======================
# Обработка сообщений
# ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in allowed_chat_ids:
        logger.info(f"Сообщение из запрещённого чата: {chat_id}")
        return

    text = update.message.text
    logger.info(f"Сообщение в чате {chat_id}: {text}")

    # Можно добавить проверку на города
    response = "Вы написали: " + text
    await update.message.reply_text(response)

# ======================
# Основная функция
# ======================
def main():
    app = ApplicationBuilder().token(bot_token).build()

    # Обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Обработчик текстовых сообщений в личке и группах
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Запуск webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=8000,
        webhook_url=f"https://city-tags-bot.onrender.com/{bot_token}"
    )

if __name__ == "__main__":
    main()

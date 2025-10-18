import json
import logging
import re
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
# Загрузка конфигурации
# ======================
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
ALLOWED_CHAT_IDS = config.get("allowed_chat_ids", [])
CITIES = config.get("cities", {})
MATCH_CASE_INSENSITIVE = config.get("match_case_insensitive", True)

logger.info(f"Webhook URL: https://city-tags-bot.onrender.com/{BOT_TOKEN}")
logger.info(f"Allowed chat ids: {ALLOWED_CHAT_IDS}")

# ======================
# Команды
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    logger.info(f"/start вызван в чате {chat_id} пользователем {update.effective_user.id}")
    await update.message.reply_text("Привет! Я бот и теперь работаю в личке и в группах!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Список команд:\n"
        "/start - начать работу\n"
        "/help - показать это сообщение"
    )

# ======================
# Функция обработки откликов
# ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username

    logger.info(f"Сообщение от {username} ({user_id}) в чате {chat_id}: {text}")

    if chat_id not in ALLOWED_CHAT_IDS:
        logger.info(f"Чат {chat_id} не разрешён.")
        return

    # Ищем город в тексте
    city_found = None
    for city in CITIES.keys():
        compare_text = text.lower() if MATCH_CASE_INSENSITIVE else text
        compare_city = city.lower() if MATCH_CASE_INSENSITIVE else city
        if compare_city in compare_text:
            city_found = city
            break

    if not city_found:
        logger.info("Город не найден в сообщении.")
        return

    # Берём первого ответственного из списка
    responsible = CITIES[city_found][0]

    # Формируем ответ
    response = f"{responsible}, #{city_found.replace(' ', '')}"

    # Отправляем в чат
    await update.message.reply_text(response)

# ======================
# Основная функция
# ======================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND &
        (filters.ChatType.PRIVATE | filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
        handle_message
    ))

    app.run_webhook(
        listen="0.0.0.0",
        port=8000,
        webhook_url=f"https://city-tags-bot.onrender.com/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()

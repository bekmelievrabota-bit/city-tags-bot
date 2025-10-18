import json
import logging
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
with open("config.json", encoding="utf-8") as f:
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
    logger.info(f"/start вызван в чате {chat_id} пользователем {update.effective_user.id}")
    await update.message.reply_text(
        "Привет! Я бот и теперь работаю в личке и в группах!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    user_id = update.effective_user.id
    username = update.effective_user.username
    text = update.message.text

    # Логируем сообщение
    logger.info(f"Сообщение от {username} ({user_id}) в чате {chat_id}: {text}")

    # Проверяем, разрешён ли чат
    if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
        await update.message.reply_text("Извините, этот чат не разрешён для работы с ботом.")
        return

    # Ищем город в тексте
    response = []
    text_to_match = text.lower() if MATCH_CASE_INSENSITIVE else text
    for city, accounts in CITIES.items():
        city_to_match = city.lower() if MATCH_CASE_INSENSITIVE else city
        if city_to_match in text_to_match:
            response.append(f"{city}: {', '.join(accounts)}")

    if response:
        await update.message.reply_text("\n".join(response))
    else:
        await update.message.reply_text("Город не найден или нет данных для этого города.")

# =

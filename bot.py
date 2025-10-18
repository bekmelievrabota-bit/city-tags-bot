import json
import logging
import re
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CallbackQueryHandler, ConversationHandler, CommandHandler

# Логирование
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загружаем конфиг
CONFIG_FILE = "config.json"  # или tags.json, если так у тебя
with open(CONFIG_FILE, encoding="utf-8") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
ALLOWED_CHAT_IDS = set(config["allowed_chat_ids"])
CITIES = config["cities"]
MATCH_CASE_INSENSITIVE = config.get("match_case_insensitive", True)

# Подготовка regex для поиска городов
CITY_PATTERNS = {
    city: re.compile(re.escape(city), re.IGNORECASE if MATCH_CASE_INSENSITIVE else 0)
    for city in CITIES
}

# ------------------ Твой существующий функционал ------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in ALLOWED_CHAT_IDS:
        return  # игнорируем чужие чаты

    text = update.effective_message.text
    if not text:
        return

    tagged_users = []
    hashtags = []

    for city, pattern in CITY_PATTERNS.items():
        if pattern.search(text):
            hashtags.append(f"#{city}")
            tagged_users.extend(CITIES[city])

    if tagged_users:
        response = f"{', '.join(tagged_users)}, {' '.join(hashtags)}"
        await update.message.reply_text(response)
        logger.info(f"Ответ отправлен: {response}")

# ------------------ Новый функционал с кнопками ------------------
ADD_CITY, ADD_TAG = range(2)

async def start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Добавить город", callback_data="add_city")],
        [InlineKeyboardButton("Добавить тег", callback_data="add_tag")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add_city":
        await query.message.reply_text("Введите название нового города:")
        return ADD_CITY
    elif query.data == "add_tag":
        await query.message.reply_text("Введите тег для города (например: user1,user2):")
        return ADD_TAG

async def add_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city_name = update.message.text.strip()
    if city_name in CITIES:
        await update.message.reply_text("Город уже существует.")
    else:
        CITIES[city_name] = []
        CITY_PATTERNS[city_name] = re.compile(re.escape(city_name), re.IGNORECASE if MATCH_CASE_INSENSITIVE else 0)
        save_config()
        await update.message.reply_text(f"Город '{city_name}' добавлен.")
    return ConversationHandler.END

async def add_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if "," not in text:
        await update.message.reply_text("Введите через запятую: Город,Пользователь1,Пользователь2...")
        return ADD_TAG
    parts = text.split(",")
    city_name = parts[0].strip()
    tags = [p.strip() for p in parts[1:]]
    if city_name not in CITIES:
        await update.message.reply_text(f"Город '{city_name}' не найден.")
    else:
        CITIES[city_name].extend(tags)
        save_config()
        await update.message.reply_text(f"Теги для города '{city_name}' добавлены: {', '.join(tags)}")
    return ConversationHandler.END

def save_config():
    config["cities"] = CITIES
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def main():
    # Webhook адрес Render
    PORT = int(os.environ.get("PORT", 8000))
    APP_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"

    application = Application.builder().token(BOT_TOKEN).build()

    # Обрабатываем все текстовые сообщения
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ------------------ Новый функционал ------------------
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("menu", start_menu), CallbackQueryHandler(button_handler)],
        states={
            ADD_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_city)],
            ADD_TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_tag)],
        },
        fallbacks=[]
    )
    application.add_handler(conv_handler)

    logger.info(f"🚀 Запуск на порту {PORT}, webhook {APP_URL}")
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=APP_URL,
    )

if __name__ == "__main__":
    main()

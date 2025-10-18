import json
import logging
import re
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
    CommandHandler,
    ConversationHandler,
    CallbackQueryHandler,
)

# --------------------- Твой существующий код --------------------- #

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"  # или tags.json
with open(CONFIG_FILE, encoding="utf-8") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
ALLOWED_CHAT_IDS = set(config["allowed_chat_ids"])
CITIES = config["cities"]
MATCH_CASE_INSENSITIVE = config.get("match_case_insensitive", True)

CITY_PATTERNS = {
    city: re.compile(re.escape(city), re.IGNORECASE if MATCH_CASE_INSENSITIVE else 0)
    for city in CITIES
}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in ALLOWED_CHAT_IDS:
        return

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

# --------------------- Новый код для кнопок --------------------- #

# Состояния для ConversationHandler
ADD_CITY, ADD_TAG = range(2)

# Команда /menu
async def start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Добавить город", callback_data="add_city")],
        [InlineKeyboardButton("Добавить тег", callback_data="add_tag")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Что вы хотите сделать?", reply_markup=reply_markup)

# Обработка нажатий кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add_city":
        context.user_data["action"] = "add_city"
        await query.message.reply_text("Введите название нового города:")
        return ADD_CITY
    elif query.data == "add_tag":
        context.user_data["action"] = "add_tag"
        await query.message.reply_text("Введите тег для города (например: user1,user2):")
        return ADD_TAG

# Добавление города
async def add_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_city = update.message.text.strip()
    if new_city in CITIES:
        await update.message.reply_text("Такой город уже существует!")
        return ConversationHandler.END
    CITIES[new_city] = []
    # Обновляем regex
    CITY_PATTERNS[new_city] = re.compile(re.escape(new_city), re.IGNORECASE if MATCH_CASE_INSENSITIVE else 0)
    await update.message.reply_text(f"Город '{new_city}' добавлен.")
    logger.info(f"Добавлен город: {new_city}")
    return ConversationHandler.END

# Добавление тега к городу
async def add_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tag_info = update.message.text.strip()
    try:
        city, users_str = tag_info.split(":", 1)  # формат "Город: user1,user2"
        users = [u.strip() for u in users_str.split(",") if u.strip()]
    except ValueError:
        await update.message.reply_text("Неверный формат! Используйте 'Город: user1,user2'")
        return ConversationHandler.END

    if city not in CITIES:
        await update.message.reply_text("Такого города нет! Сначала добавьте город.")
        return ConversationHandler.END

    CITIES[city].extend(users)
    await update.message.reply_text(f"Теги {users} добавлены к городу '{city}'.")
    logger.info(f"Добавлены теги к {city}: {users}")
    return ConversationHandler.END

def main():
    PORT = int(os.environ.get("PORT", 8000))
    APP_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"

    application = Application.builder().token(BOT_TOKEN).build()

    # Обрабатываем текстовые сообщения для тегов
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ConversationHandler для меню и кнопок
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("menu", start_menu), CallbackQueryHandler(button_handler)],
        states={
            ADD_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_city)],
            ADD_TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_tag)],
        },
        fallbacks=[],
        per_user=True,
        per_chat=True
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

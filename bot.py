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

CONFIG_FILE = "config.json"
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
WAIT_CITY_NAME, WAIT_TAG_NAME, WAIT_TAG_USERS = range(3)

# Команда /menu
async def start_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Добавить город", callback_data="add_city")],
        [InlineKeyboardButton("Добавить тег", callback_data="add_tag")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Что вы хотите сделать?", reply_markup=reply_markup)

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "add_city":
        await query.message.reply_text("Введите название нового города:")
        return WAIT_CITY_NAME
    elif query.data == "add_tag":
        await query.message.reply_text("Введите название города, к которому хотите добавить тег:")
        return WAIT_TAG_NAME

# Обработка нового города
async def add_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_city = update.message.text.strip()
    if new_city in CITIES:
        await update.message.reply_text("Такой город уже существует!")
    else:
        CITIES[new_city] = []
        CITY_PATTERNS[new_city] = re.compile(
            re.escape(new_city), re.IGNORECASE if MATCH_CASE_INSENSITIVE else 0
        )
        await update.message.reply_text(f"Город '{new_city}' добавлен.")
        logger.info(f"Добавлен город: {new_city}")
    return ConversationHandler.END

# Обработка ввода города для тега
async def ask_tag_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text.strip()
    if city not in CITIES:
        await update.message.reply_text("Такого города нет! Сначала добавьте город.")
        return ConversationHandler.END
    context.user_data["tag_city"] = city
    await update.message.reply_text(f"Введите пользователей для города '{city}' через запятую:")
    return WAIT_TAG_USERS

# Обработка пользователей для тега
async def add_tag_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = context.user_data.get("tag_city")
    if not city:
        await update.message.reply_text("Ошибка: город не найден в данных.")
        return ConversationHandler.END

    users = [u.strip() for u in update.message.text.split(",") if u.strip()]
    CITIES[city].extend(users)
    await update.message.reply_text(f"Пользователи {users} добавлены к городу '{city}'.")
    logger.info(f"Добавлены пользователи к {city}: {users}")
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
            WAIT_CITY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_city)],
            WAIT_TAG_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_tag_users)],
            WAIT_TAG_USERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_tag_users)],
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
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CallbackQueryHandler, CommandHandler, MessageHandler, filters

# состояния
WAIT_CITY_NAME, WAIT_TAG = range(2)

# меню с кнопками
async def menu_command(update, context):
    keyboard = [
        [InlineKeyboardButton("Добавить город", callback_data="add_city")],
        [InlineKeyboardButton("Добавить тег", callback_data="add_tag")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Что хотите сделать?", reply_markup=reply_markup)
    return WAIT_CITY_NAME  # ждем выбора кнопки

# обработка нажатий кнопок
async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "add_city":
        await query.message.reply_text("Введите название нового города:")
        context.user_data["action"] = "city"
        return WAIT_CITY_NAME
    elif query.data == "add_tag":
        await query.message.reply_text("Введите город, к которому хотите добавить тег:")
        context.user_data["action"] = "tag"
        return WAIT_TAG
    return WAIT_CITY_NAME

# обработка введенного текста
async def text_input(update, context):
    action = context.user_data.get("action")
    text = update.message.text.strip()
    if action == "city":
        # здесь можно добавить город в конфиг или просто логировать
        CITIES[text] = []
        await update.message.reply_text(f"Город '{text}' добавлен ✅")
    elif action == "tag":
        # ожидаем ввода "город:тег" например
        try:
            city, tag = map(str.strip, text.split(":"))
            if city in CITIES:
                CITIES[city].append(tag)
                await update.message.reply_text(f"Тег '{tag}' добавлен к городу '{city}' ✅")
            else:
                await update.message.reply_text(f"Город '{city}' не найден ❌")
        except:
            await update.message.reply_text("Неверный формат! Используйте: город:тег")
    # возвращаем меню
    await menu_command(update, context)
    return WAIT_CITY_NAME

# создаем ConversationHandler
menu_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("menu", menu_command)],
    states={
        WAIT_CITY_NAME: [
            CallbackQueryHandler(button_handler),
            MessageHandler(filters.TEXT & ~filters.COMMAND, text_input)
        ],
        WAIT_TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_input)],
    },
    fallbacks=[CommandHandler("menu", menu_command)],
)

# подключаем к приложению
application.add_handler(menu_conv_handler)

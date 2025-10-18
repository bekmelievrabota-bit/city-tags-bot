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

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# Состояния для меню
CHOOSING, TYPING_CITY, TYPING_TAG = range(3)

def menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("Добавить город", callback_data="add_city")],
        [InlineKeyboardButton("Добавить тег", callback_data="add_tag")],
        [InlineKeyboardButton("Удалить город", callback_data="remove_city")],
        [InlineKeyboardButton("Удалить тег", callback_data="remove_tag")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def menu_start(update, context):
    await update.message.reply_text(
        "Выберите действие:", reply_markup=menu_keyboard()
    )
    return CHOOSING

async def menu_choice(update, context):
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "add_city":
        await query.message.reply_text("Введите название города для добавления:")
        return TYPING_CITY
    elif choice == "add_tag":
        await query.message.reply_text("Введите тег для добавления:")
        return TYPING_TAG
    elif choice == "remove_city":
        await query.message.reply_text("Введите название города для удаления:")
        return TYPING_CITY
    elif choice == "remove_tag":
        await query.message.reply_text("Введите тег для удаления:")
        return TYPING_TAG

async def received_text(update, context):
    text = update.message.text.strip()

    # Проверяем, что это город или тег
    if context.user_data.get("state") == "city":
        if text in CITIES:
            # удаление
            del CITIES[text]
            await update.message.reply_text(f"Город {text} удалён.")
        else:
            # добавление
            CITIES[text] = []
            await update.message.reply_text(f"Город {text} добавлен.")
    elif context.user_data.get("state") == "tag":
        # Обработка тегов аналогично (можно хранить список TAGS)
        TAGS = context.bot_data.setdefault("tags", [])
        if text in TAGS:
            TAGS.remove(text)
            await update.message.reply_text(f"Тег {text} удалён.")
        else:
            TAGS.append(text)
            await update.message.reply_text(f"Тег {text} добавлен.")

    # После обработки возвращаемся в меню
    await update.message.reply_text("Выберите действие:", reply_markup=menu_keyboard())
    return CHOOSING

async def set_state_city(update, context):
    context.user_data["state"] = "city"

async def set_state_tag(update, context):
    context.user_data["state"] = "tag"

# ConversationHandler для меню
menu_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("menu", menu_start)],
    states={
        CHOOSING: [CallbackQueryHandler(menu_choice)],
        TYPING_CITY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, set_state_city),
            MessageHandler(filters.TEXT & ~filters.COMMAND, received_text),
        ],
        TYPING_TAG: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, set_state_tag),
            MessageHandler(filters.TEXT & ~filters.COMMAND, received_text),
        ],
    },
    fallbacks=[],
    per_message=False,
)

# Добавляем обработчик в приложение
application.add_handler(menu_conv_handler)

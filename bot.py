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
from telegram.ext import ConversationHandler, CallbackQueryHandler, CommandHandler, MessageHandler, filters

WAIT_ACTION, WAIT_INPUT = range(2)

async def menu_command(update, context):
    keyboard = [
        [InlineKeyboardButton("Добавить город", callback_data="add_city"),
         InlineKeyboardButton("Удалить город", callback_data="remove_city")],
        [InlineKeyboardButton("Добавить тег", callback_data="add_tag"),
         InlineKeyboardButton("Удалить тег", callback_data="remove_tag")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
    return WAIT_ACTION

async def button_handler(update, context):
    query = update.callback_query
    await query.answer()
    context.user_data["action"] = query.data
    if query.data in ["add_city", "remove_city"]:
        await query.message.reply_text("Введите название города:")
    elif query.data in ["add_tag", "remove_tag"]:
        await query.message.reply_text("Введите город и тег через двоеточие, например: Москва:Проверка")
    return WAIT_INPUT

async def text_input(update, context):
    text = update.message.text.strip()
    action = context.user_data.get("action")

    if action == "add_city":
        if text in CITIES:
            await update.message.reply_text(f"Город '{text}' уже существует ❌")
        else:
            CITIES[text] = []
            CITY_PATTERNS[text] = re.compile(re.escape(text), re.IGNORECASE if MATCH_CASE_INSENSITIVE else 0)
            await update.message.reply_text(f"Город '{text}' добавлен ✅")

    elif action == "remove_city":
        if text in CITIES:
            del CITIES[text]
            del CITY_PATTERNS[text]
            await update.message.reply_text(f"Город '{text}' удален ✅")
        else:
            await update.message.reply_text(f"Город '{text}' не найден ❌")

    elif action == "add_tag":
        try:
            city, tag = map(str.strip, text.split(":"))
            if city in CITIES:
                if tag in CITIES[city]:
                    await update.message.reply_text(f"Тег '{tag}' уже существует для города '{city}' ❌")
                else:
                    CITIES[city].append(tag)
                    await update.message.reply_text(f"Тег '{tag}' добавлен к городу '{city}' ✅")
            else:
                await update.message.reply_text(f"Город '{city}' не найден ❌")
        except:
            await update.message.reply_text("Неверный формат! Используйте: город:тег")

    elif action == "remove_tag":
        try:
            city, tag = map(str.strip, text.split(":"))
            if city in CITIES and tag in CITIES[city]:
                CITIES[city].remove(tag)
                await update.message.reply_text(f"Тег '{tag}' удален у города '{city}' ✅")
            else:
                await update.message.reply_text(f"Город или тег не найден ❌")
        except:
            await update.message.reply_text("Неверный формат! Используйте: город:тег")

    # Возвращаем меню после действия
    await menu_command(update, context)
    return WAIT_ACTION

# ================= ConversationHandler =================
menu_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("menu", menu_command)],
    states={
        WAIT_ACTION: [CallbackQueryHandler(button_handler)],
        WAIT_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_input)],
    },
    fallbacks=[CommandHandler("menu", menu_command)],
    per_message=True  # <--- добавляем, чтобы убрать предупреждение
)

# ================= В main добавляем =================
# application.add_handler(menu_conv_handler)

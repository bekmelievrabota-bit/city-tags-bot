import json
import logging
import re
import os
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

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

def main():
    # Webhook адрес Render
    PORT = int(os.environ.get("PORT", 8000))
    APP_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{BOT_TOKEN}"

    application = Application.builder().token(BOT_TOKEN).build()

    # Обрабатываем все текстовые сообщения
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info(f"🚀 Запуск на порту {PORT}, webhook {APP_URL}")
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=APP_URL,
    )

if __name__ == "__main__":
    main()
# Меню с кнопками для управления городами и тегами
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, ConversationHandler

# Состояния для меню
CHOOSING_ACTION, ADD_CITY, ADD_TAG, REMOVE_CITY, REMOVE_TAG = range(5)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Открывает меню при /start"""
    keyboard = [
        [InlineKeyboardButton("➕ Добавить город", callback_data="add_city")],
        [InlineKeyboardButton("➕ Добавить тег", callback_data="add_tag")],
        [InlineKeyboardButton("➖ Удалить город", callback_data="remove_city")],
        [InlineKeyboardButton("➖ Удалить тег", callback_data="remove_tag")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
    return CHOOSING_ACTION

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий кнопок"""
    query = update.callback_query
    await query.answer()

    if query.data == "add_city":
        await query.edit_message_text("Введите название нового города:")
        context.user_data["action"] = "add_city"
        return ADD_CITY

    elif query.data == "add_tag":
        await query.edit_message_text("Введите название нового тега:")
        context.user_data["action"] = "add_tag"
        return ADD_TAG

    elif query.data == "remove_city":
        await query.edit_message_text("Введите название города для удаления:")
        context.user_data["action"] = "remove_city"
        return REMOVE_CITY

    elif query.data == "remove_tag":
        await query.edit_message_text("Введите тег для удаления:")
        context.user_data["action"] = "remove_tag"
        return REMOVE_TAG

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавляет или удаляет данные после ввода текста"""
    user_input = update.message.text.strip()
    action = context.user_data.get("action")

    if not action:
        await update.message.reply_text("Используйте /start, чтобы открыть меню.")
        return ConversationHandler.END

    # Работа с config.json
    with open(CONFIG_FILE, encoding="utf-8") as f:
        config = json.load(f)

    if action == "add_city":
        if user_input not in config["cities"]:
            config["cities"][user_input] = []
            await update.message.reply_text(f"✅ Город {user_input} добавлен.")
        else:
            await update.message.reply_text("⚠️ Такой город уже есть.")

    elif action == "add_tag":
        last_city = list(config["cities"].keys())[-1] if config["cities"] else None
        if last_city:
            config["cities"][last_city].append(user_input)
            await update.message.reply_text(f"✅ Тег {user_input} добавлен к городу {last_city}.")
        else:
            await update.message.reply_text("⚠️ Сначала добавьте город.")

    elif action == "remove_city":
        if user_input in config["cities"]:
            del config["cities"][user_input]
            await update.message.reply_text(f"🗑 Город {user_input} удалён.")
        else:
            await update.message.reply_text("⚠️ Такого города нет.")

    elif action == "remove_tag":
        for city, tags in config["cities"].items():
            if user_input in tags:
                tags.remove(user_input)
                await update.message.reply_text(f"🗑 Тег {user_input} удалён из города {city}.")
                break
        else:
            await update.message.reply_text("⚠️ Тег не найден.")

    # Сохраняем изменения
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    context.user_data.clear()
    await update.message.reply_text("✅ Изменения сохранены. Чтобы открыть меню снова — /start")
    return ConversationHandler.END


# Регистрация хендлеров
def register_menu_handlers(application):
    menu_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_ACTION: [CallbackQueryHandler(button_handler)],ADD_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)],
            ADD_TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)],
            REMOVE_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)],
            REMOVE_TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler)],
        },
        fallbacks=[],
        name="menu_conversation",
        persistent=False,
    )

    application.add_handler(menu_conv_handler)
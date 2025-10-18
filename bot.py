import json
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ---------- Логирование ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------- Загрузка конфига ----------
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
ALLOWED_CHAT_IDS = config["allowed_chat_ids"]
CITIES = config.get("cities", {})
MATCH_CASE_INSENSITIVE = config.get("match_case_insensitive", True)

ADMIN_IDS = [6742361886]  # твой ID, если нужно можно брать из конфига

# ---------- Обработчики ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start для лички"""
    if update.effective_chat.id in ADMIN_IDS:
        keyboard = [
            [InlineKeyboardButton("Добавить город", callback_data="add_city")],
            [InlineKeyboardButton("Удалить город", callback_data="remove_city")],
            [InlineKeyboardButton("Добавить тег", callback_data="add_tag")],
            [InlineKeyboardButton("Удалить тег", callback_data="remove_tag")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Привет! Выбери действие:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Привет! Я тут, чтобы помогать.")

async def group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений в группе: отвечаем только на сообщения бота"""
    if update.message.reply_to_message and update.message.reply_to_message.from_user.is_bot:
        text = update.message.text.strip()
        results = []
        for city, tags in CITIES.items():
            for tag in tags:
                if (MATCH_CASE_INSENSITIVE and tag.lower() in text.lower()) or (not MATCH_CASE_INSENSITIVE and tag in text):
                    results.append(f"{tag}, #{city}")
        if results:
            await update.message.reply_text(", ".join(results))

async def personal_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка личных сообщений для управления тегами и городами"""
    chat_id = update.effective_chat.id
    if chat_id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет прав для управления ботом.")
        return
    await update.message.reply_text(
        "Используй кнопки /start для управления городами и тегами."
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "add_city":
        await query.edit_message_text("Напиши название нового города в формате:\n`Город`")
        context.user_data["action"] = "add_city"
    elif data == "remove_city":
        await query.edit_message_text("Напиши название города, который нужно удалить:")
        context.user_data["action"] = "remove_city"
    elif data == "add_tag":
        await query.edit_message_text("Напиши в формате `Город, @тег` чтобы добавить:")
        context.user_data["action"] = "add_tag"
    elif data == "remove_tag":
        await query.edit_message_text("Напиши в формате `Город, @тег` чтобы удалить:")
        context.user_data["action"] = "remove_tag"

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текста после нажатия кнопки"""
    chat_id = update.effective_chat.id
    if chat_id not in ADMIN_IDS:
        return
    action = context.user_data.get("action")
    text = update.message.text.strip()
    if not action:
        return

    if action == "add_city":
        if text not in CITIES:
            CITIES[text] = []
            await update.message.reply_text(f"Город `{text}` добавлен!")
        else:
            await update.message.reply_text(f"Город `{text}` уже существует.")
    elif action == "remove_city":
        if text in CITIES:
            del CITIES[text]
            await update.message.reply_text(f"Город `{text}` удалён.")
        else:
            await update.message.reply_text(f"Город `{text}` не найден.")
    elif action == "add_tag":
        try:
            city, tag = [x.strip() for x in text.split(",", 1)]
            if city not in CITIES:
                CITIES[city] = []
            if tag not in CITIES[city]:
                CITIES[city].append(tag)
                await update.message.reply_text(f"Тег `{tag}` добавлен к городу `{city}`.")
            else:
                await update.message.reply_text(f"Тег `{tag}` уже существует для `{city}`.")
        except ValueError:
            await update.message.reply_text("Ошибка формата. Используй: `Город, @тег`")
    elif action == "remove_tag":
        try:
            city, tag = [x.strip() for x in text.split(",", 1)]
            if city in CITIES and tag in CITIES[city]:
                CITIES[city].remove(tag)
                await update.message.reply_text(f"Тег `{tag}` удалён из города `{city}`.")
            else:
                await update.message.reply_text(f"Тег `{tag}` для города `{city}` не найден.")
        except ValueError:
            await update.message.reply_text("Ошибка формата. Используй: `Город, @тег`")

    # Сохраняем изменения в config.json
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump({**config, "cities": CITIES}, f, ensure_ascii=False, indent=2)

    context.user_data["action"] = None

# ---------- Основная функция запуска ----------
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT, personal_message))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT, handle_text))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.ChatType.PRIVATE, group_message))
    app.add_handler(CallbackQueryHandler(button))

    # Запуск Webhook
    PORT = 8000
    WEBHOOK_URL = f"https://city-tags-bot.onrender.com/{BOT_TOKEN}"

    logger.info(f"🚀 Запуск на порту {PORT}, webhook {WEBHOOK_URL}")
    await app.initialize()
    await app.bot.set_webhook(WEBHOOK_URL)
    await app.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_path=f"/{BOT_TOKEN}"
    )
    await app.updater.idle()

if __name__ == "__main__":
    asyncio.run(main())

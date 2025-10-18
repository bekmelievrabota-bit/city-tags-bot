import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка конфигурации
with open("config.json", encoding="utf-8") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
ALLOWED_CHAT_IDS = config["allowed_chat_ids"]
MATCH_CASE_INSENSITIVE = config.get("match_case_insensitive", True)
CITIES = config.get("cities", {})

# --- Хелперы для работы с тегами ---
def save_config():
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def find_matches(text: str):
    results = []
    for city, tags in CITIES.items():
        for tag in tags:
            if MATCH_CASE_INSENSITIVE:
                if tag.lower() in text.lower():
                    results.append((tag, city))
            else:
                if tag in text:
                    results.append((tag, city))
    return results

# --- Основной хендлер для сообщений в группах ---
async def group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id not in ALLOWED_CHAT_IDS:
        return

    message = update.effective_message
    # Проверяем, что это сообщение бота
    if message.from_user.is_bot:
        matches = find_matches(message.text or "")
        if matches:
            response = ", ".join([tag for tag, city in matches]) + " | " + ", ".join(set([city for tag, city in matches]))
            await message.reply_text(f"Ответ отправлен: {response}")
            logger.info(f"Ответ отправлен: {response}")

# --- Работа с личкой (добавление/удаление тегов и городов) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != update.effective_user.id:
        return  # только админ
    keyboard = [
        [InlineKeyboardButton("Добавить город/тег", callback_data="add")],
        [InlineKeyboardButton("Удалить город/тег", callback_data="remove")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "add":
        await query.edit_message_text("Отправьте сообщение в формате: Город:тег1,тег2")
    elif data == "remove":
        await query.edit_message_text("Отправьте сообщение в формате: Город:тег1,тег2 для удаления")

async def personal_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != update.effective_user.id:
        return  # только админ

    text = update.message.text.strip()
    if ":" not in text:
        await update.message.reply_text("Неверный формат. Используйте Город:тег1,тег2")
        return

    city, tags_str = text.split(":", 1)
    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
    if not tags:
        await update.message.reply_text("Не найдено тегов для добавления/удаления")
        return

    # Определяем действие по последнему выбранному callback_data
    last_action = context.user_data.get("last_action", "add")
    if last_action == "add":
        if city not in CITIES:
            CITIES[city] = []
        for tag in tags:
            if tag not in CITIES[city]:
                CITIES[city].append(tag)
        save_config()
        await update.message.reply_text(f"Теги добавлены для города {city}: {tags}")
    elif last_action == "remove":
        if city in CITIES:
            for tag in tags:
                if tag in CITIES[city]:
                    CITIES[city].remove(tag)
            save_config()
            await update.message.reply_text(f"Теги удалены для города {city}: {tags}")

# --- Основная функция запуска ---
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Групповые сообщения
    app.add_handler(MessageHandler(filters.ALL & ~filters.ChatType.PRIVATE, group_message))

    # Личные сообщения и кнопки
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE, personal_message))

    # Запуск Webhook
    PORT = 8000
    WEBHOOK_URL = f"https://city-tags-bot.onrender.com/{BOT_TOKEN}"
    logger.info(f"🚀 Запуск на порту {PORT}, webhook {WEBHOOK_URL}")
    await app.bot.set_webhook(WEBHOOK_URL)
    await app.start()
    await app.updater.start_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_path=f"/{BOT_TOKEN}"
    )
    await app.updater.idle()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

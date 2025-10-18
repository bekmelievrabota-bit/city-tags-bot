import json
import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from httpx import AsyncClient

# ==============================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ==============================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ==============================
# ЗАГРУЗКА КОНФИГА
# ==============================
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
ALLOWED_CHAT_IDS = config["allowed_chat_ids"]
CITIES = config["cities"]
MATCH_CASE_INSENSITIVE = config.get("match_case_insensitive", True)

# ==============================
# ОБРАБОТЧИК КОМАНД
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"/start от {update.effective_user.id} в чате {update.effective_chat.id}")
    await update.message.reply_text("✅ Бот запущен и готов к работе!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ Доступные команды:\n/start — проверить, что бот работает\n/help — список команд")

# ==============================
# ОСНОВНОЙ ОБРАБОТЧИК СООБЩЕНИЙ
# ==============================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user = update.effective_user.username or update.effective_user.first_name
    text = update.message.text.strip()

    # Проверяем, что чат разрешён
    if chat_id not in ALLOWED_CHAT_IDS:
        logger.warning(f"⚠️ Сообщение из неразрешённого чата: {chat_id}")
        return

    logger.info(f"📩 Сообщение от @{user} ({chat_id}): {text}")

    # Ищем город в тексте
    found_city = None
    for city in CITIES.keys():
        if MATCH_CASE_INSENSITIVE:
            if city.lower() in text.lower():
                found_city = city
                break
        else:
            if city in text:
                found_city = city
                break

    if not found_city:
        logger.info("❌ Город не найден в сообщении.")
        return

    # Формируем ответ
    tags = CITIES[found_city]
    hashtag = f"#{found_city.replace(' ', '')}"
    mention = " ".join(tags)
    response = f"{mention}, {hashtag}"

    await update.message.reply_text(response)
    logger.info(f"✅ Ответ отправлен: {response}")

# ==============================
# ПРОВЕРКА / УСТАНОВКА WEBHOOK
# ==============================
async def setup_webhook(application):
    webhook_url = f"https://city-tags-bot.onrender.com/{BOT_TOKEN}"
    logger.info(f"🔗 Установка Webhook: {webhook_url}")
    async with AsyncClient() as client:
        await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
            params={"url": webhook_url},
        )
    logger.info("✅ Webhook успешно установлен!")

# ==============================
# ОСНОВНАЯ ФУНКЦИЯ
# ==============================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем Webhook
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"🚀 Запуск на порту {port}")
    app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path=BOT_TOKEN,
        webhook_url=f"https://city-tags-bot.onrender.com/{BOT_TOKEN}",
        on_startup=[setup_webhook],
    )

if __name__ == "__main__":
    main()

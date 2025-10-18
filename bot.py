import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ==================== НАСТРОЙКИ ====================

TOKEN = os.getenv("BOT_TOKEN")  # токен из Render env vars
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL", "").strip()  # Render сам подставит свой домен
ADMIN_ID = 123456789  # ТВОЙ Telegram ID (замени!)

CONFIG_FILE = "config.txt"  # файл с городами и тегами

# ==================== ЛОГИ ====================

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== ДАННЫЕ ====================

def load_config():
    tags, cities = {}, []
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("city:"):
                    cities.append(line.split(":", 1)[1].strip().lower())
                elif line.startswith("tag:"):
                    parts = line.strip().split(":", 2)
                    if len(parts) == 3:
                        tags[parts[1].lower()] = parts[2]
    return tags, cities

def save_config(tags, cities):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        for city in cities:
            f.write(f"city:{city}\n")
        for k, v in tags.items():
            f.write(f"tag:{k}:{v}\n")

tags, cities = load_config()

# ==================== КОМАНДЫ ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Бот запущен и готов к работе!")

async def add_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 У тебя нет прав.")
    if not context.args:
        return await update.message.reply_text("Используй: /add_city Москва")
    city = " ".join(context.args).lower()
    if city in cities:
        return await update.message.reply_text("⚠️ Город уже есть.")
    cities.append(city)
    save_config(tags, cities)
    await update.message.reply_text(f"✅ Город '{city}' добавлен.")

async def del_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 У тебя нет прав.")
    if not context.args:
        return await update.message.reply_text("Используй: /del_city Москва")
    city = " ".join(context.args).lower()
    if city not in cities:
        return await update.message.reply_text("⚠️ Такого города нет.")
    cities.remove(city)
    save_config(tags, cities)
    await update.message.reply_text(f"🗑 Город '{city}' удалён.")

async def add_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 У тебя нет прав.")
    if len(context.args) < 2:
        return await update.message.reply_text("Используй: /add_tag имя @тег")
    name = context.args[0].lower()
    tag = context.args[1]
    tags[name] = tag
    save_config(tags, cities)
    await update.message.reply_text(f"✅ Тег '{name}' добавлен: {tag}")

async def del_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("🚫 У тебя нет прав.")
    if not context.args:
        return await update.message.reply_text("Используй: /del_tag имя")
    name = context.args[0].lower()
    if name not in tags:
        return await update.message.reply_text("⚠️ Такого тега нет.")
    del tags[name]
    save_config(tags, cities)
    await update.message.reply_text(f"🗑 Тег '{name}' удалён.")

# ==================== ОСНОВНАЯ ЛОГИКА ====================

async def process_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    found_city = next((c for c in cities if c in text), None)
    found_tag = next((t for t in tags if t in text), None)

    if found_city and found_tag:
        reply = f"{tags[found_tag]}, #{found_city.replace(' ', '_')}"
        await update.message.reply_text(reply, reply_to_message_id=update.message.message_id)
        logger.info(f"Ответ: {reply}")
    else:
        logger.info(f"Сообщение без совпадений: {text}")

# ==================== ЗАПУСК ====================

async def main():
    logger.info("🚀 Запуск Telegram-бота...")

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_city", add_city))
    app.add_handler(CommandHandler("del_city", del_city))
    app.add_handler(CommandHandler("add_tag", add_tag))
    app.add_handler(CommandHandler("del_tag", del_tag))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_message))

    port = int(os.environ.get("PORT", 8080))
    if WEBHOOK_URL:
        logger.info(f"🌐 Устанавливаю webhook: {WEBHOOK_URL}")
        try:
            await app.bot.set_webhook(WEBHOOK_URL)
            await app.run_webhook(listen="0.0.0.0", port=port, webhook_url=WEBHOOK_URL)
        except Exception as e:
            logger.error(f"Ошибка webhook ({e}), перехожу на polling")
            await app.run_polling()
    else:
        logger.warning("⚠️ Не найден WEBHOOK_URL, запускаю polling")
        await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.get_event_loop().run_until_complete(main())

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ============ ЛОГИ ============
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ============ ЗАГРУЗКА КОНФИГА ============
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Ошибка загрузки config.json: {e}")
        return {}

def save_config(config):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения config.json: {e}")

config = load_config()
BOT_TOKEN = config.get("bot_token")
ADMIN_ID = config.get("admin_id")
ALLOWED_CHATS = config.get("allowed_chat_ids", [])
CITIES = config.get("cities", {})
MATCH_CASE_INSENSITIVE = config.get("match_case_insensitive", True)

# ============ ОСНОВНАЯ ЛОГИКА ============
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    chat_id = update.message.chat_id
    text = update.message.text.strip()

    if chat_id not in ALLOWED_CHATS:
        logging.info(f"Сообщение из неразрешенного чата: {chat_id}")
        return

    # Проверяем города
    for city, tags in CITIES.items():
        if (city.lower() in text.lower()) if MATCH_CASE_INSENSITIVE else (city in text):
            tag_str = ", ".join(tags)
            reply_text = f"{tag_str}, #{city.replace(' ', '_')}"
            await update.message.reply_text(reply_text, reply_to_message_id=update.message.message_id)
            logging.info(f"Ответ на город {city}: {reply_text}")
            return

async def add_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ У тебя нет прав на выполнение этой команды.")
        return

    try:
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("Используй формат: /addcity Город @тег1 @тег2 ...")
            return

        city = args[0]
        tags = args[1:]
        CITIES[city] = tags
        config["cities"] = CITIES
        save_config(config)
        await update.message.reply_text(f"✅ Добавлен город {city} с тегами {', '.join(tags)}")
        logging.info(f"Город добавлен: {city} -> {tags}")
    except Exception as e:
        logging.error(f"Ошибка при добавлении города: {e}")
        await update.message.reply_text("Ошибка при добавлении города.")

async def del_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ У тебя нет прав на выполнение этой команды.")
        return

    try:
        if not context.args:
            await update.message.reply_text("Используй формат: /delcity Город")
            return

        city = context.args[0]
        if city in CITIES:
            del CITIES[city]
            config["cities"] = CITIES
            save_config(config)
            await update.message.reply_text(f"🗑 Город {city} удалён.")
            logging.info(f"Город удалён: {city}")
        else:
            await update.message.reply_text("❌ Такого города нет в списке.")
    except Exception as e:
        logging.error(f"Ошибка при удалении города: {e}")
        await update.message.reply_text("Ошибка при удалении города.")

# ============ СЕРВЕР ДЛЯ ВЕБХУКА ============
class SimpleWebhookServer(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers["Content-Length"])
        body = self.rfile.read(content_length)
        try:
            update = Update.de_json(json.loads(body.decode("utf-8")), app.bot)
            app.update_queue.put_nowait(update)
            self.send_response(200)
            self.end_headers()
        except Exception as e:
            logging.error(f"Ошибка при обработке вебхука: {e}")
            self.send_response(500)
            self.end_headers()

# ============ ЗАПУСК ============
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CommandHandler("addcity", add_city))
app.add_handler(CommandHandler("delcity", del_city))

PORT = int(os.environ.get("PORT", "8080"))
WEBHOOK_URL = f"https://{os.environ.get('RENDER_EXTERNAL_URL', 'example.com')}/webhook"

async def set_webhook():
    await app.bot.set_webhook(url=WEBHOOK_URL)
    logging.info(f"✅ Вебхук установлен: {WEBHOOK_URL}")

if __name__ == '__main__':
    import asyncio

    async def main():
        await set_webhook()
        server = HTTPServer(("0.0.0.0", PORT), SimpleWebhookServer)
        logging.info(f"🚀 Бот запущен и слушает порт {PORT}")
        server.serve_forever()

    asyncio.run(main())

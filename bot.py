import json
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Настройка логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Загрузка конфига
CONFIG_FILE = 'config.json'
with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
    config = json.load(f)

BOT_TOKEN = config['bot_token']
ALLOWED_CHAT_IDS = config['allowed_chat_ids']
CITIES = config['cities']
MATCH_CASE_INSENSITIVE = config.get('match_case_insensitive', True)
ADMIN_IDS = [6742361886]  # Твой Telegram ID

# Сохраняем конфиг
def save_config():
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# Проверка администратора
def is_admin(user_id: int):
    return user_id in ADMIN_IDS

# Добавление/удаление городов и тегов
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    text = update.message.text.strip()
    chat_id = update.message.chat_id

    # Команды добавления
    if text.startswith('/add_city '):
        parts = text.split(' ', 2)
        if len(parts) < 3:
            await update.message.reply_text("Используй /add_city <Город> <@тег>")
            return
        city, tag = parts[1], parts[2]
        if city not in CITIES:
            CITIES[city] = []
        if tag not in CITIES[city]:
            CITIES[city].append(tag)
        save_config()
        await update.message.reply_text(f"Добавлен {tag} в город {city}")
        return

    if text.startswith('/remove_city '):
        parts = text.split(' ', 2)
        if len(parts) < 3:
            await update.message.reply_text("Используй /remove_city <Город> <@тег>")
            return
        city, tag = parts[1], parts[2]
        if city in CITIES and tag in CITIES[city]:
            CITIES[city].remove(tag)
            if not CITIES[city]:
                del CITIES[city]
            save_config()
            await update.message.reply_text(f"Удален {tag} из города {city}")
        else:
            await update.message.reply_text("Такого города или тега нет")
        return

# Автоответ на отклики
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id not in ALLOWED_CHAT_IDS:
        return

    text = update.message.text
    # Проверка на соответствие городам
    for city, tags in CITIES.items():
        if (text.lower() if MATCH_CASE_INSENSITIVE else text) == (city.lower() if MATCH_CASE_INSENSITIVE else city):
            reply_text = ', '.join(tags) + f", #{city}"
            await update.message.reply_text(reply_text, reply_to_message_id=update.message.message_id)
            return

async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Обработчики
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_admin_message))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_message))

    # Запуск webhook
    PORT = 8000
    URL = f"https://city-tags-bot.onrender.com/{BOT_TOKEN}"
    await app.initialize()
    await app.start()
    await app.bot.set_webhook(URL)
    logging.info(f"🚀 Бот запущен на webhook: {URL}")

    await asyncio.Event().wait()  # держим приложение живым

if name == '__main__':
    if __name__ == '__main__':
    app.run_polling()
asyncio.run(main())
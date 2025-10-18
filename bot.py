import json
import logging
import os
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes,
    CommandHandler, MessageHandler, filters,
    CallbackQueryHandler
)

# ====== Логирование ======
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====== Конфигурация ======
CONFIG_PATH = Path(__file__).parent / "config.json"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

config = load_config()
BOT_TOKEN = config["bot_token"]
ALLOWED_CHAT_IDS = config["allowed_chat_ids"]
CITIES = config["cities"]
MATCH_CASE_INSENSITIVE = config.get("match_case_insensitive", True)
ADMIN_IDS = [6742361886]  # твой ID для управления

# ====== Вспомогательные функции ======
def normalize(text: str):
    return text.lower() if MATCH_CASE_INSENSITIVE else text

# ====== Команды ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я городской бот.\n"
        "Если вы админ, используйте кнопки для управления городами и тегами."
    )
    if update.effective_user.id in ADMIN_IDS:
        await show_admin_menu(update, context)

async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Добавить город", callback_data="admin:add_city")],
        [InlineKeyboardButton("Удалить город", callback_data="admin:remove_city")],
        [InlineKeyboardButton("Добавить тег", callback_data="admin:add_tag")],
        [InlineKeyboardButton("Удалить тег", callback_data="admin:remove_tag")]
    ]
    await update.message.reply_text(
        "Меню админа:", reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ====== Callback для кнопок ======
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if user_id not in ADMIN_IDS:
        await query.edit_message_text("❌ У вас нет доступа к этой функции.")
        return

    # ===== Управление городами =====
    if data == "admin:add_city":
        await query.edit_message_text("Отправьте название нового города сообщением.")
        context.user_data["action"] = "add_city"
        return
    if data == "admin:remove_city":
        keyboard = [
            [InlineKeyboardButton(name, callback_data=f"remove_city:{name}")]
            for name in CITIES.keys()
        ]
        await query.edit_message_text("Выберите город для удаления:", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    if data.startswith("remove_city:"):
        city = data.split(":", 1)[1]
        if city in CITIES:
            del CITIES[city]
            save_config(config)
            await query.edit_message_text(f"✅ Город '{city}' удалён!")
        return

    # ===== Управление тегами =====
    if data == "admin:add_tag":
        await query.edit_message_text("Отправьте сообщение в формате: <город> <тег>")
        context.user_data["action"] = "add_tag"
        return
    if data == "admin:remove_tag":
        await query.edit_message_text("Отправьте сообщение в формате: <город> <тег> для удаления")
        context.user_data["action"] = "remove_tag"
        return

# ====== Обработчик сообщений админа ======
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return

    text = update.message.text.strip()
    action = context.user_data.get("action")

    if action == "add_city":
        if text in CITIES:
            await update.message.reply_text("Такой город уже существует.")
        else:
            CITIES[text] = []
            save_config(config)
            await update.message.reply_text(f"✅ Город '{text}' добавлен!")
        context.user_data["action"] = None
        return

    if action in ["add_tag", "remove_tag"]:
        parts = text.split(maxsplit=1)
        if len(parts) != 2:
            await update.message.reply_text("Ошибка формата. Используйте: <город> <тег>")
            return
        city, tag = parts
        if city not in CITIES:
            await update.message.reply_text("Такого города нет.")
            return

        if action == "add_tag":
            if tag in CITIES[city]:
                await update.message.reply_text("Такой тег уже есть.")
            else:
                CITIES[city].append(tag)
                save_config(config)
                await update.message.reply_text(f"✅ Тег '{tag}' добавлен в город '{city}'!")
        elif action == "remove_tag":
            if tag not in CITIES[city]:
                await update.message.reply_text("Такого тега нет.")
            else:
                CITIES[city].remove(tag)
                save_config(config)
                await update.message.reply_text(f"✅ Тег '{tag}' удалён из города '{city}'!")
        context.user_data["action"] = None

# ====== Обработчик сообщений в группах ======
async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id not in ALLOWED_CHAT_IDS:
        return
    text_norm = normalize(update.message.text)
    for city, tags in CITIES.items():
        for tag in tags:
            if normalize(tag) in text_norm:
                await update.message.reply_text(f"{tag}, #{city}")

# ====== Основная функция ======
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))

    # Callback кнопки
    app.add_handler(CallbackQueryHandler(button_callback))

    # Сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_group_message))

    # Webhook
    PORT = int(os.environ.get("PORT", 8000))
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"https://city-tags-bot.onrender.com/{BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()

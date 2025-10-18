import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters
)

# ====== Настройка логирования ======
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ====== Конфиг ======
CONFIG_PATH = "config.json"
with open(CONFIG_PATH, encoding="utf-8") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
ALLOWED_CHAT_IDS = config["allowed_chat_ids"]
CITIES = config["cities"]
MATCH_CASE_INSENSITIVE = config.get("match_case_insensitive", True)

# Админ
ADMIN_IDS = [6742361886]  # твой ID

# ====== Кнопки для админа ======
def admin_menu():
    keyboard = [
        [InlineKeyboardButton("Добавить город", callback_data="add_city")],
        [InlineKeyboardButton("Удалить город", callback_data="remove_city")],
        [InlineKeyboardButton("Добавить тег", callback_data="add_tag")],
        [InlineKeyboardButton("Удалить тег", callback_data="remove_tag")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ====== Команда /admin ======
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("У вас нет доступа к этим командам.")
        return
    await update.message.reply_text("Выберите действие:", reply_markup=admin_menu())

# ====== Обработчик кнопок ======
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in ADMIN_IDS:
        await query.edit_message_text("У вас нет доступа к этим действиям.")
        return

    action = query.data
    if action == "add_city":
        await query.edit_message_text("Напишите название нового города:")
        context.user_data["next_action"] = "add_city"
    elif action == "remove_city":
        await query.edit_message_text("Напишите название города для удаления:")
        context.user_data["next_action"] = "remove_city"
    elif action == "add_tag":
        await query.edit_message_text("Напишите город и тег через запятую (Москва,@w333rd):")
        context.user_data["next_action"] = "add_tag"
    elif action == "remove_tag":
        await query.edit_message_text("Напишите город и тег для удаления через запятую:")
        context.user_data["next_action"] = "remove_tag"

# ====== Обработчик сообщений от админа ======
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return

    action = context.user_data.get("next_action")
    if not action:
        return

    text = update.message.text.strip()

    if action == "add_city":
        if text not in CITIES:
            CITIES[text] = []
            await update.message.reply_text(f"Город {text} добавлен.")
    elif action == "remove_city":
        if text in CITIES:
            del CITIES[text]
            await update.message.reply_text(f"Город {text} удалён.")
    elif action == "add_tag":
        try:
            city, tag = [x.strip() for x in text.split(",")]
            if city in CITIES:
                if tag not in CITIES[city]:
                    CITIES[city].append(tag)
                    await update.message.reply_text(f"Тег {tag} добавлен для города {city}.")
                else:
                    await update.message.reply_text(f"Тег {tag} уже есть для города {city}.")
            else:
                await update.message.reply_text(f"Город {city} не найден.")
        except:
            await update.message.reply_text("Неправильный формат. Используйте: Москва,@w333rd")
    elif action == "remove_tag":
        try:
            city, tag = [x.strip() for x in text.split(",")]
            if city in CITIES and tag in CITIES[city]:
                CITIES[city].remove(tag)
                await update.message.reply_text(f"Тег {tag} удалён из города {city}.")
            else:
                await update.message.reply_text("Город или тег не найден.")
        except:
            await update.message.reply_text("Неправильный формат. Используйте: Москва,@w333rd")

    # Сохраняем изменения в config.json
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    context.user_data["next_action"] = None

# ====== Основной обработчик сообщений в группах ======
async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    chat_id = message.chat.id
    # Отвечаем только в разрешённых чатах
    if chat_id not in ALLOWED_CHAT_IDS:
        return

    # Только на сообщения бота
    if not message.from_user or not message.from_user.is_bot:
        return

    text = message.text
    if not text:
        return

    results = []
    for city, tags in CITIES.items():
        for tag in tags:
            if MATCH_CASE_INSENSITIVE:
                if tag.lower() in text.lower():
                    results.append(f"{tag}, #{city}")
            else:
                if tag in text:
                    results.append(f"{tag}, #{city}")

    if results:
        await message.reply_text("\n".join(results))

# ====== Запуск бота ======
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Админ
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_admin_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Группы
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, handle_group_message))

    logger.info("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()

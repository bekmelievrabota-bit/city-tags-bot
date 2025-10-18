import json
import logging
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ---------------- ЛОГИ ---------------- #
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- КОНФИГ ---------------- #
CONFIG_PATH = "config.json"

def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки config.json: {e}")
        return {}

config = load_config()
BOT_TOKEN = config.get("bot_token")
ALLOWED_CHAT_IDS = config.get("allowed_chat_ids", [])
CITIES = config.get("cities", {})
MATCH_CASE_INSENSITIVE = config.get("match_case_insensitive", True)

ADMIN_ID = 6742361886  # твой ID

# ---------------- СЕРДЦЕ БОТА ---------------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для откликов.\n"
        "Доступные команды:\n"
        "/add_city — добавить город\n"
        "/remove_city — удалить город\n"
        "/add_tag — добавить тег\n"
        "/remove_tag — удалить тег"
    )

# --- Админ-проверка ---
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# --- Кнопки ---
def main_menu():
    keyboard = [
        [InlineKeyboardButton("➕ Добавить город", callback_data="add_city")],
        [InlineKeyboardButton("➖ Удалить город", callback_data="remove_city")],
        [InlineKeyboardButton("➕ Добавить тег", callback_data="add_tag")],
        [InlineKeyboardButton("➖ Удалить тег", callback_data="remove_tag")],
    ]
    return InlineKeyboardMarkup(keyboard)

# --- Callback от кнопок ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.edit_message_text("⛔ Только админ может управлять данными.")
        return

    action = query.data
    context.user_data["action"] = action
    await query.edit_message_text(f"Введите данные для {action.replace('_', ' ')}:")

# --- Обновление конфигурации ---
def save_config():
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

# --- Обработка добавления/удаления ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat_id = message.chat_id
    text = message.text.strip()

    if chat_id not in ALLOWED_CHAT_IDS and update.effective_user.id != ADMIN_ID:
        return

    # Режим админки
    action = context.user_data.get("action")
    if action:
        if not is_admin(update.effective_user.id):
            await message.reply_text("⛔ У тебя нет прав.")
            return

        if action == "add_city":
            parts = text.split(maxsplit=1)
            if len(parts) == 2:
                city, tags_str = parts
                tags = tags_str.split()
                config["cities"][city] = tags
                save_config()
                await message.reply_text(f"✅ Город {city} добавлен с тегами: {', '.join(tags)}")
            else:
                await message.reply_text("⚠ Формат: Город @тег1 @тег2")
        elif action == "remove_city":
            if text in config["cities"]:
                del config["cities"][text]
                save_config()
                await message.reply_text(f"🗑 Город {text} удалён.")
            else:
                await message.reply_text("❌ Такого города нет.")
        elif action == "add_tag":
            found = False
            for city, tags in config["cities"].items():
                if city.lower() in text.lower():
                    tag = text.split()[-1]
                    if tag not in tags:
                        tags.append(tag)
                        save_config()
                        await message.reply_text(f"✅ Тег {tag} добавлен в город {city}")
                    else:
                        await message.reply_text("⚠ Такой тег уже есть.")
                    found = True
                    break
            if not found:
                await message.reply_text("❌ Город не найден в конфиге.")
        elif action == "remove_tag":
            found = False
            for city, tags in config["cities"].items():
                if city.lower() in text.lower():
                    tag = text.split()[-1]
                    if tag in tags:
                        tags.remove(tag)
                        save_config()
                        await message.reply_text(f"🗑 Тег {tag} удалён из города {city}")
                    else:
                        await message.reply_text("❌ Тег не найден.")
                    found = True
                    break
            if not found:
                await message.reply_text("❌ Город не найден в конфиге.")
        context.user_data["action"] = None
        return

    # Основная логика — отклики
    lowered = text.lower() if MATCH_CASE_INSENSITIVE else text
    if any(word in lowered for word in ["отправил отклик", "откликнулся", "отклик"]):
        for city, tags in config["cities"].items():
            if city.lower() in lowered:
                mention_str = " ".join(tags)
                await message.reply_text(
                    f"{mention_str} #{city.replace(' ', '_')}",
                    reply_to_message_id=message.message_id
                )
                logger.info(f"Ответ для города {city}: {mention_str}")
                return
        await message.reply_text("⚠ Не удалось определить город. Проверь сообщение.")

# --- Команды ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ У тебя нет прав.")
        return
    await update.message.reply_text("Панель управления:", reply_markup=main_menu())

# ---------------- ЗАПУСК ---------------- #
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("panel", admin_panel))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    PORT = int(os.environ.get("PORT", 8443))
    WEBHOOK_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}"  # Render генерирует домен

    async def run():
        if WEBHOOK_URL and "render" in WEBHOOK_URL:
            try:
                logger.info(f"Устанавливаю webhook: {WEBHOOK_URL}")
                await app.bot.set_webhook(url=f"{WEBHOOK_URL}")
                await app.run_webhook(
                    listen="0.0.0.0",
                    port=PORT,
                    url_path="",
                    webhook_url=WEBHOOK_URL
                )
            except Exception as e:
                logger.error(f"Ошибка вебхука: {e}, включаю polling...")
                await app.run_polling()
        else:
            logger.warning("Render-домен не найден, запускаю polling.")
            await app.run_polling()

    import asyncio
    asyncio.run(run())

# bot.py
import os
import json
import logging
import re
from typing import Dict, List

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ====== ЛОГИРОВАНИЕ ======
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ====== КОНФИГ ======
CONFIG_FILE = "config.json"
if not os.path.exists(CONFIG_FILE):
    logger.error(f"Конфиг {CONFIG_FILE} не найден")
    raise SystemExit(1)

with open(CONFIG_FILE, encoding="utf-8") as f:
    config = json.load(f)

BOT_TOKEN: str = config["bot_token"]
ALLOWED_CHAT_IDS = set(config.get("allowed_chat_ids", []))  # сюда включается твой личный id
CITIES: Dict[str, List[str]] = config.get("cities", {})
MATCH_CASE_INSENSITIVE: bool = config.get("match_case_insensitive", True)

# Подготовка регулярных выражений для поиска
CITY_PATTERNS = {
    city: re.compile(re.escape(city), re.IGNORECASE if MATCH_CASE_INSENSITIVE else 0)
    for city in CITIES
}

# ====== СТАНЫ ДЛЯ ConversationHandler ======
CHOOSING_ACTION, WAITING_FOR_CITY_NAME, WAITING_FOR_TAG_TEXT, WAITING_FOR_REMOVE_NAME = range(4)

# ====== УТИЛИТЫ ======
def save_config():
    """Сохраняем config обратно в файл"""
    global CITIES
    config["cities"] = CITIES
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    logger.info("config.json обновлён")

def is_admin(user_id: int) -> bool:
    return user_id in ALLOWED_CHAT_IDS

# ====== ОСНОВНАЯ ЛОГИКА ОБРАБОТКИ ОТКЛИКОВ (без изменений) ======
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения: ищет города и отвечает тегами/хэштегами."""
    if update.effective_message is None:
        return

    chat_id = update.effective_chat.id
    # позволяем сообщения только из разрешённых чатов (группы/личка)
    if ALLOWED_CHAT_IDS and (chat_id not in ALLOWED_CHAT_IDS and update.effective_user.id not in ALLOWED_CHAT_IDS):
        # если список ALLOWED_CHAT_IDS непуст — игнорируем чужие
        return

    text = update.effective_message.text or ""
    if not text.strip():
        return

    tagged_users = []
    hashtags = []

    # обновляем CITY_PATTERNS если CITIES изменился в рантайме
    for city, tags in CITIES.items():
        pat = re.compile(re.escape(city), re.IGNORECASE if MATCH_CASE_INSENSITIVE else 0)
        if pat.search(text):
            hashtags.append(f"#{city}")
            # теги ответственных могут быть список
            tagged_users.extend(tags)

    if tagged_users:
        # формируем ответ: упоминания через запятую, затем хештеги
        tagged_unique = ", ".join(dict.fromkeys(tagged_users))  # убираем дубликаты, сохраняя порядок
        hashtags_text = " ".join(hashtags)
        response = f"{tagged_unique}, {hashtags_text}"
        # отвечаем на сообщение (reply)
        await update.message.reply_text(response)
        logger.info(f"Ответ отправлен: {response}")

# ====== МЕНЮ: кнопки для управления городами/тегами ======
async def menu_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показываем меню с кнопками — только для админов."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет доступа к меню управления.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("➕ Добавить город", callback_data="add_city")],
        [InlineKeyboardButton("➕ Добавить тег к городу", callback_data="add_tag")],
        [InlineKeyboardButton("➖ Удалить город", callback_data="remove_city")],
        [InlineKeyboardButton("➖ Удалить тег", callback_data="remove_tag")],
    ]
    await update.message.reply_text("Выберите действие:", reply_markup=InlineKeyboardMarkup(keyboard))
    return CHOOSING_ACTION

async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий меню (CallbackQuery)."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа.")
        return ConversationHandler.END

    data = query.data
    if data == "add_city":
        await query.edit_message_text("Введите название города, который хотите добавить (пример: Калуга):")
        return WAITING_FOR_CITY_NAME

    if data == "add_tag":
        # попросим ввести "Город|@тег" для простоты
        await query.edit_message_text("Введите город и тег через |  в формате: Город|@tag (пример: Калуга|@rabot_v_Kaluge)")
        return WAITING_FOR_TAG_TEXT

    if data == "remove_city":
        # кнопки со списком текущих городов (если много — отображаем текстовый запрос)
        if not CITIES:
            await query.edit_message_text("Список городов пуст.")
            return ConversationHandler.END
        # если городов немного — показать кнопки
        if len(CITIES) <= 10:
            keyboard = [[InlineKeyboardButton(city, callback_data=f"do_remove_city::{city}")] for city in CITIES.keys()]
            await query.edit_message_text("Выберите город для удаления:", reply_markup=InlineKeyboardMarkup(keyboard))
            return CHOOSING_ACTION
        else:
            await query.edit_message_text("Введите название города для удаления:")
            return WAITING_FOR_REMOVE_NAME

    if data == "remove_tag":
        await query.edit_message_text("Введите тег для удаления (например: @rabot_v_Kaluge):")
        return WAITING_FOR_REMOVE_NAME

    # обработка кнопок удаления города вlined
    if data and data.startswith("do_remove_city::"):
        _, city_to_remove = data.split("::", 1)
        if city_to_remove in CITIES:
            del CITIES[city_to_remove]
            save_config()
            await query.edit_message_text(f"✅ Город {city_to_remove} удалён.")
        else:
            await query.edit_message_text("⚠️ Такой город не найден.")
        return ConversationHandler.END

    await query.edit_message_text("Неизвестная команда.")
    return ConversationHandler.END

async def text_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текст, введённый после выбора действия."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ У вас нет доступа.")
        return ConversationHandler.END

    state = context.user_data.get("state")
    text = (update.message.text or "").strip()
    if not text:
        await update.message.reply_text("Пустой ввод, отмена.")
        return ConversationHandler.END

    # Но! мы не полагаемся на context.user_data["state"] — так как у нас ConversationHandler
    # самостоятельно назначает состояния. Вместо этого определим текущий state по аргументу вызова.
    current_state = update.message.chat_data.get("menu_state") or context.user_data.get("menu_state")
    # однако проще: получаем state при помощи conversation handler: context.user_data['last_state']? 
    # (мы будем полагаться на возвращаемые состояния из callback'ов)

    # Определим поведение в зависимости от того, в каком состоянии находится Conversation:
    # В PTB ConversationHandler, текущий state передаётся вызовом соответствующего MessageHandler,
    # поэтому тут мы просто проверим text формата:
    # - Если text содержит '|' — это добавление тега (Город|@tag)
    if "|" in text:
        parts = text.split("|", 1)
        city_name = parts[0].strip()
        tag_text = parts[1].strip()
        if not city_name or not tag_text:
            await update.message.reply_text("Неверный формат. Пример: Калуга|@rabot_v_Kaluge")
            return ConversationHandler.END
        # Добавляем город если нет
        if city_name not in CITIES:
            CITIES[city_name] = []
        if tag_text not in CITIES[city_name]:
            CITIES[city_name].append(tag_text)
            save_config()
            await update.message.reply_text(f"✅ Тег {tag_text} добавлен для города {city_name}.")
        else:
            await update.message.reply_text("⚠️ Такой тег уже есть для этого города.")
        return ConversationHandler.END

    # Если ввели одиночное слово — это добавление/удаление города или удаление тега
    # Проверим, есть ли такой город — если нет, то добавим как новый город:
    if text in CITIES:
        await update.message.reply_text("⚠️ Такой город уже есть.")
        return ConversationHandler.END

    # Если сообщение выглядит как тег (начинается с @) — удаляем этот тег из всех городов (если есть)
    if text.startswith("@"):
        found = False
        for city, tags in CITIES.items():
            if text in tags:
                tags.remove(text)
                found = True
        if found:
            save_config()
            await update.message.reply_text(f"✅ Тег {text} удалён из конфигурации.")
        else:
            await update.message.reply_text("⚠️ Тег не найден.")
        return ConversationHandler.END

    # Иначе — добавляем город (если не было другого указания)
    CITIES[text] = CITIES.get(text, [])
    save_config()
    await update.message.reply_text(f"✅ Город {text} добавлен. Теперь вы можете добавить теги к нему через меню или вводом 'Город|@tag'.")
    return ConversationHandler.END

# ====== ПОМОЩНИК: обработчик callback удаления города (в состоянии CHOOSING_ACTION) ======
async def callback_removal_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("do_remove_city::"):
        _, city_name = data.split("::", 1)
        if city_name in CITIES:
            del CITIES[city_name]
            save_config()
            await query.edit_message_text(f"✅ Город {city_name} удалён.")
        else:
            await query.edit_message_text("⚠️ Такой город не найден.")
    return ConversationHandler.END

# ====== ФУНКЦИЯ MAIN: собираем Application и регистрируем обработчики ======
def main():
    # Webhook адрес Render (как у тебя раньше успешно сработало)
    PORT = int(os.environ.get("PORT", 8000))
    external_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    if external_host:
        WEBHOOK_URL = f"https://{external_host}/{BOT_TOKEN}"
    else:
        # fallback — если запускаешь локально, тебе потребуется свой URL или использовать polling
        WEBHOOK_URL = os.environ.get("WEBHOOK_URL", f"https://example.com/{BOT_TOKEN}")

    app = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler для меню (вход через /menu или /start_menu)
    menu_conv = ConversationHandler(
        entry_points=[CommandHandler("menu", menu_start), CommandHandler("start_menu", menu_start), CommandHandler("start", menu_start)],
        states={
            CHOOSING_ACTION: [
                CallbackQueryHandler(menu_callback_handler),
                CallbackQueryHandler(callback_removal_handler, pattern=r"^do_remove_city::"),
            ],
            WAITING_FOR_CITY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_input_handler)],
            WAITING_FOR_TAG_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_input_handler)],
            WAITING_FOR_REMOVE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, text_input_handler)],
        },
        fallbacks=[],
        per_message=False,  # стандартное поведение — callbackquery handler будет отслеживаться
        name="menu_conv",
        persistent=False,
    )

    # Регистрируем обработчики
    app.add_handler(menu_conv)

    # Ставим общий обработчик сообщений (важно: должен регистрироваться после разговорного, чтобы не перебивать)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Логирование и запуск webhook (как в твоём рабочем варианте)
    logger.info(f"🚀 Запуск на порту {PORT}, webhook {WEBHOOK_URL}")
    # url_path — токен, чтобы Telegram слал апдейты на /<token>
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=WEBHOOK_URL,
    )

if __name__ == "__main__":
    main()

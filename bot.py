# bot.py
import os
import json
import logging
import re
from pathlib import Path
from typing import Optional, List, Dict

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

# ------------------------
# Настройка логирования
# ------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ------------------------
# Конфиг
# ------------------------
CFG_PATH = Path("config.json")


def load_config() -> Dict:
    if not CFG_PATH.exists():
        logger.error("config.json не найден в рабочей директории.")
        raise SystemExit("config.json required")
    with CFG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg: Dict):
    with CFG_PATH.open("w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    logger.info("config.json сохранён.")


# ------------------------
# Поиск города в тексте
# ------------------------
def extract_city_structured(text: str) -> Optional[str]:
    """
    Ищет явную строку "Город: <город,...>" в теле сообщения.
    """
    m = re.search(r"Город[:\s\-–]*([^\n,\\/]+)", text, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def find_city_by_name(text: str, cities_list: List[str], ci=True) -> Optional[str]:
    txt = text.lower() if ci else text
    for c in cities_list:
        key = c.lower() if ci else c
        # \b может не срабатывать для кириллицы в некоторых краях, но обычно ок
        if re.search(rf"\b{re.escape(key)}\b", txt):
            return c
    return None


# ------------------------
# Business: формируем ответ (теги + хештег)
# ------------------------
def make_reply_for_city(city_key: str, cfg: Dict) -> Optional[str]:
    cities_map = cfg.get("cities", {})
    # ищем точный ключ в конфиге с учётом регистра
    matched_key = None
    for k in cities_map.keys():
        if k.lower() == city_key.lower():
            matched_key = k
            break
    if not matched_key:
        for k in cities_map.keys():
            if city_key.lower() in k.lower():
                matched_key = k
                break
    if not matched_key:
        return None
    users = cities_map.get(matched_key, [])
    if not users:
        return None
    mention_text = " ".join(users)
    hashtag = f"#{matched_key.replace(' ', '')}"
    return f"{mention_text}, {hashtag}"


# ------------------------
# Хэндлеры
# ------------------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Бот живой. Я слежу за откликами и буду упоминать ответственных по городам."
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — старт\n"
        "/help — помощь\n\n"
        "Админ-команды (только в личке для админов):\n"
        "/addcity <Город> <@user1,@user2,...> — добавить город\n"
        "/delcity <Город> — удалить город\n"
        "/listcities — показать карту город->теги\n"
    )


# Приват: управление картой городов (только для админов)
def is_admin(user_id: int, cfg: Dict) -> bool:
    # Если указан отдельный список admin_ids — используем его
    if cfg.get("admin_ids"):
        return user_id in cfg.get("admin_ids", [])
    # Иначе считаем положительные ID в allowed_chat_ids (личные) админами
    allowed = cfg.get("allowed_chat_ids", [])
    # часто group IDs negative or -100..., personal IDs positive — возьмём положительные
    admins_guess = [i for i in allowed if isinstance(i, int) and i > 0]
    return user_id in admins_guess


async def addcity_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = context.bot_data["cfg"]
    uid = update.effective_user.id
    if not is_admin(uid, cfg):
        await update.message.reply_text("Ты не админ — у тебя нет прав для этой команды.")
        return

    # Текст: /addcity Город @user1,@user2
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Использование: /addcity <Город> <@u1,@u2,...>")
        return
    city = args[0].strip()
    # остальные аргументы — можем объединить и разбить по запятым
    users_txt = " ".join(args[1:])
    # допустимо разделять запятыми или пробелами
    users = re.split(r"[,\s]+", users_txt.strip())
    users = [u for u in users if u]
    cfg.setdefault("cities", {})[city] = users
    save_config(cfg)
    await update.message.reply_text(f"Город добавлен/обновлён: {city} -> {users}")


async def delcity_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = context.bot_data["cfg"]
    uid = update.effective_user.id
    if not is_admin(uid, cfg):
        await update.message.reply_text("Ты не админ — у тебя нет прав для этой команды.")
        return
    if not context.args:
        await update.message.reply_text("Использование: /delcity <Город>")
        return
    city = context.args[0].strip()
    if city in cfg.get("cities", {}):
        cfg["cities"].pop(city)
        save_config(cfg)
        await update.message.reply_text(f"Город удалён: {city}")
    else:
        await update.message.reply_text("Город не найден в конфиге.")


async def listcities_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cfg = context.bot_data["cfg"]
    uid = update.effective_user.id
    if not is_admin(uid, cfg):
        await update.message.reply_text("Ты не админ — у тебя нет прав для этой команды.")
        return
    cities = cfg.get("cities", {})
    if not cities:
        await update.message.reply_text("Список городов пуст.")
        return
    lines = []
    for k, v in cities.items():
        lines.append(f"{k}: {' '.join(v)}")
    # Telegram limits message length, но это коротко
    await update.message.reply_text("\n".join(lines))


# Главный обработчик текстовых сообщений
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Нам нужен только текст
    if update.message is None or update.message.text is None:
        return

    cfg = context.bot_data["cfg"]
    allowed = cfg.get("allowed_chat_ids", [])
    chat_id = update.effective_chat.id

    # Проверяем разрешён ли этот чат вообще
    if allowed and chat_id not in allowed:
        logger.debug("Чат %s не в allowed_chat_ids — игнорирую.", chat_id)
        return

    text = update.message.text
    logger.info("Новое сообщение в %s: %s", chat_id, text[:120])

    # Нам нужна структура "отклик" — ищем город явным образом или по названию в списке
    city = extract_city_structured(text)
    if not city:
        city = find_city_by_name(text, list(cfg.get("cities", {}).keys()), cfg.get("match_case_insensitive", True))

    if not city:
        # ничего не понимаем — пропускаем
        logger.debug("Не нашли город в тексте.")
        return

    reply_text = make_reply_for_city(city, cfg)
    if not reply_text:
        logger.debug("Нет ответственных для найденного города '%s'.", city)
        return

    try:
        # Отвечаем как reply на текущее сообщение (так будет видно контекст)
        await update.message.reply_text(reply_text)
        logger.info("Ответ отправлен: %s", reply_text)
    except Exception as e:
        logger.exception("Не удалось отправить ответ: %s", e)


# ------------------------
# Запуск приложения (webhook)
# ------------------------
def build_app(cfg: Dict):
    token = cfg.get("bot_token")
    if not token:
        logger.error("bot_token отсутствует в config.json")
        raise SystemExit("bot_token required")

    app = ApplicationBuilder().token(token).build()
    app.bot_data["cfg"] = cfg

    # Команды
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("addcity", addcity_cmd))
    app.add_handler(CommandHandler("delcity", delcity_cmd))
    app.add_handler(CommandHandler("listcities", listcities_cmd))

    # Все текстовые сообщения (кроме команд)
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), on_message))
    return app


async def main():
    cfg = load_config()
    token = cfg["bot_token"]

    # Порт и URL (Render предоставляет RENDER_EXTERNAL_URL, порт в PORT)
    PORT = int(os.environ.get("PORT", os.environ.get("RENDER_PORT", 8000)))
    render_url = os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("WEBHOOK_BASE_URL")
    if not render_url:
        logger.warning(
            "Переменная окружения RENDER_EXTERNAL_URL не установлена. "
            "Нужно добавить вручную в Render: RENDER_EXTERNAL_URL = https://your-service.onrender.com"
        )

    app = build_app(cfg)

    # Сформируем webhook-url (используем путь с токеном, чтобы не открывать публичный endpoint)
    if render_url:
        webhook_url = f"{render_url.rstrip('/')}/{token}"
    else:
        # fallback (если не указан render_url — будет попытка установить webhook по токену, возможно не сработает)
        webhook_url = f"https://{os.environ.get('HOSTNAME','localhost')}/{token}"

    logger.info("Webhook URL: %s", webhook_url)
    # Запуск вебхука (параметры совместимы с python-telegram-bot[webhooks])
    try:
        # Для Render обычно подходят эти аргументы
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=token,  # путь, который telegram будет постить: https://host/<token>
            webhook_url=webhook_url,
        )
    except TypeError:
        # на случай различий API (более старые/новые версии) — пробуем альтернативный подход:
        logger.exception("run_webhook вызвал TypeError — пробую простой запуск")
        await app.initialize()
        await app.bot.set_webhook(webhook_url)
        logger.info("Webhook установлен вручную: %s", webhook_url)
        await app.start()
        await app.updater.start_webhook(listen="0.0.0.0", port=PORT, url_path=token)
        await app.updater.idle()


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановлено пользователем")

import logging
from telegram import Update, Chat
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)

# ======================
# Настройка логирования
# ======================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ======================
# Команды
# ======================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    logger.info(f"/start вызван в чате {chat_type} пользователем {update.effective_user.id}")
    await update.message.reply_text(
        "Привет! Я бот и теперь работаю в личке и в группах!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Список команд:\n"
        "/start - начать работу\n"
        "/help - показать это сообщение"
    )

# ======================
# Обработка текстовых сообщений
# ======================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    user_id = update.effective_user.id
    username = update.effective_user.username
    text = update.message.text

    # Логируем в консоль
    logger.info(f"Сообщение от {username} ({user_id}) в {chat_type}: {text}")

    # Ответ пользователю
    await update.message.reply_text(f"Вы написали: {text}")

# ======================
# Основная функция
# ======================
def main():
    token = "YOUR_BOT_TOKEN_HERE"
    app = ApplicationBuilder().token(token).build()

    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Обработчик всех текстовых сообщений в личке и группах
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & (
            filters.ChatType.PRIVATE | filters.ChatType.GROUP | filters.ChatType.SUPERGROUP
        ),
        handle_message
    ))

    # Запуск вебхука для Render
    app.run_webhook(
        listen="0.0.0.0",
        port=8000,
        webhook_url=f"https://city-tags-bot.onrender.com/{token}"
    )

if __name__ == "__main__":
    main()

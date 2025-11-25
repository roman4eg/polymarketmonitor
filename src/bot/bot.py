"""
Основний модуль Telegram бота
"""
import logging
import os
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from src.bot.handlers import (
    start_command,
    help_command,
    positions_command,
    handle_message,
    error_handler
)

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def create_bot(token: str) -> Application:
    """
    Створити та налаштувати бота

    Args:
        token: Telegram Bot API токен

    Returns:
        Налаштований Application бота
    """
    # Створюємо Application
    application = Application.builder().token(token).build()

    # Додаємо обробники команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("positions", positions_command))

    # Обробник текстових повідомлень
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Обробник помилок
    application.add_error_handler(error_handler)

    return application


def run_bot(token: str):
    """
    Запустити бота

    Args:
        token: Telegram Bot API токен
    """
    logger.info("Starting Polymarket Monitor Bot...")

    application = create_bot(token)

    logger.info("Bot is running! Press Ctrl+C to stop.")

    # Запускаємо бота (блокуючий виклик)
    application.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True
    )

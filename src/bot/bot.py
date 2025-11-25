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
    watchlist_command,
    add_wallet_command,
    remove_wallet_command,
    setfilter_command,
    handle_message,
    error_handler
)
from src.bot.monitor import PositionMonitor
from src.utils.database import Database

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

    # Команди watchlist
    application.add_handler(CommandHandler("watchlist", watchlist_command))
    application.add_handler(CommandHandler("add", add_wallet_command))
    application.add_handler(CommandHandler("remove", remove_wallet_command))
    application.add_handler(CommandHandler("setfilter", setfilter_command))

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

    # Створюємо базу даних та монітор
    db = Database()
    monitor = PositionMonitor(application, db, check_interval=10)

    # Callback для запуску монітора після ініціалізації
    async def post_init(app: Application) -> None:
        await monitor.start()
        logger.info("Position monitor started")

    # Callback для зупинки монітора
    async def post_stop(app: Application) -> None:
        await monitor.stop()
        logger.info("Position monitor stopped")

    # Додаємо callbacks
    application.post_init = post_init
    application.post_stop = post_stop

    logger.info("Bot is running! Press Ctrl+C to stop.")
    logger.info("Monitoring enabled - checking for new positions every 10 seconds")

    # Запускаємо бота (блокуючий виклик)
    application.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True
    )

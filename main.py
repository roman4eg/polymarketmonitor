"""
Точка входу для запуску бота
"""
import os
import sys
from dotenv import load_dotenv

from src.bot.bot import run_bot


def main():
    """Головна функція для запуску бота"""
    # Завантажуємо змінні середовища
    load_dotenv()

    # Отримуємо токен бота
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not bot_token:
        print("❌ Помилка: TELEGRAM_BOT_TOKEN не знайдено!")
        print("Створіть файл .env та додайте:")
        print("TELEGRAM_BOT_TOKEN=your_bot_token_here")
        sys.exit(1)

    # Запускаємо бота
    try:
        run_bot(bot_token)
    except KeyboardInterrupt:
        print("\n👋 Бот зупинено користувачем")
    except Exception as e:
        print(f"❌ Критична помилка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

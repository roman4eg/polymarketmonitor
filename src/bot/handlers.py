"""
Обробники команд та повідомлень для Telegram бота
"""
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import logging

from src.api.polymarket import PolymarketAPI, format_position
from src.utils.validators import is_valid_ethereum_address, normalize_address

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start"""
    welcome_message = """
👋 Привіт! Я бот для моніторингу ставок на Polymarket.

**Команди:**
/start - Показати це повідомлення
/help - Допомога
/positions <адреса_гаманця> - Показати активні позиції гаманця

**Як користуватися:**
1. Надішліть команду `/positions` з адресою Ethereum гаманця
2. Отримайте список всіх активних ставок

**Приклад:**
`/positions 0x1234567890abcdef1234567890abcdef12345678`

Або просто надішліть адресу гаманця без команди!
"""
    await update.message.reply_text(
        welcome_message,
        parse_mode=ParseMode.MARKDOWN
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /help"""
    help_message = """
📖 **Допомога**

**Доступні команди:**
• `/start` - Показати привітальне повідомлення
• `/help` - Показати цю допомогу
• `/positions <адреса>` - Показати позиції гаманця

**Формат адреси:**
Адреса має бути валідною Ethereum адресою у форматі:
`0x` + 40 hex символів

**Приклади:**
✅ `/positions 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb`
✅ Просто надіслати: `0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb`

Бот автоматично розпізнає адресу гаманця!
"""
    await update.message.reply_text(
        help_message,
        parse_mode=ParseMode.MARKDOWN
    )


async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /positions"""
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ Будь ласка, вкажіть адресу гаманця!\n\n"
            "Приклад: `/positions 0x1234...`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    wallet_address = context.args[0]

    # Валідація адреси
    if not is_valid_ethereum_address(wallet_address):
        await update.message.reply_text(
            "❌ Невалідна Ethereum адреса!\n\n"
            "Адреса має починатися з `0x` та містити 40 hex символів.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Нормалізація адреси
    wallet_address = normalize_address(wallet_address)

    # Показати повідомлення про завантаження
    loading_msg = await update.message.reply_text(
        f"🔍 Шукаю позиції для гаманця `{wallet_address[:10]}...`",
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        # Отримати позиції через API
        async with PolymarketAPI() as api:
            positions = await api.get_positions(wallet_address)

            if not positions:
                await loading_msg.edit_text(
                    f"📭 Активних позицій для гаманця `{wallet_address[:10]}...` не знайдено.\n\n"
                    "Можливо:\n"
                    "• Гаманець не має активних ставок\n"
                    "• Адреса введена некоректно\n"
                    "• Позиції вже закриті",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            # Формуємо відповідь з позиціями
            response = f"💼 **Позиції гаманця:** `{wallet_address[:10]}...`\n"
            response += f"📊 **Знайдено позицій:** {len(positions)}\n\n"
            response += "─" * 30 + "\n\n"

            for idx, position in enumerate(positions[:10], 1):  # Обмежуємо 10 позиціями
                formatted_position = format_position(position)
                response += f"**{idx}.** {formatted_position}\n"

            if len(positions) > 10:
                response += f"\n... та ще {len(positions) - 10} позицій"

            await loading_msg.edit_text(
                response,
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        await loading_msg.edit_text(
            "❌ Виникла помилка при отриманні позицій.\n"
            "Спробуйте пізніше.",
            parse_mode=ParseMode.MARKDOWN
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник текстових повідомлень (автоматичне розпізнавання адреси)"""
    text = update.message.text.strip()

    # Перевіряємо чи це адреса гаманця
    if is_valid_ethereum_address(text):
        # Якщо це валідна адреса, обробляємо як команду /positions
        context.args = [text]
        await positions_command(update, context)
    else:
        # Інакше показуємо підказку
        await update.message.reply_text(
            "❓ Не розумію команди.\n\n"
            "Надішліть адресу Ethereum гаманця або використайте /help",
            parse_mode=ParseMode.MARKDOWN
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник помилок"""
    logger.error(f"Update {update} caused error {context.error}")

    if update and update.message:
        await update.message.reply_text(
            "❌ Виникла непередбачена помилка. Спробуйте пізніше."
        )

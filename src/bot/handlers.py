"""
Обробники команд та повідомлень для Telegram бота
"""
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import logging

from src.api.polymarket import PolymarketAPI, format_position
from src.utils.validators import is_valid_ethereum_address, normalize_address
from src.utils.database import Database

logger = logging.getLogger(__name__)

# Глобальна instance бази даних
db = Database()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start"""
    welcome_message = """👋 Привіт! Я бот для моніторингу ставок на Polymarket.

<b>📊 Команди перегляду:</b>
/positions &lt;адреса&gt; - Показати активні позиції гаманця

<b>🔔 Команди моніторингу:</b>
/watchlist - Показати ваш список відстеження
/add &lt;адреса&gt; - Додати гаманець до watchlist
/remove &lt;адреса&gt; - Видалити гаманець з watchlist
/setfilter &lt;ціна&gt; - Встановити макс. ціну входу (наприклад: /setfilter 0.5)

<b>ℹ️ Інше:</b>
/help - Детальна допомога
/start - Це повідомлення

<b>💡 Швидкий старт:</b>
1. Додайте гаманець: <code>/add 0x123...</code>
2. Встановіть фільтр: <code>/setfilter 0.7</code>
3. Отримуйте сповіщення про нові ставки кожні 10 секунд!"""
    await update.message.reply_text(
        welcome_message,
        parse_mode=ParseMode.HTML
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /help"""
    help_message = """📖 <b>Детальна допомога</b>

<b>📊 Команди перегляду:</b>
<code>/positions адреса</code> - Показати всі активні позиції гаманця
Приклад: <code>/positions 0x751a2b86...</code>

<b>🔔 Команди моніторингу:</b>
<code>/watchlist</code> - Показати список відстежуваних гаманців
<code>/add адреса</code> - Додати гаманець до watchlist
<code>/remove адреса</code> - Видалити гаманець з watchlist
<code>/setfilter ціна</code> - Встановити макс. ціну входу (0-1)

<b>💡 Як працює моніторинг:</b>
1. Додайте гаманець через <code>/add</code>
2. Встановіть фільтр через <code>/setfilter</code> (опціонально)
3. Бот автоматично перевіряє нові позиції кожні 10 секунд
4. Отримуйте миттєві сповіщення про нові ставки!

<b>🎯 Приклад фільтрації:</b>
<code>/setfilter 0.5</code> - отримувати тільки ставки з ціною входу ≤ $0.50
<code>/setfilter 0.8</code> - отримувати ставки з ціною входу ≤ $0.80
<code>/setfilter 1.0</code> - отримувати всі ставки

<b>📝 Формат адреси:</b>
Ethereum адреса у форматі: <code>0x</code> + 40 hex символів

<b>ℹ️ Корисно:</b>
• Можна додати кілька гаманців одночасно
• Фільтр діє на всі гаманці в watchlist
• Сповіщення приходять тільки про нові позиції"""
    await update.message.reply_text(
        help_message,
        parse_mode=ParseMode.HTML
    )


async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /positions"""
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ Будь ласка, вкажіть адресу гаманця!\n\n"
            "Приклад: <code>/positions 0x1234...</code>",
            parse_mode=ParseMode.HTML
        )
        return

    wallet_address = context.args[0]

    # Валідація адреси
    if not is_valid_ethereum_address(wallet_address):
        await update.message.reply_text(
            "❌ Невалідна Ethereum адреса!\n\n"
            "Адреса має починатися з <code>0x</code> та містити 40 hex символів.",
            parse_mode=ParseMode.HTML
        )
        return

    # Нормалізація адреси
    wallet_address = normalize_address(wallet_address)

    # Показати повідомлення про завантаження
    loading_msg = await update.message.reply_text(
        f"🔍 Шукаю позиції для гаманця <code>{wallet_address[:10]}...</code>",
        parse_mode=ParseMode.HTML
    )

    try:
        # Отримати позиції через API
        async with PolymarketAPI() as api:
            positions = await api.get_positions(wallet_address)

            if not positions:
                await loading_msg.edit_text(
                    f"📭 Активних позицій для гаманця <code>{wallet_address[:10]}...</code> не знайдено.\n\n"
                    "Можливо:\n"
                    "• Гаманець не має активних ставок\n"
                    "• Адреса введена некоректно\n"
                    "• Позиції вже закриті",
                    parse_mode=ParseMode.HTML
                )
                return

            # Формуємо відповідь з позиціями
            response = f"💼 <b>Позиції гаманця:</b> <code>{wallet_address[:10]}...</code>\n"
            response += f"📊 <b>Знайдено позицій:</b> {len(positions)}\n\n"
            response += "─" * 30 + "\n\n"

            for idx, position in enumerate(positions[:10], 1):  # Обмежуємо 10 позиціями
                formatted_position = format_position(position)
                response += f"<b>{idx}.</b> {formatted_position}\n"

            if len(positions) > 10:
                response += f"\n... та ще {len(positions) - 10} позицій"

            await loading_msg.edit_text(
                response,
                parse_mode=ParseMode.HTML
            )

    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        await loading_msg.edit_text(
            "❌ Виникла помилка при отриманні позицій.\n"
            "Спробуйте пізніше."
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
            "Надішліть адресу Ethereum гаманця або використайте /help"
        )


async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /watchlist - показати список відстеження"""
    chat_id = update.effective_chat.id
    watchlist = db.get_user_watchlist(chat_id)
    max_price = db.get_max_entry_price(chat_id)

    if not watchlist:
        await update.message.reply_text(
            "📭 Ваш watchlist порожній!\n\n"
            "Додайте гаманець командою:\n"
            "<code>/add 0xадреса_гаманця</code>",
            parse_mode=ParseMode.HTML
        )
        return

    message = f"👀 <b>Ваш Watchlist</b>\n\n"
    message += f"Відстежується гаманців: {len(watchlist)}\n"
    message += f"Фільтр по ціні входу: ≤ ${max_price:.2f}\n\n"
    message += "─" * 30 + "\n\n"

    for idx, wallet in enumerate(watchlist, 1):
        message += f"{idx}. <code>{wallet}</code>\n"

    message += f"\n<b>Команди управління:</b>\n"
    message += f"• /add - Додати гаманець\n"
    message += f"• /remove - Видалити гаманець\n"
    message += f"• /setfilter - Змінити фільтр"

    await update.message.reply_text(message, parse_mode=ParseMode.HTML)


async def add_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /add - додати гаманець до watchlist"""
    chat_id = update.effective_chat.id

    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ Будь ласка, вкажіть адресу гаманця!\n\n"
            "Приклад: <code>/add 0x1234...</code>",
            parse_mode=ParseMode.HTML
        )
        return

    wallet_address = context.args[0]

    # Валідація адреси
    if not is_valid_ethereum_address(wallet_address):
        await update.message.reply_text(
            "❌ Невалідна Ethereum адреса!\n\n"
            "Адреса має починатися з <code>0x</code> та містити 40 hex символів.",
            parse_mode=ParseMode.HTML
        )
        return

    # Нормалізація адреси
    wallet_address = normalize_address(wallet_address)

    # Додаємо до watchlist
    success = db.add_wallet_to_watchlist(chat_id, wallet_address)

    if success:
        watchlist = db.get_user_watchlist(chat_id)
        await update.message.reply_text(
            f"✅ Гаманець додано до watchlist!\n\n"
            f"Адреса: <code>{wallet_address}</code>\n"
            f"Всього в watchlist: {len(watchlist)}\n\n"
            f"Ви отримуватимете сповіщення про нові ставки кожні 10 секунд!",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            "⚠️ Цей гаманець вже є у вашому watchlist!",
            parse_mode=ParseMode.HTML
        )


async def remove_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /remove - видалити гаманець з watchlist"""
    chat_id = update.effective_chat.id

    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ Будь ласка, вкажіть адресу гаманця!\n\n"
            "Приклад: <code>/remove 0x1234...</code>",
            parse_mode=ParseMode.HTML
        )
        return

    wallet_address = normalize_address(context.args[0])

    # Видаляємо з watchlist
    success = db.remove_wallet_from_watchlist(chat_id, wallet_address)

    if success:
        watchlist = db.get_user_watchlist(chat_id)
        await update.message.reply_text(
            f"✅ Гаманець видалено з watchlist!\n\n"
            f"Адреса: <code>{wallet_address}</code>\n"
            f"Залишилось в watchlist: {len(watchlist)}",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            "❌ Цього гаманця немає у вашому watchlist!",
            parse_mode=ParseMode.HTML
        )


async def setfilter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /setfilter - встановити фільтр по ціні входу"""
    chat_id = update.effective_chat.id

    if not context.args or len(context.args) == 0:
        current_price = db.get_max_entry_price(chat_id)
        await update.message.reply_text(
            f"📊 Поточний фільтр: ≤ ${current_price:.2f}\n\n"
            f"Для зміни використайте:\n"
            f"<code>/setfilter 0.5</code> - для ціни ≤ $0.50\n"
            f"<code>/setfilter 0.8</code> - для ціни ≤ $0.80\n"
            f"<code>/setfilter 1.0</code> - для всіх ставок",
            parse_mode=ParseMode.HTML
        )
        return

    try:
        max_price = float(context.args[0])

        if max_price <= 0 or max_price > 1:
            await update.message.reply_text(
                "❌ Ціна має бути між 0 та 1!\n\n"
                "Приклад: <code>/setfilter 0.7</code>",
                parse_mode=ParseMode.HTML
            )
            return

        # Встановлюємо фільтр
        db.set_max_entry_price(chat_id, max_price)

        await update.message.reply_text(
            f"✅ Фільтр встановлено!\n\n"
            f"Максимальна ціна входу: ≤ ${max_price:.2f}\n\n"
            f"Ви отримуватимете сповіщення тільки про ставки з ціною входу не вище ${max_price:.2f}",
            parse_mode=ParseMode.HTML
        )

    except ValueError:
        await update.message.reply_text(
            "❌ Невірний формат ціни!\n\n"
            "Використовуйте число від 0 до 1, наприклад:\n"
            "<code>/setfilter 0.7</code>",
            parse_mode=ParseMode.HTML
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник помилок"""
    logger.error(f"Update {update} caused error {context.error}")

    if update and update.message:
        await update.message.reply_text(
            "❌ Виникла непередбачена помилка. Спробуйте пізніше."
        )

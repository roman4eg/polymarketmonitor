"""
Модуль для моніторингу позицій в фоновому режимі
"""
import asyncio
import logging
from typing import Dict, List, Optional
from telegram.ext import Application
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.api.polymarket import PolymarketAPI, format_position
from src.utils.database import Database

logger = logging.getLogger(__name__)


def create_progress_bar(percentage: float, length: int = 10) -> str:
    """
    Створити візуальний прогрес бар

    Args:
        percentage: Відсоток (0-100)
        length: Довжина бару

    Returns:
        Текстовий прогрес бар
    """
    filled = int((percentage / 100) * length)
    empty = length - filled

    if percentage >= 50:
        bar = "🟩" * filled + "⬜" * empty
    else:
        bar = "🟥" * filled + "⬜" * empty

    return bar


class PositionMonitor:
    """Клас для моніторингу нових позицій"""

    def __init__(self, application: Application, db: Database, check_interval: int = 10):
        """
        Ініціалізація монітора

        Args:
            application: Telegram Application
            db: Database instance
            check_interval: Інтервал перевірки в секундах
        """
        self.application = application
        self.db = db
        self.check_interval = check_interval
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Запустити моніторинг"""
        if self.is_running:
            logger.warning("Monitor is already running")
            return

        self.is_running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Position monitor started")

    async def stop(self):
        """Зупинити моніторинг"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Position monitor stopped")

    async def _monitor_loop(self):
        """Основний цикл моніторингу"""
        logger.info("Monitor loop started")

        while self.is_running:
            try:
                await self._check_all_watchlists()
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)

            # Чекаємо перед наступною перевіркою
            await asyncio.sleep(self.check_interval)

    async def _check_all_watchlists(self):
        """Перевірити всі watchlist користувачів"""
        watchlists = self.db.get_all_watchlists()

        if not watchlists:
            return

        logger.debug(f"Checking {len(watchlists)} watchlists")

        # Використовуємо один API клієнт для всіх запитів
        async with PolymarketAPI() as api:
            for chat_id, wallet_addresses in watchlists.items():
                try:
                    await self._check_user_watchlist(api, chat_id, wallet_addresses)
                except Exception as e:
                    logger.error(f"Error checking watchlist for user {chat_id}: {e}")

    async def _check_user_watchlist(self, api: PolymarketAPI, chat_id: int, wallet_addresses: List[str]):
        """
        Перевірити watchlist конкретного користувача

        Args:
            api: API клієнт
            chat_id: ID чату користувача
            wallet_addresses: Список адрес для моніторингу
        """
        max_entry_price = self.db.get_max_entry_price(chat_id)

        for wallet_address in wallet_addresses:
            try:
                positions = await api.get_positions(wallet_address)

                if not positions:
                    continue

                # Перевіряємо кожну позицію
                new_positions = []
                size_changes = []  # Зміни розміру (продаж/merge)

                for position in positions:
                    # Data API повертає поле 'asset' для ID активу
                    asset_id = position.get('asset', '')
                    if not asset_id:
                        # Якщо немає asset, спробуємо conditionId як fallback
                        asset_id = position.get('conditionId', '')
                    if not asset_id:
                        continue

                    current_size = float(position.get('size', 0))
                    avg_price = float(position.get('avgPrice', 0))

                    # Перевіряємо чи це нова позиція
                    if not self.db.is_position_tracked(wallet_address, asset_id):
                        # Перевіряємо фільтр по ціні для нових позицій
                        if avg_price <= max_entry_price:
                            # Додаємо позицію до відстежуваних
                            condition_id = position.get('conditionId', '')
                            self.db.add_tracked_position(wallet_address, asset_id, condition_id, current_size)
                            new_positions.append(position)
                    else:
                        # Перевіряємо зміни розміру існуючої позиції
                        old_size = self.db.get_position_size(wallet_address, asset_id)
                        if old_size is not None and abs(current_size - old_size) > 0.01:  # Якщо зміна більше 0.01
                            size_change_info = {
                                'position': position,
                                'old_size': old_size,
                                'new_size': current_size,
                                'change_type': 'increase' if current_size > old_size else 'decrease'
                            }
                            size_changes.append(size_change_info)
                            # Оновлюємо розмір
                            self.db.update_position_size(wallet_address, asset_id, current_size)

                # Надсилаємо сповіщення про нові позиції
                if new_positions:
                    await self._send_notification(chat_id, wallet_address, new_positions, "new")

                # Надсилаємо сповіщення про зміни розміру
                if size_changes:
                    await self._send_size_change_notification(chat_id, wallet_address, size_changes)

            except Exception as e:
                logger.error(f"Error checking wallet {wallet_address}: {e}")

    async def _send_notification(self, chat_id: int, wallet_address: str, positions: List[Dict], notification_type: str = "new"):
        """
        Надіслати сповіщення про нові позиції

        Args:
            chat_id: ID чату
            wallet_address: Адреса гаманця
            positions: Список нових позицій
            notification_type: Тип сповіщення (new)
        """
        try:
            # Отримуємо ім'я гаманця
            wallet_name = self.db.get_wallet_name(chat_id, wallet_address)

            for position in positions[:5]:  # Обмежуємо 5 позиціями
                # Формуємо повідомлення
                message = f"🎯 <b>Нова ставка!</b>\n\n"

                # Додаємо посилання на профіль
                if wallet_name:
                    profile_link = f"https://polymarket.com/profile/{wallet_address}"
                    message += f"👤 Гаманець: <a href='{profile_link}'>{wallet_name}</a>\n\n"
                else:
                    message += f"👤 Гаманець: <code>{wallet_address[:10]}...{wallet_address[-8:]}</code>\n\n"

                # Додаємо посилання на подію
                slug = position.get('slug', '')
                event_slug = position.get('eventSlug', '')
                title = position.get('title', 'Невідома подія')

                market_link = None
                if slug and event_slug:
                    market_link = f"https://polymarket.com/event/{event_slug}/{slug}"
                    message += f"📋 <a href='{market_link}'>{title}</a>\n\n"
                elif slug:
                    market_link = f"https://polymarket.com/event/{slug}"
                    message += f"📋 <a href='{market_link}'>{title}</a>\n\n"
                else:
                    message += f"📋 {title}\n\n"

                # Додаємо деталі позиції
                outcome = position.get('outcome', 'Unknown')
                size = float(position.get('size', 0))
                avg_price = float(position.get('avgPrice', 0))
                cur_price = float(position.get('curPrice', avg_price))
                initial_value = float(position.get('initialValue', 0))

                # Розраховуємо поточну вартість і прибуток
                current_value = size * cur_price
                profit = current_value - initial_value
                profit_percent = ((cur_price - avg_price) / avg_price * 100) if avg_price > 0 else 0

                message += f"💎 Позиція: <b>{outcome}</b>\n"
                message += f"💰 Розмір: <b>${current_value:.2f}</b> ({size:.0f} токенів)\n"
                message += f"💵 Ціна входу: ${avg_price:.4f}\n"
                message += f"📈 Поточна ціна: ${cur_price:.4f}"

                # Додаємо прибуток/збиток
                if abs(profit_percent) > 0.1:
                    profit_emoji = "🟢" if profit > 0 else "🔴"
                    message += f" ({profit_percent:+.1f}%) {profit_emoji}\n"
                else:
                    message += f" (0%) ➡️\n"

                message += f"💎 Потенційний профіт: ${size - initial_value:.2f}\n\n"

                # Додаємо прогрес бар (якщо є дані про YES/NO)
                # Використовуємо поточну ціну як ймовірність YES
                yes_prob = cur_price * 100
                no_prob = 100 - yes_prob
                yes_bar = create_progress_bar(yes_prob, 10)
                no_bar = create_progress_bar(no_prob, 10)

                message += f"📊 <b>Ймовірність:</b>\n"
                message += f"YES {yes_bar} {yes_prob:.0f}%\n"
                message += f"NO  {no_bar} {no_prob:.0f}%"

                # Створюємо inline кнопки
                keyboard = []
                if market_link:
                    keyboard.append([InlineKeyboardButton("🔗 Відкрити на Polymarket", url=market_link)])

                profile_url = f"https://polymarket.com/profile/{wallet_address}"
                keyboard.append([InlineKeyboardButton("👤 Профіль гаманця", url=profile_url)])

                reply_markup = InlineKeyboardMarkup(keyboard)

                # Надсилаємо повідомлення
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=reply_markup
                )

            logger.info(f"Notification sent to {chat_id} for {wallet_address}: {len(positions)} new positions")

        except Exception as e:
            logger.error(f"Error sending notification to {chat_id}: {e}")

    async def _send_size_change_notification(self, chat_id: int, wallet_address: str, size_changes: List[Dict]):
        """
        Надіслати сповіщення про зміни розміру позицій

        Args:
            chat_id: ID чату
            wallet_address: Адреса гаманця
            size_changes: Список змін розміру
        """
        try:
            # Отримуємо ім'я гаманця
            wallet_name = self.db.get_wallet_name(chat_id, wallet_address)

            # Формуємо повідомлення
            for change_info in size_changes:
                change_type = change_info['change_type']
                old_size = change_info['old_size']
                new_size = change_info['new_size']
                position = change_info['position']

                if change_type == 'decrease':
                    emoji = "📉"
                    action = "Продаж/Merge позиції"
                    change_amount = old_size - new_size
                else:
                    emoji = "📈"
                    action = "Додавання позиції"
                    change_amount = new_size - old_size

                message = f"{emoji} <b>{action}!</b>\n\n"

                # Додаємо посилання на профіль
                if wallet_name:
                    profile_link = f"https://polymarket.com/profile/{wallet_address}"
                    message += f"👤 Гаманець: <a href='{profile_link}'>{wallet_name}</a>\n\n"
                else:
                    message += f"👤 Гаманець: <code>{wallet_address[:10]}...{wallet_address[-8:]}</code>\n\n"

                # Додаємо посилання на подію
                slug = position.get('slug', '')
                event_slug = position.get('eventSlug', '')
                title = position.get('title', 'Невідома подія')

                market_link = None
                if slug and event_slug:
                    market_link = f"https://polymarket.com/event/{event_slug}/{slug}"
                    message += f"📋 <a href='{market_link}'>{title}</a>\n\n"
                elif slug:
                    market_link = f"https://polymarket.com/event/{slug}"
                    message += f"📋 <a href='{market_link}'>{title}</a>\n\n"
                else:
                    message += f"📋 {title}\n\n"

                # Додаємо деталі зміни
                outcome = position.get('outcome', 'Unknown')
                cur_price = float(position.get('curPrice', 0))

                # Розраховуємо вартість
                old_value = old_size * cur_price
                new_value = new_size * cur_price
                value_change = new_value - old_value

                message += f"💎 Позиція: <b>{outcome}</b>\n"
                message += f"📊 Було: {old_size:.0f} токенів (${old_value:.2f})\n"
                message += f"📊 Стало: {new_size:.0f} токенів (${new_value:.2f})\n"

                # Додаємо зміну з кольоровим індикатором
                change_emoji = "🟢" if change_type == 'increase' else "🔴"
                message += f"📈 Зміна: {'+' if change_type == 'increase' else ''}{change_amount:.0f} токенів (${value_change:+.2f}) {change_emoji}\n"
                message += f"💵 Поточна ціна: ${cur_price:.4f}\n\n"

                # Додаємо прогрес бар
                yes_prob = cur_price * 100
                no_prob = 100 - yes_prob
                yes_bar = create_progress_bar(yes_prob, 10)
                no_bar = create_progress_bar(no_prob, 10)

                message += f"📊 <b>Ймовірність:</b>\n"
                message += f"YES {yes_bar} {yes_prob:.0f}%\n"
                message += f"NO  {no_bar} {no_prob:.0f}%"

                # Створюємо inline кнопки
                keyboard = []
                if market_link:
                    keyboard.append([InlineKeyboardButton("🔗 Відкрити на Polymarket", url=market_link)])

                profile_url = f"https://polymarket.com/profile/{wallet_address}"
                keyboard.append([InlineKeyboardButton("👤 Профіль гаманця", url=profile_url)])

                reply_markup = InlineKeyboardMarkup(keyboard)

                # Надсилаємо повідомлення
                await self.application.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=reply_markup
                )

            logger.info(f"Size change notification sent to {chat_id} for {wallet_address}: {len(size_changes)} changes")

        except Exception as e:
            logger.error(f"Error sending size change notification to {chat_id}: {e}")

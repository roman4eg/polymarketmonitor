"""
Модуль для моніторингу позицій в фоновому режимі
"""
import asyncio
import logging
from typing import Dict, List, Optional
from telegram.ext import Application

from src.api.polymarket import PolymarketAPI, format_position
from src.utils.database import Database

logger = logging.getLogger(__name__)


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
                for position in positions:
                    # Data API повертає поле 'asset' для ID активу
                    asset_id = position.get('asset', '')
                    if not asset_id:
                        # Якщо немає asset, спробуємо conditionId як fallback
                        asset_id = position.get('conditionId', '')
                    if not asset_id:
                        continue

                    # Перевіряємо фільтр по ціні
                    avg_price = float(position.get('avgPrice', 0))
                    if avg_price > max_entry_price:
                        continue

                    # Перевіряємо чи це нова позиція
                    if not self.db.is_position_tracked(wallet_address, asset_id):
                        # Додаємо позицію до відстежуваних
                        condition_id = position.get('conditionId', '')
                        self.db.add_tracked_position(wallet_address, asset_id, condition_id)
                        new_positions.append(position)

                # Надсилаємо сповіщення про нові позиції
                if new_positions:
                    await self._send_notification(chat_id, wallet_address, new_positions)

            except Exception as e:
                logger.error(f"Error checking wallet {wallet_address}: {e}")

    async def _send_notification(self, chat_id: int, wallet_address: str, positions: List[Dict]):
        """
        Надіслати сповіщення про нові позиції

        Args:
            chat_id: ID чату
            wallet_address: Адреса гаманця
            positions: Список нових позицій
        """
        try:
            # Формуємо повідомлення
            message = f"🔔 <b>Нова ставка!</b>\n\n"
            message += f"Гаманець: <code>{wallet_address[:10]}...{wallet_address[-8:]}</code>\n"
            message += f"Нових позицій: {len(positions)}\n\n"
            message += "─" * 30 + "\n\n"

            for idx, position in enumerate(positions[:5], 1):  # Обмежуємо 5 позиціями
                formatted_position = format_position(position)
                message += f"<b>{idx}.</b> {formatted_position}\n"

            if len(positions) > 5:
                message += f"\n... та ще {len(positions) - 5} позицій"

            # Надсилаємо повідомлення
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="HTML"
            )

            logger.info(f"Notification sent to {chat_id} for {wallet_address}: {len(positions)} new positions")

        except Exception as e:
            logger.error(f"Error sending notification to {chat_id}: {e}")

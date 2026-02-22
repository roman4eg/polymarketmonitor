"""
Модуль для моніторингу позицій в фоновому режимі
"""
import asyncio
import logging
import logging.handlers
import os
from typing import Dict, List, Optional, Set
from telegram.ext import Application
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.api.polymarket import PolymarketAPI, format_position
from src.utils.database import Database

logger = logging.getLogger(__name__)

# Налаштування окремого debug-логера у файл
def setup_debug_logger() -> logging.Logger:
    debug_logger = logging.getLogger("polymarket.debug")
    debug_logger.setLevel(logging.DEBUG)

    if not debug_logger.handlers:
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        # Rotating file handler: макс 5 МБ, 3 файли
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, "debug.log"),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        debug_logger.addHandler(file_handler)
        debug_logger.propagate = False

    return debug_logger

debug_log = setup_debug_logger()


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
                debug_log.debug(f"=== Checking wallet {wallet_address} (chat_id={chat_id}) ===")

                positions = await api.get_positions(wallet_address)

                # Позиції з БД (відстежувані)
                db_positions = self.db.get_wallet_tracked_positions(wallet_address)
                db_asset_ids: Set[str] = {p["asset_id"] for p in db_positions}

                total_api = len(positions) if positions else 0
                debug_log.debug(f"API returned {total_api} positions (all pages fetched)")
                debug_log.debug(f"DB has {len(db_asset_ids)} tracked positions")

                new_positions = []
                size_changes = []

                if positions:
                    # ID активів, які є в API зараз
                    api_asset_ids: Set[str] = set()

                    for position in positions:
                        asset_id = position.get('asset', '') or position.get('conditionId', '')
                        if not asset_id:
                            debug_log.debug(f"  Skipping position without asset_id: {position.get('title', '?')}")
                            continue

                        api_asset_ids.add(asset_id)
                        current_size = float(position.get('size', 0))
                        avg_price = float(position.get('avgPrice', 0))
                        title = position.get('title', '?')

                        debug_log.debug(
                            f"  Position: {title[:50]} | asset={asset_id[:16]}... | "
                            f"size={current_size:.2f} | avg_price={avg_price:.4f}"
                        )

                        if asset_id not in db_asset_ids:
                            # Нова позиція
                            cur_price_new = float(position.get('curPrice', avg_price))
                            debug_log.debug(f"    → NEW position (not in DB) | curPrice={cur_price_new:.4f}")

                            # Пропускаємо resolved ринки (curPrice = 0 означає завершений ринок)
                            if cur_price_new == 0:
                                debug_log.debug(f"    → Skipped: resolved market (curPrice=0)")
                                # Все одно додаємо до DB щоб не показувати знову
                                self.db.add_tracked_position(
                                    wallet_address, asset_id,
                                    position.get('conditionId', ''), current_size,
                                    title=position.get('title'), outcome=position.get('outcome'),
                                    slug=position.get('slug'), event_slug=position.get('eventSlug')
                                )
                                continue

                            if avg_price <= max_entry_price:
                                condition_id = position.get('conditionId', '')
                                added = self.db.add_tracked_position(
                                    wallet_address, asset_id, condition_id, current_size,
                                    title=position.get('title'), outcome=position.get('outcome'),
                                    slug=position.get('slug'), event_slug=position.get('eventSlug')
                                )
                                debug_log.debug(f"    → Added to DB: {added}")
                                new_positions.append(position)
                            else:
                                debug_log.debug(
                                    f"    → Filtered out: avg_price={avg_price:.4f} > max_entry_price={max_entry_price:.4f}"
                                )
                        else:
                            # Існуюча позиція — оновлюємо metadata якщо вона відсутня в DB
                            self.db.update_position_metadata(
                                wallet_address, asset_id,
                                title=position.get('title'),
                                outcome=position.get('outcome'),
                                slug=position.get('slug'),
                                event_slug=position.get('eventSlug'),
                            )

                            # Перевіряємо зміну розміру
                            old_size = self.db.get_position_size(wallet_address, asset_id)
                            debug_log.debug(
                                f"    → EXISTING | old_size={old_size} | current_size={current_size:.2f} | "
                                f"diff={abs(current_size - (old_size or 0)):.4f}"
                            )

                            if old_size is not None and abs(current_size - old_size) > 0.01:
                                change_type = 'increase' if current_size > old_size else 'decrease'
                                debug_log.debug(f"    → SIZE CHANGE detected: {change_type} ({old_size:.2f} → {current_size:.2f})")
                                size_changes.append({
                                    'position': position,
                                    'old_size': old_size,
                                    'new_size': current_size,
                                    'change_type': change_type
                                })
                                self.db.update_position_size(wallet_address, asset_id, current_size)
                            else:
                                debug_log.debug(f"    → No significant change")

                    # Перевіряємо повністю продані позиції (є в БД, але відсутні в API)
                    fully_closed = db_asset_ids - api_asset_ids
                    debug_log.debug(f"Fully closed positions (in DB but not in API): {fully_closed}")

                    for asset_id in fully_closed:
                        db_pos = next((p for p in db_positions if p["asset_id"] == asset_id), None)
                        old_size = db_pos["size"] if db_pos else 0
                        debug_log.debug(f"  → FULL SELL: asset={asset_id[:16]}... | last known size={old_size:.2f}")

                        # Будуємо позицію для сповіщення з metadata зі збереженої в DB
                        closed_position = {
                            'asset': asset_id,
                            'conditionId': db_pos["condition_id"] if db_pos else '',
                            'title': (db_pos["title"] if db_pos and db_pos["title"] else 'Невідома позиція'),
                            'outcome': (db_pos["outcome"] if db_pos and db_pos["outcome"] else '—'),
                            'size': 0,
                            'avgPrice': 0,
                            'curPrice': 0,
                            'slug': (db_pos["slug"] if db_pos and db_pos["slug"] else ''),
                            'eventSlug': (db_pos["event_slug"] if db_pos and db_pos["event_slug"] else ''),
                        }
                        size_changes.append({
                            'position': closed_position,
                            'old_size': old_size,
                            'new_size': 0,
                            'change_type': 'decrease',
                            'fully_closed': True
                        })
                        self.db.remove_tracked_position(wallet_address, asset_id)
                        debug_log.debug(f"  → Removed from DB")

                else:
                    # API повернув пусто — можливо всі позиції закриті
                    debug_log.debug(f"API returned empty — checking for fully closed positions")
                    for db_pos in db_positions:
                        asset_id = db_pos["asset_id"]
                        old_size = db_pos["size"]
                        debug_log.debug(f"  → FULL SELL (empty API): asset={asset_id[:16]}... | size={old_size:.2f}")
                        closed_position = {
                            'asset': asset_id,
                            'conditionId': db_pos["condition_id"] or '',
                            'title': (db_pos["title"] if db_pos["title"] else 'Невідома позиція'),
                            'outcome': (db_pos["outcome"] if db_pos["outcome"] else '—'),
                            'size': 0,
                            'avgPrice': 0,
                            'curPrice': 0,
                            'slug': (db_pos["slug"] or ''),
                            'eventSlug': (db_pos["event_slug"] or ''),
                        }
                        size_changes.append({
                            'position': closed_position,
                            'old_size': old_size,
                            'new_size': 0,
                            'change_type': 'decrease',
                            'fully_closed': True
                        })
                        self.db.remove_tracked_position(wallet_address, asset_id)

                debug_log.debug(
                    f"Summary: {len(new_positions)} new, {len(size_changes)} changes "
                    f"(for wallet {wallet_address})"
                )

                if new_positions:
                    await self._send_notification(chat_id, wallet_address, new_positions, "new")

                if size_changes:
                    await self._send_size_change_notification(chat_id, wallet_address, size_changes)

            except Exception as e:
                logger.error(f"Error checking wallet {wallet_address}: {e}", exc_info=True)
                debug_log.error(f"Exception for wallet {wallet_address}: {e}", exc_info=True)

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

                fully_closed = change_info.get('fully_closed', False)

                if change_type == 'decrease':
                    if fully_closed:
                        emoji = "🔴"
                        action = "Позицію повністю продано"
                    else:
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
                outcome = position.get('outcome', '—')
                cur_price = float(position.get('curPrice', 0))

                message += f"💎 Позиція: <b>{outcome}</b>\n"

                if fully_closed:
                    # Повне закриття — ціни API вже немає
                    message += f"📊 Було: {old_size:.0f} токенів\n"
                    message += f"📊 Стало: 0 токенів (повністю продано) 🔴\n"
                    message += f"📈 Зміна: -{change_amount:.0f} токенів\n"
                else:
                    # Часткова зміна — є актуальна ціна
                    old_value = old_size * cur_price
                    new_value = new_size * cur_price
                    value_change = new_value - old_value

                    message += f"📊 Було: {old_size:.0f} токенів (${old_value:.2f})\n"
                    message += f"📊 Стало: {new_size:.0f} токенів (${new_value:.2f})\n"

                    change_emoji = "🟢" if change_type == 'increase' else "🔴"
                    message += f"📈 Зміна: {'+' if change_type == 'increase' else ''}{change_amount:.0f} токенів (${value_change:+.2f}) {change_emoji}\n"
                    message += f"💵 Поточна ціна: ${cur_price:.4f}\n\n"

                    # Прогрес бар тільки якщо є реальна ціна
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

            debug_log.debug(
                f"Size change notifications sent: {len(size_changes)} for wallet {wallet_address}"
            )
            logger.info(f"Size change notification sent to {chat_id} for {wallet_address}: {len(size_changes)} changes")

        except Exception as e:
            logger.error(f"Error sending size change notification to {chat_id}: {e}")
            debug_log.error(f"Error in _send_size_change_notification: {e}", exc_info=True)

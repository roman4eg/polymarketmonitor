"""
Модуль для роботи з Polymarket API
"""
import aiohttp
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PolymarketAPI:
    """Клас для взаємодії з Polymarket API"""

    BASE_URL = "https://clob.polymarket.com"
    DATA_API_URL = "https://data-api.polymarket.com"
    GAMMA_API_URL = "https://gamma-api.polymarket.com"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def get_positions(self, wallet_address: str) -> List[Dict]:
        """
        Отримати всі активні позиції (ставки) для гаманця з пагінацією

        Args:
            wallet_address: Адреса гаманця Ethereum

        Returns:
            Повний список позицій користувача (всі сторінки)
        """
        PAGE_SIZE = 100
        all_positions = []
        offset = 0

        try:
            while True:
                url = f"{self.DATA_API_URL}/positions"
                params = {
                    "user": wallet_address.lower(),
                    "sizeThreshold": "0.01",
                    "limit": str(PAGE_SIZE),
                    "offset": str(offset)
                }

                async with self.session.get(url, params=params) as response:
                    if response.status != 200:
                        text = await response.text()
                        logger.error(f"Error fetching positions (offset={offset}): {response.status} — {text}")
                        break

                    data = await response.json()
                    page = data if isinstance(data, list) else []
                    all_positions.extend(page)

                    logger.debug(f"Fetched {len(page)} positions (offset={offset}), total so far: {len(all_positions)}")

                    # Якщо прийшло менше ніж PAGE_SIZE — більше немає
                    if len(page) < PAGE_SIZE:
                        break

                    offset += PAGE_SIZE

            return all_positions

        except Exception as e:
            logger.error(f"Exception in get_positions: {e}")
            return []

    async def get_market_info(self, condition_id: str) -> Optional[Dict]:
        """
        Отримати інформацію про ринок

        Args:
            condition_id: ID умови ринку

        Returns:
            Інформація про ринок
        """
        try:
            url = f"{self.GAMMA_API_URL}/markets/{condition_id}"

            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Error fetching market info: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Exception in get_market_info: {e}")
            return None

    async def get_markets(self) -> List[Dict]:
        """
        Отримати список всіх активних ринків

        Returns:
            Список ринків
        """
        try:
            url = f"{self.GAMMA_API_URL}/markets"

            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data if isinstance(data, list) else []
                else:
                    logger.error(f"Error fetching markets: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Exception in get_markets: {e}")
            return []

    async def get_events(self) -> List[Dict]:
        """
        Отримати список подій/ринків

        Returns:
            Список подій
        """
        try:
            url = f"{self.GAMMA_API_URL}/events"
            params = {"closed": "false"}

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data if isinstance(data, list) else []
                else:
                    logger.error(f"Error fetching events: {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Exception in get_events: {e}")
            return []


def format_position(position: Dict, market_info: Optional[Dict] = None) -> str:
    """
    Форматувати позицію для відображення в Telegram

    Args:
        position: Дані позиції
        market_info: Додаткова інформація про ринок

    Returns:
        Форматований текст позиції
    """
    try:
        # Отримуємо дані з Data API response
        title = position.get('title', 'N/A')
        outcome = position.get('outcome', 'Unknown')
        size = float(position.get('size', 0))
        avg_price = float(position.get('avgPrice', 0))
        cur_price = float(position.get('curPrice', 0))
        initial_value = float(position.get('initialValue', 0))
        current_value = float(position.get('currentValue', 0))
        cash_pnl = float(position.get('cashPnl', 0))
        percent_pnl = float(position.get('percentPnl', 0))

        # Форматуємо вивід
        result = f"📊 <b>{title}</b>\n"
        result += f"├ Позиція: <b>{outcome}</b>\n"
        result += f"├ Розмір: {size:.2f} токенів\n"
        result += f"├ Ціна входу: ${avg_price:.4f}\n"
        result += f"├ Поточна ціна: ${cur_price:.4f}\n"
        result += f"├ Початкова вартість: ${initial_value:.2f}\n"
        result += f"├ Поточна вартість: ${current_value:.2f}\n"

        # Показуємо прибуток/збиток з кольором
        pnl_emoji = "📈" if cash_pnl >= 0 else "📉"
        pnl_sign = "+" if cash_pnl >= 0 else ""
        result += f"└ P&L: {pnl_emoji} {pnl_sign}${cash_pnl:.2f} ({pnl_sign}{percent_pnl:.2f}%)\n"

        return result
    except Exception as e:
        logger.error(f"Error formatting position: {e}")
        logger.error(f"Position data: {position}")
        return "❌ Помилка форматування позиції"

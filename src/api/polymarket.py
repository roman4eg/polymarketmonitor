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
        Отримати активні позиції (ставки) для гаманця

        Args:
            wallet_address: Адреса гаманця Ethereum

        Returns:
            Список позицій користувача
        """
        try:
            url = f"{self.GAMMA_API_URL}/positions"
            params = {"user": wallet_address.lower()}

            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data if isinstance(data, list) else []
                else:
                    logger.error(f"Error fetching positions: {response.status}")
                    return []
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
        asset_id = position.get('asset_id', 'N/A')
        market_id = position.get('market', 'N/A')
        size = float(position.get('size', 0))

        # Отримуємо інформацію про токен
        outcome = position.get('outcome', 'Unknown')

        # Вартість позиції
        value = position.get('value', 'N/A')

        # Середня ціна входу
        avg_price = position.get('avg_price', 'N/A')

        result = f"📊 <b>Позиція #{asset_id[:8]}...</b>\n"
        result += f"├ Результат: {outcome}\n"
        result += f"├ Розмір: {size:.2f}\n"
        result += f"├ Середня ціна: {avg_price}\n"
        result += f"├ Вартість: {value}\n"
        result += f"└ Ринок: {market_id[:16]}...\n"

        if market_info:
            title = market_info.get('question', market_info.get('title', 'N/A'))
            result += f"\n📝 {title}\n"

        return result
    except Exception as e:
        logger.error(f"Error formatting position: {e}")
        return "❌ Помилка форматування позиції"

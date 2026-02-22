"""
Модуль для роботи з базою даних
"""
import sqlite3
import logging
from typing import List, Dict, Optional
from contextlib import contextmanager
import os

logger = logging.getLogger(__name__)


class Database:
    """Клас для роботи з SQLite базою даних"""

    def __init__(self, db_path: str = "data/watchlist.db"):
        """
        Ініціалізація бази даних

        Args:
            db_path: Шлях до файлу бази даних
        """
        # Створюємо директорію якщо не існує
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Контекстний менеджер для підключення до БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Ініціалізація таблиць бази даних"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Таблиця користувачів
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    chat_id INTEGER UNIQUE NOT NULL,
                    max_entry_price REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблиця watchlist з іменами гаманців
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    wallet_address TEXT NOT NULL,
                    wallet_name TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id, wallet_address)
                )
            """)

            # Перевірка чи існує колонка wallet_name (для міграції старих БД)
            cursor.execute("PRAGMA table_info(watchlist)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'wallet_name' not in columns:
                cursor.execute("ALTER TABLE watchlist ADD COLUMN wallet_name TEXT")
                logger.info("Added wallet_name column to watchlist table")

            # Таблиця відстежуваних позицій з розміром для виявлення змін
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracked_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wallet_address TEXT NOT NULL,
                    asset_id TEXT NOT NULL,
                    condition_id TEXT,
                    size REAL DEFAULT 0,
                    title TEXT,
                    outcome TEXT,
                    slug TEXT,
                    event_slug TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(wallet_address, asset_id)
                )
            """)

            # Перевірка чи існують всі необхідні колонки
            cursor.execute("PRAGMA table_info(tracked_positions)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'size' not in columns:
                cursor.execute("ALTER TABLE tracked_positions ADD COLUMN size REAL DEFAULT 0")
                logger.info("Added size column to tracked_positions table")
            if 'last_updated' not in columns:
                cursor.execute("ALTER TABLE tracked_positions ADD COLUMN last_updated TIMESTAMP")
                cursor.execute("UPDATE tracked_positions SET last_updated = CURRENT_TIMESTAMP WHERE last_updated IS NULL")
                logger.info("Added last_updated column to tracked_positions table")
            for col in ('title', 'outcome', 'slug', 'event_slug'):
                if col not in columns:
                    cursor.execute(f"ALTER TABLE tracked_positions ADD COLUMN {col} TEXT")
                    logger.info(f"Added {col} column to tracked_positions table")

            logger.info("Database initialized successfully")

    def add_user(self, chat_id: int) -> bool:
        """
        Додати користувача

        Args:
            chat_id: ID чату Telegram

        Returns:
            True якщо користувач доданий успішно
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO users (user_id, chat_id) VALUES (?, ?)",
                    (chat_id, chat_id)
                )
                return True
        except Exception as e:
            logger.error(f"Error adding user: {e}")
            return False

    def add_wallet_to_watchlist(self, chat_id: int, wallet_address: str, wallet_name: Optional[str] = None) -> bool:
        """
        Додати гаманець до watchlist

        Args:
            chat_id: ID чату користувача
            wallet_address: Адреса гаманця
            wallet_name: Назва гаманця (опціонально)

        Returns:
            True якщо гаманець доданий успішно
        """
        try:
            # Спочатку переконуємось що користувач існує
            self.add_user(chat_id)

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO watchlist (user_id, wallet_address, wallet_name) VALUES (?, ?, ?)",
                    (chat_id, wallet_address.lower(), wallet_name)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error adding wallet to watchlist: {e}")
            return False

    def remove_wallet_from_watchlist(self, chat_id: int, wallet_address: str) -> bool:
        """
        Видалити гаманець з watchlist

        Args:
            chat_id: ID чату користувача
            wallet_address: Адреса гаманця

        Returns:
            True якщо гаманець видалено успішно
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM watchlist WHERE user_id = ? AND wallet_address = ?",
                    (chat_id, wallet_address.lower())
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing wallet from watchlist: {e}")
            return False

    def get_user_watchlist(self, chat_id: int) -> List[str]:
        """
        Отримати watchlist користувача

        Args:
            chat_id: ID чату користувача

        Returns:
            Список адрес гаманців
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT wallet_address FROM watchlist WHERE user_id = ? ORDER BY added_at DESC",
                    (chat_id,)
                )
                return [row["wallet_address"] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting user watchlist: {e}")
            return []

    def get_all_watchlists(self) -> Dict[int, List[str]]:
        """
        Отримати всі watchlist

        Returns:
            Словник {chat_id: [wallet_addresses]}
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id, wallet_address FROM watchlist")

                watchlists = {}
                for row in cursor.fetchall():
                    user_id = row["user_id"]
                    wallet = row["wallet_address"]
                    if user_id not in watchlists:
                        watchlists[user_id] = []
                    watchlists[user_id].append(wallet)

                return watchlists
        except Exception as e:
            logger.error(f"Error getting all watchlists: {e}")
            return {}

    def set_max_entry_price(self, chat_id: int, max_price: float) -> bool:
        """
        Встановити максимальну ціну входу для фільтрації

        Args:
            chat_id: ID чату користувача
            max_price: Максимальна ціна входу

        Returns:
            True якщо встановлено успішно
        """
        try:
            # Спочатку переконуємось що користувач існує
            self.add_user(chat_id)

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET max_entry_price = ? WHERE user_id = ?",
                    (max_price, chat_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error setting max entry price: {e}")
            return False

    def get_max_entry_price(self, chat_id: int) -> float:
        """
        Отримати максимальну ціну входу користувача

        Args:
            chat_id: ID чату користувача

        Returns:
            Максимальна ціна входу (за замовчуванням 1.0)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT max_entry_price FROM users WHERE user_id = ?",
                    (chat_id,)
                )
                row = cursor.fetchone()
                return row["max_entry_price"] if row else 1.0
        except Exception as e:
            logger.error(f"Error getting max entry price: {e}")
            return 1.0

    def is_position_tracked(self, wallet_address: str, asset_id: str) -> bool:
        """
        Перевірити чи позиція вже відстежується

        Args:
            wallet_address: Адреса гаманця
            asset_id: ID активу

        Returns:
            True якщо позиція вже відстежується
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT 1 FROM tracked_positions WHERE wallet_address = ? AND asset_id = ?",
                    (wallet_address.lower(), asset_id)
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking tracked position: {e}")
            return False

    def add_tracked_position(
        self,
        wallet_address: str,
        asset_id: str,
        condition_id: Optional[str] = None,
        size: float = 0,
        title: Optional[str] = None,
        outcome: Optional[str] = None,
        slug: Optional[str] = None,
        event_slug: Optional[str] = None,
    ) -> bool:
        """
        Додати позицію до відстежуваних

        Args:
            wallet_address: Адреса гаманця
            asset_id: ID активу
            condition_id: ID умови (опціонально)
            size: Розмір позиції
            title: Назва ринку
            outcome: Позиція (YES/NO/назва команди)
            slug: Slug ринку
            event_slug: Slug події

        Returns:
            True якщо позиція додана успішно
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT OR IGNORE INTO tracked_positions
                       (wallet_address, asset_id, condition_id, size, title, outcome, slug, event_slug, last_updated)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                    (wallet_address.lower(), asset_id, condition_id, size, title, outcome, slug, event_slug)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error adding tracked position: {e}")
            return False

    def get_wallet_name(self, chat_id: int, wallet_address: str) -> Optional[str]:
        """
        Отримати ім'я гаманця

        Args:
            chat_id: ID чату користувача
            wallet_address: Адреса гаманця

        Returns:
            Ім'я гаманця або None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT wallet_name FROM watchlist WHERE user_id = ? AND wallet_address = ?",
                    (chat_id, wallet_address.lower())
                )
                row = cursor.fetchone()
                return row["wallet_name"] if row else None
        except Exception as e:
            logger.error(f"Error getting wallet name: {e}")
            return None

    def get_watchlist_with_names(self, chat_id: int) -> List[Dict[str, str]]:
        """
        Отримати watchlist з іменами

        Args:
            chat_id: ID чату користувача

        Returns:
            Список словників з адресами та іменами
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT wallet_address, wallet_name FROM watchlist WHERE user_id = ? ORDER BY added_at DESC",
                    (chat_id,)
                )
                return [{"address": row["wallet_address"], "name": row["wallet_name"]} for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting watchlist with names: {e}")
            return []

    def get_wallet_tracked_positions(self, wallet_address: str) -> List[Dict]:
        """
        Отримати всі відстежувані позиції гаманця з БД

        Args:
            wallet_address: Адреса гаманця

        Returns:
            Список позицій зі словниками {asset_id, condition_id, size}
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT asset_id, condition_id, size, title, outcome, slug, event_slug FROM tracked_positions WHERE wallet_address = ?",
                    (wallet_address.lower(),)
                )
                return [
                    {
                        "asset_id": row["asset_id"],
                        "condition_id": row["condition_id"],
                        "size": row["size"],
                        "title": row["title"],
                        "outcome": row["outcome"],
                        "slug": row["slug"],
                        "event_slug": row["event_slug"],
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Error getting wallet tracked positions: {e}")
            return []

    def remove_tracked_position(self, wallet_address: str, asset_id: str) -> bool:
        """
        Видалити позицію зі списку відстежуваних (повний продаж)

        Args:
            wallet_address: Адреса гаманця
            asset_id: ID активу

        Returns:
            True якщо видалено успішно
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM tracked_positions WHERE wallet_address = ? AND asset_id = ?",
                    (wallet_address.lower(), asset_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error removing tracked position: {e}")
            return False

    def get_position_size(self, wallet_address: str, asset_id: str) -> Optional[float]:
        """
        Отримати розмір позиції

        Args:
            wallet_address: Адреса гаманця
            asset_id: ID активу

        Returns:
            Розмір позиції або None
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT size FROM tracked_positions WHERE wallet_address = ? AND asset_id = ?",
                    (wallet_address.lower(), asset_id)
                )
                row = cursor.fetchone()
                return row["size"] if row else None
        except Exception as e:
            logger.error(f"Error getting position size: {e}")
            return None

    def update_position_size(self, wallet_address: str, asset_id: str, new_size: float) -> bool:
        """
        Оновити розмір позиції

        Args:
            wallet_address: Адреса гаманця
            asset_id: ID активу
            new_size: Новий розмір позиції

        Returns:
            True якщо оновлено успішно
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE tracked_positions SET size = ?, last_updated = CURRENT_TIMESTAMP WHERE wallet_address = ? AND asset_id = ?",
                    (new_size, wallet_address.lower(), asset_id)
                )
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating position size: {e}")
            return False

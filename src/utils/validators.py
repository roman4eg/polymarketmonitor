"""
Утиліти для валідації даних
"""
import re


def is_valid_ethereum_address(address: str) -> bool:
    """
    Перевірити чи є адреса валідною Ethereum адресою

    Args:
        address: Адреса для перевірки

    Returns:
        True якщо адреса валідна, False інакше
    """
    if not address:
        return False

    # Перевірка базового формату (0x + 40 hex символів)
    pattern = r'^0x[a-fA-F0-9]{40}$'
    return bool(re.match(pattern, address))


def normalize_address(address: str) -> str:
    """
    Нормалізувати Ethereum адресу (lowercase)

    Args:
        address: Адреса для нормалізації

    Returns:
        Нормалізована адреса
    """
    return address.lower().strip()

# Polymarket Monitor Bot 🤖

Telegram бот для моніторингу активних ставок на Polymarket за адресою Ethereum гаманця.

## 📋 Опис

Цей бот дозволяє швидко переглядати активні позиції (ставки) будь-якого гаманця на платформі Polymarket. Просто надішліть адресу гаманця, і отримаєте детальну інформацію про всі активні ставки.

## ✨ Функціональність

- 🔍 Пошук активних позицій за адресою гаманця
- 📊 Відображення детальної інформації про кожну позицію
- ✅ Автоматична валідація Ethereum адрес
- 🚀 Простий та зручний інтерфейс

## 🛠 Технології

- Python 3.8+
- python-telegram-bot - для роботи з Telegram Bot API
- aiohttp - для асинхронних HTTP запитів
- Polymarket API - для отримання даних про ставки

## 📦 Встановлення

### 1. Клонуйте репозиторій

```bash
git clone https://github.com/yourusername/polymarketmonitor.git
cd polymarketmonitor
```

### 2. Створіть віртуальне середовище

```bash
python -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
```

### 3. Встановіть залежності

```bash
pip install -r requirements.txt
```

### 4. Налаштуйте бота

1. Створіть нового бота через [@BotFather](https://t.me/BotFather) в Telegram
2. Скопіюйте отриманий токен
3. Створіть файл `.env` на основі `.env.example`:

```bash
cp .env.example .env
```

4. Відредагуйте `.env` та додайте свій токен:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

## 🚀 Запуск

```bash
python main.py
```

Якщо все налаштовано правильно, ви побачите повідомлення:

```
Starting Polymarket Monitor Bot...
Bot is running! Press Ctrl+C to stop.
```

## 💬 Використання

### Команди бота

- `/start` - Привітальне повідомлення та інструкції
- `/help` - Допомога по використанню
- `/positions <адреса_гаманця>` - Показати активні позиції гаманця

### Приклади

1. **Використання команди:**
   ```
   /positions 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
   ```

2. **Просто надішліть адресу:**
   ```
   0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb
   ```

Бот автоматично розпізнає Ethereum адресу та покаже позиції!

## 📁 Структура проекту

```
polymarketmonitor/
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── polymarket.py      # Модуль для роботи з Polymarket API
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── bot.py             # Основна логіка бота
│   │   └── handlers.py        # Обробники команд
│   └── utils/
│       ├── __init__.py
│       └── validators.py      # Утиліти для валідації
├── main.py                    # Точка входу
├── requirements.txt           # Залежності
├── .env.example              # Приклад конфігурації
├── .gitignore
└── README.md
```

## 🔧 Налаштування

### Змінні середовища

| Змінна | Опис | Обов'язкова |
|--------|------|-------------|
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота від BotFather | Так |

## 📝 Приклад виводу

```
💼 Позиції гаманця: 0x742d35Cc...
📊 Знайдено позицій: 3

──────────────────────────────

1. 📊 Позиція #a1b2c3d4...
├ Результат: Yes
├ Розмір: 100.00
├ Середня ціна: 0.65
├ Вартість: 65.00
└ Ринок: market_abc123...

📝 Will Bitcoin reach $100k in 2024?
```

## 🤝 Внесок

Ласкаво просимо до участі! Будь ласка:

1. Форкніть проект
2. Створіть feature-гілку (`git checkout -b feature/AmazingFeature`)
3. Закомітьте зміни (`git commit -m 'Add some AmazingFeature'`)
4. Запуште в гілку (`git push origin feature/AmazingFeature`)
5. Відкрийте Pull Request

## 📄 Ліцензія

Цей проект розповсюджується під ліцензією MIT. Дивіться файл `LICENSE` для деталей.

## ⚠️ Застереження

Цей бот призначений тільки для інформаційних цілей. Він не є фінансовою порадою. Завжди проводьте власне дослідження перед прийняттям інвестиційних рішень.

## 📞 Підтримка

Якщо у вас виникли питання або проблеми:

1. Перевірте [Issues](https://github.com/yourusername/polymarketmonitor/issues)
2. Створіть новий Issue якщо ваша проблема ще не описана

## 🔗 Корисні посилання

- [Polymarket](https://polymarket.com/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)

---

Зроблено з ❤️ для спільноти Polymarket

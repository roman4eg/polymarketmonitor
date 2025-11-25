# Polymarket Monitor Bot 🤖

Telegram бот для моніторингу активних ставок на Polymarket за адресою Ethereum гаманця з автоматичними сповіщеннями.

## 📋 Опис

Цей бот дозволяє відстежувати гаманці на Polymarket та отримувати миттєві сповіщення про нові ставки. Підтримує фільтрацію по ціні входу та автоматичний моніторинг кожні 10 секунд.

## ✨ Функціональність

### 📊 Перегляд позицій
- 🔍 Пошук активних позицій за адресою гаманця
- 📊 Відображення детальної інформації про кожну позицію
- 💰 Показ P&L (прибутку/збитку) з відсотками
- ✅ Автоматична валідація Ethereum адрес

### 🔔 Watchlist та моніторинг
- 👀 Додавання гаманців до watchlist
- ⏱ Автоматична перевірка нових позицій кожні 10 секунд
- 🎯 Фільтрація по ціні входу (наприклад, тільки ставки ≤ $0.70)
- 🔔 Миттєві сповіщення про нові ставки
- 📝 Відстеження історії позицій

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

### Локальний запуск

```bash
python main.py
```

Якщо все налаштовано правильно, ви побачите повідомлення:

```
Starting Polymarket Monitor Bot...
Bot is running! Press Ctrl+C to stop.
Monitoring enabled - checking for new positions every 10 seconds
```

### 🖥 Розгортання на Ubuntu сервері

**Швидкий старт (5 хвилин):**

```bash
# 1. Клонуйте репозиторій
git clone https://github.com/roman4eg/polymarketmonitor.git
cd polymarketmonitor

# 2. Запустіть автоматичне встановлення
bash deploy.sh

# 3. Додайте токен в .env
nano .env

# 4. Запустіть в screen
screen -S polymarket-bot
source venv/bin/activate
python3 main.py
# Від'єднайтеся: Ctrl+A, потім D
```

📖 **Детальна інструкція:** [DEPLOYMENT.md](DEPLOYMENT.md) | [Швидкий старт](QUICK_START.md)

## 💬 Використання

### 📊 Команди перегляду

- `/positions <адреса>` - Показати всі активні позиції гаманця
- Або просто надішліть адресу гаманця без команди!

### 🔔 Команди моніторингу

- `/watchlist` - Показати ваш список відстеження
- `/add <адреса>` - Додати гаманець до watchlist
- `/remove <адреса>` - Видалити гаманець з watchlist
- `/setfilter <ціна>` - Встановити макс. ціну входу (0-1)

### ℹ️ Інше

- `/start` - Привітальне повідомлення
- `/help` - Детальна допомога

### 💡 Приклад використання

```
# Перегляд позицій
/positions 0x751a2b8687e9ce69c68e7e4e8e8b0a1b31b2f1ae

# Додавання до watchlist
/add 0x751a2b8687e9ce69c68e7e4e8e8b0a1b31b2f1ae

# Встановлення фільтру (тільки ставки ≤ $0.70)
/setfilter 0.7

# Тепер отримуватимете сповіщення про нові ставки автоматично! 🔔
```

## 📁 Структура проекту

```
polymarketmonitor/
├── src/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   └── polymarket.py           # Модуль для роботи з Polymarket API
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── bot.py                  # Основна логіка бота
│   │   ├── handlers.py             # Обробники команд
│   │   └── monitor.py              # Фоновий моніторинг позицій
│   └── utils/
│       ├── __init__.py
│       ├── database.py             # SQLite база даних
│       └── validators.py           # Утиліти для валідації
├── data/                           # Директорія для бази даних
│   └── watchlist.db               # SQLite база (створюється автоматично)
├── main.py                         # Точка входу
├── deploy.sh                       # Скрипт автоматичного деплою
├── requirements.txt                # Залежності Python
├── .env.example                    # Приклад конфігурації
├── polymarket-bot.service.example  # Приклад systemd service
├── DEPLOYMENT.md                   # Детальна інструкція по деплою
├── QUICK_START.md                  # Швидкий старт
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

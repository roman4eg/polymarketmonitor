# 🚀 Встановлення на Ubuntu сервер

Детальна інструкція по розгортанню Polymarket Monitor Bot на віддаленому Ubuntu сервері з запуском в screen.

## 📋 Вимоги

- Ubuntu 20.04 або новіше
- Python 3.8+
- Git
- SSH доступ до сервера

---

## 🔧 Крок 1: Підключення до сервера

```bash
# Підключіться до вашого сервера через SSH
ssh user@your-server-ip

# Або якщо використовуєте ключ
ssh -i /path/to/key.pem user@your-server-ip
```

---

## 📦 Крок 2: Встановлення необхідних пакетів

```bash
# Оновіть список пакетів
sudo apt update && sudo apt upgrade -y

# Встановіть Python 3, pip, venv та screen
sudo apt install -y python3 python3-pip python3-venv git screen

# Перевірте версії
python3 --version  # Має бути 3.8 або новіше
screen --version
```

---

## 📥 Крок 3: Клонування репозиторію

```bash
# Перейдіть в домашню директорію
cd ~

# Клонуйте репозиторій
git clone https://github.com/roman4eg/polymarketmonitor.git

# Перейдіть в директорію проекту
cd polymarketmonitor
```

---

## 🐍 Крок 4: Створення віртуального середовища

```bash
# Створіть віртуальне середовище
python3 -m venv venv

# Активуйте віртуальне середовище
source venv/bin/activate

# Після активації ви побачите (venv) перед командним рядком
```

---

## 📚 Крок 5: Встановлення залежностей

```bash
# Оновіть pip
pip install --upgrade pip

# Встановіть залежності проекту
pip install -r requirements.txt

# Перевірте що всі пакети встановлені
pip list
```

---

## ⚙️ Крок 6: Налаштування .env файлу

```bash
# Створіть .env файл з прикладу
cp .env.example .env

# Відредагуйте .env файл
nano .env
```

У nano редакторі додайте ваш токен:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_from_BotFather
```

**Збережіть файл:**
- Натисніть `Ctrl + O` (збереження)
- Натисніть `Enter` (підтвердження)
- Натисніть `Ctrl + X` (вихід)

---

## 🧪 Крок 7: Тестовий запуск

```bash
# Переконайтеся що venv активовано
source venv/bin/activate

# Запустіть бота для тесту
python3 main.py

# Якщо все працює, ви побачите:
# Starting Polymarket Monitor Bot...
# Bot is running! Press Ctrl+C to stop.
# Monitoring enabled - checking for new positions every 10 seconds

# Зупиніть бота: Ctrl+C
```

---

## 📺 Крок 8: Запуск в Screen

### Створення нової screen сесії

```bash
# Створіть нову screen сесію з назвою "polymarket-bot"
screen -S polymarket-bot
```

### Запуск бота в screen

```bash
# Активуйте віртуальне середовище (якщо ще не активовано)
source ~/polymarketmonitor/venv/bin/activate

# Перейдіть в директорію проекту
cd ~/polymarketmonitor

# Запустіть бота
python3 main.py
```

### Від'єднання від screen сесії

**ВАЖЛИВО:** Щоб залишити бота працюючим та вийти з screen:
```
Натисніть: Ctrl + A, потім D (detach)
```

Ви побачите повідомлення: `[detached from 12345.polymarket-bot]`

---

## 🔍 Крок 9: Управління Screen сесіями

### Перегляд активних сесій

```bash
# Показати список всіх screen сесій
screen -ls

# Вивід буде приблизно таким:
# There is a screen on:
#     12345.polymarket-bot	(Detached)
# 1 Socket in /run/screen/S-user.
```

### Повернення до запущеної сесії

```bash
# Приєднатися до сесії за назвою
screen -r polymarket-bot

# Або за ID
screen -r 12345
```

### Зупинка бота

```bash
# Спочатку приєднайтеся до сесії
screen -r polymarket-bot

# Зупиніть бота
Ctrl + C

# Закрийте screen сесію
exit
```

### Вимкнення screen сесії без входу

```bash
# Видалити зависшу сесію (якщо потрібно)
screen -X -S polymarket-bot quit
```

---

## 🔄 Крок 10: Автоматичний запуск після перезавантаження

### Варіант 1: Systemd Service (рекомендовано)

Створіть systemd service файл:

```bash
sudo nano /etc/systemd/system/polymarket-bot.service
```

Додайте наступний вміст:

```ini
[Unit]
Description=Polymarket Monitor Bot
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/polymarketmonitor
Environment="PATH=/home/YOUR_USERNAME/polymarketmonitor/venv/bin"
ExecStart=/home/YOUR_USERNAME/polymarketmonitor/venv/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Замініть `YOUR_USERNAME` на ваше ім'я користувача!**

Активуйте service:

```bash
# Перезавантажте systemd
sudo systemctl daemon-reload

# Увімкніть автозапуск
sudo systemctl enable polymarket-bot

# Запустіть сервіс
sudo systemctl start polymarket-bot

# Перевірте статус
sudo systemctl status polymarket-bot
```

Керування сервісом:

```bash
# Зупинити
sudo systemctl stop polymarket-bot

# Перезапустити
sudo systemctl restart polymarket-bot

# Переглянути логи
sudo journalctl -u polymarket-bot -f
```

### Варіант 2: Cron з Screen

```bash
# Відкрийте crontab
crontab -e

# Додайте рядок для запуску при перезавантаженні:
@reboot cd /home/YOUR_USERNAME/polymarketmonitor && /usr/bin/screen -dmS polymarket-bot /home/YOUR_USERNAME/polymarketmonitor/venv/bin/python3 main.py
```

---

## 📊 Крок 11: Моніторинг та логування

### Перегляд логів в реальному часі

```bash
# Якщо використовуєте screen
screen -r polymarket-bot

# Якщо використовуєте systemd
sudo journalctl -u polymarket-bot -f
```

### Створення окремого лог файлу (опціонально)

Змініть `main.py` для логування в файл:

```bash
nano main.py
```

Або запускайте з перенаправленням:

```bash
python3 main.py >> logs/bot.log 2>&1
```

---

## 🔐 Крок 12: Безпека

```bash
# Обмежте права доступу до .env файлу
chmod 600 .env

# Перевірте що .env не доданий в git
cat .gitignore | grep .env
```

---

## 🆘 Troubleshooting

### Проблема: "Permission denied"

```bash
# Надайте права на виконання
chmod +x main.py
```

### Проблема: "ModuleNotFoundError"

```bash
# Переконайтеся що venv активовано
source venv/bin/activate

# Переустановіть залежності
pip install -r requirements.txt --force-reinstall
```

### Проблема: Screen не запускається

```bash
# Перевірте що screen встановлений
which screen

# Встановіть якщо немає
sudo apt install screen
```

### Проблема: База даних не створюється

```bash
# Створіть директорію для бази даних
mkdir -p data

# Перевірте права
ls -la data/
```

---

## ✅ Швидка довідка команд

```bash
# Базові команди
screen -S polymarket-bot              # Створити нову сесію
Ctrl+A, D                              # Від'єднатися від сесії
screen -ls                             # Список сесій
screen -r polymarket-bot               # Приєднатися до сесії
screen -X -S polymarket-bot quit       # Закрити сесію

# Оновлення бота
cd ~/polymarketmonitor
git pull
source venv/bin/activate
pip install -r requirements.txt
# Перезапустіть бота

# Systemd (якщо використовуєте)
sudo systemctl start polymarket-bot    # Запустити
sudo systemctl stop polymarket-bot     # Зупинити
sudo systemctl restart polymarket-bot  # Перезапустити
sudo systemctl status polymarket-bot   # Статус
```

---

## 🎉 Готово!

Ваш бот тепер працює на віддаленому сервері!

**Перевірте роботу:**
1. Відкрийте Telegram
2. Знайдіть вашого бота
3. Надішліть `/start`
4. Додайте гаманець: `/add 0xадреса`
5. Встановіть фільтр: `/setfilter 0.7`

Сповіщення будуть приходити автоматично кожні 10 секунд! 🔔

# ⚡ Швидкий старт для Ubuntu сервера

## 🚀 За 5 хвилин до запуску

### 1. Підключіться до сервера
```bash
ssh user@your-server-ip
```

### 2. Клонуйте та перейдіть в проект
```bash
cd ~
git clone https://github.com/roman4eg/polymarketmonitor.git
cd polymarketmonitor
```

### 3. Запустіть скрипт автоматичного встановлення
```bash
bash deploy.sh
```

### 4. Додайте токен бота
```bash
nano .env
```
Замініть `your_bot_token_here` на ваш токен від @BotFather

### 5. Запустіть в screen
```bash
# Створіть screen сесію
screen -S polymarket-bot

# Активуйте venv та запустіть
source venv/bin/activate
python3 main.py

# Від'єднайтеся: Ctrl+A, потім D
```

## ✅ Готово!

Бот працює у фоні. Для повернення:
```bash
screen -r polymarket-bot
```

---

## 📋 Корисні команди

### Screen управління
```bash
screen -ls                    # Список сесій
screen -r polymarket-bot      # Приєднатися
screen -X -S polymarket-bot quit  # Закрити сесію
```

### Оновлення бота
```bash
cd ~/polymarketmonitor
git pull
source venv/bin/activate
pip install -r requirements.txt
# Перезапустіть бота в screen
```

### Перегляд логів
```bash
# Приєднайтеся до screen сесії
screen -r polymarket-bot
```

---

## 🔄 Автозапуск через systemd (опціонально)

### Швидке налаштування:
```bash
cd ~/polymarketmonitor

# Створіть директорію для логів
mkdir -p logs

# Скопіюйте service файл
sudo cp polymarket-bot.service.example /etc/systemd/system/polymarket-bot.service

# Відредагуйте service (замініть YOUR_USERNAME на ваше ім'я)
sudo nano /etc/systemd/system/polymarket-bot.service

# Активуйте
sudo systemctl daemon-reload
sudo systemctl enable polymarket-bot
sudo systemctl start polymarket-bot
```

### Команди systemd:
```bash
sudo systemctl status polymarket-bot   # Статус
sudo systemctl restart polymarket-bot  # Перезапуск
sudo systemctl stop polymarket-bot     # Зупинка
sudo journalctl -u polymarket-bot -f   # Логи в реальному часі
```

---

## 💡 Перші кроки з ботом

1. Відкрийте Telegram та знайдіть вашого бота
2. Надішліть `/start`
3. Додайте гаманець для моніторингу:
   ```
   /add 0x751a2b8687e9ce69c68e7e4e8e8b0a1b31b2f1ae
   ```
4. Встановіть фільтр по ціні (опціонально):
   ```
   /setfilter 0.7
   ```
5. Отримуйте сповіщення про нові ставки автоматично!

---

**Детальна інструкція:** [DEPLOYMENT.md](DEPLOYMENT.md)

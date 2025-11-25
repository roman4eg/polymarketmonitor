#!/bin/bash

# Скрипт для швидкого деплою Polymarket Monitor Bot на Ubuntu сервер

set -e  # Зупинити при помилці

echo "🚀 Polymarket Monitor Bot - Deployment Script"
echo "=============================================="
echo ""

# Кольори для виводу
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Функція для виводу статусу
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Перевірка що скрипт запущено на Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    print_error "Цей скрипт призначений для Linux систем"
    exit 1
fi

# Крок 1: Перевірка Python
echo "Крок 1/6: Перевірка Python..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d " " -f 2)
    print_status "Python $PYTHON_VERSION встановлено"

    # Перевірка python3-venv
    if ! python3 -m venv --help &> /dev/null; then
        print_warning "python3-venv не встановлено"
        echo "Встановлюємо python3-venv..."
        sudo apt install -y python3-venv
        print_status "python3-venv встановлено"
    fi
else
    print_error "Python 3 не знайдено"
    echo "Встановіть: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

# Крок 2: Перевірка screen
echo "Крок 2/6: Перевірка screen..."
if command -v screen &> /dev/null; then
    print_status "Screen встановлено"
else
    print_warning "Screen не знайдено"
    echo "Встановлюємо screen..."
    sudo apt install -y screen
    print_status "Screen встановлено"
fi

# Крок 3: Створення віртуального середовища
echo "Крок 3/6: Налаштування віртуального середовища..."
if [ ! -f "venv/bin/activate" ]; then
    # Видаляємо стару директорію якщо вона існує але пошкоджена
    if [ -d "venv" ]; then
        rm -rf venv
    fi
    python3 -m venv venv
    if [ -f "venv/bin/activate" ]; then
        print_status "Віртуальне середовище створено"
    else
        print_error "Не вдалося створити віртуальне середовище"
        echo "Встановіть python3-venv: sudo apt install python3-venv"
        exit 1
    fi
else
    print_status "Віртуальне середовище вже існує"
fi

# Крок 4: Встановлення залежностей
echo "Крок 4/6: Встановлення залежностей..."
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
print_status "Залежності встановлено"

# Крок 5: Перевірка .env файлу
echo "Крок 5/6: Перевірка конфігурації..."
if [ ! -f ".env" ]; then
    print_warning ".env файл не знайдено"
    cp .env.example .env
    print_status ".env файл створено з прикладу"
    echo ""
    print_warning "ВАЖЛИВО: Відредагуйте .env файл та додайте ваш TELEGRAM_BOT_TOKEN"
    echo "Використайте: nano .env"
    echo ""
else
    # Перевірка чи є токен
    if grep -q "your_bot_token_here" .env; then
        print_warning "УВАГА: Необхідно встановити TELEGRAM_BOT_TOKEN в .env файлі"
        echo "Використайте: nano .env"
    else
        print_status ".env файл налаштовано"
    fi
fi

# Крок 6: Створення директорії для бази даних
echo "Крок 6/6: Підготовка бази даних..."
mkdir -p data
print_status "Директорія data створена"

echo ""
echo "=============================================="
echo -e "${GREEN}✓ Встановлення завершено!${NC}"
echo "=============================================="
echo ""
echo "Для запуску бота в screen виконайте:"
echo ""
echo "  screen -S polymarket-bot"
echo "  source venv/bin/activate"
echo "  python3 main.py"
echo ""
echo "Для від'єднання від screen: Ctrl+A, потім D"
echo "Для повернення: screen -r polymarket-bot"
echo ""
echo "Детальна інструкція: DEPLOYMENT.md"
echo ""

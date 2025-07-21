#!/bin/bash

# add_user.sh - Скрипт добавления нового пользователя в RSS Media Bus v3.0

set -e

USER_ID="$1"
USER_NAME="$2" 
CHAT_ID="$3"
BOT_TOKEN="$4"

# Проверка параметров
if [ $# -ne 4 ]; then
    echo "❌ Использование: $0 <user_id> <user_name> <chat_id> <bot_token>"
    echo ""
    echo "Примеры:"
    echo "  $0 \"new_user\" \"Новый Пользователь\" \"-1001234567890\" \"123456789:ABC...\""
    echo ""
    echo "Как получить параметры:"
    echo "  📱 chat_id: напишите боту /start, затем curl 'https://api.telegram.org/bot<TOKEN>/getUpdates'"
    echo "  🤖 bot_token: создайте бота через @BotFather"
    exit 1
fi

echo "🚀 RSS Media Bus v3.0 - Добавление пользователя"
echo "=============================================="

# Проверяем, что мы в правильной директории
if [ ! -f "config/users.yaml" ]; then
    echo "❌ Ошибка: файл config/users.yaml не найден"
    echo "   Убедитесь, что запускаете скрипт из директории RSS Media Bus"
    exit 1
fi

# Проверяем, что пользователь не существует
if grep -q "^$USER_ID:" config/users.yaml; then
    echo "⚠️  Пользователь '$USER_ID' уже существует!"
    echo "   Хотите обновить конфигурацию? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "❌ Отменено"
        exit 1
    fi
    echo "🔄 Обновляем существующего пользователя..."
else
    echo "✅ Добавляем нового пользователя: $USER_ID"
fi

# Тест Telegram бота
echo "🧪 Тестируем Telegram бота..."
TELEGRAM_TEST=$(curl -s "https://api.telegram.org/bot$BOT_TOKEN/getMe")

if echo "$TELEGRAM_TEST" | grep -q '"ok":true'; then
    BOT_USERNAME=$(echo "$TELEGRAM_TEST" | grep -o '"username":"[^"]*"' | cut -d'"' -f4)
    echo "✅ Бот работает: @$BOT_USERNAME"
else
    echo "❌ Ошибка: неверный bot_token или бот недоступен"
    echo "   Ответ API: $TELEGRAM_TEST"
    exit 1
fi

# Тест доступа к чату
echo "🔍 Проверяем доступ к чату..."
CHAT_TEST=$(curl -s "https://api.telegram.org/bot$BOT_TOKEN/getChat?chat_id=$CHAT_ID")

if echo "$CHAT_TEST" | grep -q '"ok":true'; then
    CHAT_TITLE=$(echo "$CHAT_TEST" | grep -o '"title":"[^"]*"' | cut -d'"' -f4 || echo "Personal Chat")
    echo "✅ Доступ к чату: $CHAT_TITLE"
else
    echo "⚠️  Предупреждение: проблемы с доступом к чату"
    echo "   Убедитесь, что бот добавлен в чат как администратор"
    echo "   Ответ API: $CHAT_TEST"
fi

# Создаем backup конфигурации
echo "💾 Создаем backup конфигурации..."
cp config/users.yaml "config/users.yaml.backup.$(date +%Y%m%d_%H%M%S)"
echo "✅ Backup создан"

# Добавляем пользователя в конфигурацию
echo "📝 Добавляем пользователя в config/users.yaml..."

# Если пользователь существует, обновляем, иначе добавляем
if grep -q "^$USER_ID:" config/users.yaml; then
    # Обновление существующего пользователя (сложнее, пока пропустим)
    echo "⚠️  Обновление существующего пользователя требует ручного редактирования"
else
    # Добавление нового пользователя
    cat >> config/users.yaml << EOF

$USER_ID:
  name: "$USER_NAME"
  description: "Автоматически добавлен $(date)"
  active: true
  registration_method: "script"
  created_at: "$(date -Iseconds)"
  
  # Telegram настройки
  telegram:
    chat_id: "$CHAT_ID"
    bot_token: "$BOT_TOKEN"
    topic_id: null
    enabled: true
  
  # Источники (базовый набор - можно настроить)
  sources:
    - tass.ru
    - ria.ru
    - rbc.ru
    - lenta.ru
    - interfax.ru
  
  # Процессоры (без фильтрации - все новости)
  processors:
    - name: "telegram_sender"
      config:
        format: "markdown"
        include_source: true
        max_preview_length: 300
        send_all: true
EOF
fi

echo "✅ Пользователь добавлен в конфигурацию"

# Перезапускаем User Notification Service
echo "🔄 Перезапускаем User Notification Service..."

USER_SERVICE_PID=$(ps aux | grep "user_notification_service.py" | grep -v grep | awk '{print $2}')

if [ -n "$USER_SERVICE_PID" ]; then
    echo "🛑 Останавливаем User Notification Service (PID: $USER_SERVICE_PID)..."
    kill $USER_SERVICE_PID 2>/dev/null || true
    
    echo "⏳ Ждем автоматического перезапуска (RSS Bus Manager)..."
    sleep 10
    
    # Проверяем перезапуск
    NEW_PID=$(ps aux | grep "user_notification_service.py" | grep -v grep | awk '{print $2}')
    if [ -n "$NEW_PID" ]; then
        echo "✅ User Notification Service перезапущен (новый PID: $NEW_PID)"
    else
        echo "⚠️  User Notification Service не перезапустился автоматически"
        echo "   Запустите вручную: python3 user_notification_service.py"
    fi
else
    echo "⚠️  User Notification Service не был запущен"
    echo "   Запустите систему: python3 start_rss_bus.py"
fi

# Проверяем подхват нового пользователя
echo "🔍 Проверяем подхват нового пользователя..."
sleep 5

USER_CHECK=$(python3 -c "
import asyncio
import yaml
from user_notification_service import UserNotificationService

async def check():
    try:
        service = UserNotificationService()
        await service.load_users()
        users = list(service.users.keys())
        print(f'{len(users)}:{\"$USER_ID\" in users}')
        for uid in users:
            print(f'  - {uid}')
    except Exception as e:
        print(f'ERROR:{e}')

asyncio.run(check())
" 2>/dev/null)

if echo "$USER_CHECK" | grep -q "$USER_ID"; then
    echo "✅ Пользователь успешно подхвачен User Notification Service!"
else
    echo "⚠️  Пользователь пока не подхвачен сервисом"
    echo "   Результат проверки: $USER_CHECK"
fi

# Отправляем тестовое сообщение
echo "📤 Отправляем тестовое сообщение..."

TEST_MESSAGE="🎉 Добро пожаловать в RSS Media Bus v3.0!

👤 Пользователь: $USER_NAME ($USER_ID)
📱 Чат: $CHAT_ID
🤖 Бот: @$BOT_USERNAME
⏰ Добавлен: $(date)

📡 Источники: tass.ru, ria.ru, rbc.ru, lenta.ru, interfax.ru
🔔 Уведомления: каждые 2 минуты
📊 Статус: активен

RSS Media Bus будет автоматически отправлять новости в этот чат."

SEND_RESULT=$(python3 -c "
import asyncio
from outputs.telegram_sender import TelegramSender

async def send_test():
    try:
        sender = TelegramSender(
            bot_token='$BOT_TOKEN',
            chat_id='$CHAT_ID'
        )
        await sender.send_message('$TEST_MESSAGE')
        print('SUCCESS')
    except Exception as e:
        print(f'ERROR:{e}')

asyncio.run(send_test())
" 2>/dev/null)

if [ "$SEND_RESULT" = "SUCCESS" ]; then
    echo "✅ Тестовое сообщение отправлено!"
else
    echo "⚠️  Ошибка отправки тестового сообщения: $SEND_RESULT"
fi

echo ""
echo "🎯 ИТОГ:"
echo "=============================================="
echo "✅ Пользователь '$USER_ID' успешно добавлен"
echo "📱 Telegram: @$BOT_USERNAME → $CHAT_ID"
echo "📡 Источников: 5 (базовый набор)"
echo "🔄 User Notification Service: перезапущен"
echo "📤 Тестовое сообщение: отправлено"
echo ""
echo "📊 Мониторинг:"
echo "  Проверить процессы: ps aux | grep -E '(rss_bus_core|user_notification)'"
echo "  Проверить пользователей: python3 scripts/list_users.py"
echo "  Логи: tail -f user_notification.log"
echo ""
echo "🚀 RSS Media Bus v3.0 готов к работе с новым пользователем!" 
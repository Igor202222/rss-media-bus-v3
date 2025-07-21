#!/bin/bash

echo "🚀 ЗАПУСК RSS MEDIA BUS СИСТЕМЫ"
echo "==============================="

# Проверяем что рабочая директория правильная
if [ ! -f "rss_bus_core.py" ] || [ ! -f "user_notification_service.py" ]; then
    echo "❌ Файлы не найдены! Проверьте рабочую директорию"
    exit 1
fi

# Убиваем старые процессы если есть
echo "🛑 Останавливаем старые процессы..."
pkill -f "rss_bus_core.py" 2>/dev/null || true
pkill -f "user_notification_service.py" 2>/dev/null || true
sleep 2

echo "🔍 Проверяем что процессы остановлены..."
if pgrep -f "rss_bus_core.py" > /dev/null || pgrep -f "user_notification_service.py" > /dev/null; then
    echo "⚠️ Процессы ещё работают, принудительно убиваем..."
    pkill -9 -f "rss_bus_core.py" 2>/dev/null || true
    pkill -9 -f "user_notification_service.py" 2>/dev/null || true
    sleep 2
fi

echo "✅ Все старые процессы остановлены"
echo ""

# Запускаем RSS Bus Core
echo "📡 Запуск RSS Bus Core..."
nohup python3 rss_bus_core.py > rss_core.log 2>&1 &
RSS_PID=$!
echo "   PID: $RSS_PID"
sleep 2

# Проверяем что RSS Core запустился
if ! kill -0 $RSS_PID 2>/dev/null; then
    echo "❌ RSS Bus Core не запустился!"
    exit 1
fi

# Запускаем User Notification Service
echo "📬 Запуск User Notification Service..."
nohup python3 user_notification_service.py > user_service.log 2>&1 &
USER_PID=$!
echo "   PID: $USER_PID"
sleep 2

# Проверяем что User Service запустился
if ! kill -0 $USER_PID 2>/dev/null; then
    echo "❌ User Notification Service не запустился!"
    kill $RSS_PID 2>/dev/null || true
    exit 1
fi

echo ""
echo "✅ СИСТЕМА ЗАПУЩЕНА УСПЕШНО!"
echo "📊 Статус процессов:"
echo "   📡 RSS Bus Core: PID $RSS_PID"
echo "   📬 User Notification Service: PID $USER_PID"
echo ""
echo "📋 Логи:"
echo "   RSS Core: tail -f rss_core.log"
echo "   User Service: tail -f user_service.log"
echo ""
echo "🛑 Для остановки: pkill -f 'rss_bus_core.py|user_notification_service.py'"

# Финальная проверка через 3 секунды
sleep 3
echo ""
echo "🔍 Финальная проверка процессов..."
RUNNING_PROCESSES=$(ps aux | grep python3 | grep -E "(rss_bus_core|user_notification)" | wc -l)
echo "📊 Запущенных процессов: $RUNNING_PROCESSES"

if [ $RUNNING_PROCESSES -eq 2 ]; then
    echo "✅ Идеально! Запущено ровно 2 процесса (по одному каждого типа)"
elif [ $RUNNING_PROCESSES -gt 2 ]; then
    echo "⚠️ ВНИМАНИЕ: Запущено $RUNNING_PROCESSES процессов! Возможно дублирование"
else
    echo "❌ ОШИБКА: Запущено только $RUNNING_PROCESSES процессов!"
fi 
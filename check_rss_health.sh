#!/bin/bash

echo "🩺 RSS HEALTH CHECK - Проверка состояния источников"
echo "=================================================================="

# Проверяем запущенные процессы
echo "📊 ПРОЦЕССЫ:"
RSS_COUNT=$(ps aux | grep -E "(rss_bus_core|user_notification)" | grep -v grep | wc -l)
if [ $RSS_COUNT -eq 2 ]; then
    echo "✅ RSS система работает (2 процесса)"
    ps aux | grep -E "(rss_bus_core|user_notification)" | grep -v grep | awk '{print "   •", $11, "(PID:", $2")"}'
else
    echo "⚠️ RSS система не полностью запущена ($RSS_COUNT/2 процессов)"
fi

echo ""
echo "📁 ЛОГИ И РАЗМЕРЫ:"
for log in rss_core.log user_service.log rss_errors.log; do
    if [ -f "$log" ]; then
        size=$(du -h "$log" | cut -f1)
        echo "   • $log: $size"
    else
        echo "   • $log: отсутствует"
    fi
done

echo ""
echo "🔍 ПОСЛЕДНИЕ ОШИБКИ RSS:"
python3 rss_error_viewer.py log 5 2>/dev/null || echo "   Ошибка получения логов"

echo ""
echo "📊 СТАТИСТИКА БД (последние статьи):"
sqlite3 rss_media_bus.db "
SELECT 
    datetime(MAX(added_date), 'localtime') as last_article,
    COUNT(*) as total_articles,
    COUNT(DISTINCT feed_id) as active_feeds
FROM articles 
WHERE added_date > datetime('now', '-24 hours');" 2>/dev/null || echo "   Ошибка доступа к БД"

echo ""
echo "🚨 ПРОБЛЕМНЫЕ ИСТОЧНИКИ (отключены):"
grep -E "active:\s*false" config/sources.yaml | wc -l | xargs -I {} echo "   Отключено источников: {}"

echo ""
echo "💡 КОМАНДЫ ДЛЯ ДИАГНОСТИКИ:"
echo "   python3 rss_error_viewer.py          - полный отчет об ошибках"
echo "   python3 rss_error_viewer.py log 50   - последние 50 записей лога"  
echo "   python3 rss_error_viewer.py export   - экспорт отчета в JSON"
echo "   tail -f rss_errors.log                - мониторинг ошибок в реальном времени"
echo "   ./start_system.sh                     - перезапуск системы" 
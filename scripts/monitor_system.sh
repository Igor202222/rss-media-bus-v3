#!/bin/bash

# monitor_system.sh - Мониторинг RSS Media Bus v3.0

echo "📊 RSS Media Bus v3.0 - Системный мониторинг"
echo "=============================================="
echo "⏰ $(date)"
echo ""

# Проверка процессов
echo "🔄 ПРОЦЕССЫ:"
echo "----------------------------------------"

RSS_MANAGER_PID=$(ps aux | grep "start_rss_bus.py" | grep -v grep | awk '{print $2}')
RSS_CORE_PID=$(ps aux | grep "rss_bus_core.py" | grep -v grep | awk '{print $2}')
USER_SERVICE_PID=$(ps aux | grep "user_notification_service.py" | grep -v grep | awk '{print $2}')

if [ -n "$RSS_MANAGER_PID" ]; then
    RSS_MANAGER_UPTIME=$(ps -o etime= -p $RSS_MANAGER_PID | tr -d ' ')
    echo "  ✅ RSS Bus Manager    (PID: $RSS_MANAGER_PID, uptime: $RSS_MANAGER_UPTIME)"
else
    echo "  ❌ RSS Bus Manager    (не запущен)"
fi

if [ -n "$RSS_CORE_PID" ]; then
    RSS_CORE_UPTIME=$(ps -o etime= -p $RSS_CORE_PID | tr -d ' ')
    echo "  ✅ RSS Bus Core       (PID: $RSS_CORE_PID, uptime: $RSS_CORE_UPTIME)"
else
    echo "  ❌ RSS Bus Core       (не запущен)"
fi

if [ -n "$USER_SERVICE_PID" ]; then
    USER_SERVICE_UPTIME=$(ps -o etime= -p $USER_SERVICE_PID | tr -d ' ')
    echo "  ✅ User Service       (PID: $USER_SERVICE_PID, uptime: $USER_SERVICE_UPTIME)"
else
    echo "  ❌ User Service       (не запущен)"
fi

echo ""

# Проверка базы данных
echo "🗄️ БАЗА ДАННЫХ:"
echo "----------------------------------------"

if [ -f "rss_media_bus.db" ]; then
    DB_SIZE=$(du -h rss_media_bus.db | cut -f1)
    echo "  📊 Размер БД: $DB_SIZE"
    
    # Общее количество статей
    TOTAL_ARTICLES=$(sqlite3 rss_media_bus.db "SELECT COUNT(*) FROM articles;" 2>/dev/null || echo "ERROR")
    echo "  📰 Всего статей: $TOTAL_ARTICLES"
    
    # Статьи за последний час
    NEW_ARTICLES_HOUR=$(sqlite3 rss_media_bus.db "SELECT COUNT(*) FROM articles WHERE created_at > datetime('now', '-1 hour');" 2>/dev/null || echo "ERROR")
    echo "  📈 Новых за час: $NEW_ARTICLES_HOUR"
    
    # Статьи за последние 24 часа
    NEW_ARTICLES_DAY=$(sqlite3 rss_media_bus.db "SELECT COUNT(*) FROM articles WHERE created_at > datetime('now', '-1 day');" 2>/dev/null || echo "ERROR")
    echo "  📅 Новых за сутки: $NEW_ARTICLES_DAY"
    
    # Топ источников
    echo "  📡 Топ-5 источников:"
    sqlite3 rss_media_bus.db "
    SELECT '    ' || feed_id || ': ' || COUNT(*) 
    FROM articles 
    GROUP BY feed_id 
    ORDER BY COUNT(*) DESC 
    LIMIT 5;
    " 2>/dev/null | while read line; do
        echo "$line"
    done
    
else
    echo "  ❌ База данных не найдена"
fi

echo ""

# Проверка пользователей
echo "👥 ПОЛЬЗОВАТЕЛИ:"
echo "----------------------------------------"

if [ -f "config/users.yaml" ]; then
    # Используем Python для точного подсчета
    USER_STATS=$(python3 -c "
import yaml
try:
    with open('config/users.yaml', 'r', encoding='utf-8') as f:
        users = yaml.safe_load(f) or {}
    
    total = len(users)
    active = sum(1 for u in users.values() if u and u.get('active'))
    telegram_enabled = sum(1 for u in users.values() 
                          if u and u.get('active') and 
                          u.get('telegram', {}).get('enabled'))
    
    print(f'{total}:{active}:{telegram_enabled}')
    
    # Список активных пользователей
    for uid, data in users.items():
        if data and data.get('active'):
            telegram_status = '✅' if data.get('telegram', {}).get('enabled') else '❌'
            sources_count = len(data.get('sources', []))
            print(f'  {telegram_status} {uid}: {sources_count} источников')
    
except Exception as e:
    print(f'ERROR:{e}')
" 2>/dev/null)
    
    if echo "$USER_STATS" | grep -q "ERROR"; then
        echo "  ❌ Ошибка чтения config/users.yaml"
    else
        STATS_LINE=$(echo "$USER_STATS" | head -n1)
        TOTAL_USERS=$(echo "$STATS_LINE" | cut -d: -f1)
        ACTIVE_USERS=$(echo "$STATS_LINE" | cut -d: -f2)
        TELEGRAM_USERS=$(echo "$STATS_LINE" | cut -d: -f3)
        
        echo "  📊 Всего пользователей: $TOTAL_USERS"
        echo "  ✅ Активных: $ACTIVE_USERS"
        echo "  📱 С Telegram: $TELEGRAM_USERS"
        echo ""
        echo "$USER_STATS" | tail -n +2
    fi
else
    echo "  ❌ Файл config/users.yaml не найден"
fi

echo ""

# Проверка источников RSS
echo "📡 RSS ИСТОЧНИКИ:"
echo "----------------------------------------"

if [ -f "config/sources.yaml" ]; then
    SOURCE_STATS=$(python3 -c "
import yaml
try:
    with open('config/sources.yaml', 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        sources = data.get('sources', {}) if data else {}
    
    total = len(sources)
    active = sum(1 for s in sources.values() if s and s.get('active', True))
    
    print(f'  📊 Всего источников: {total}')
    print(f'  ✅ Активных: {active}')
    
    # Группировка по категориям
    groups = {}
    for sid, sdata in sources.items():
        if not sdata:
            continue
        group = sdata.get('group', 'other')
        if group not in groups:
            groups[group] = 0
        if sdata.get('active', True):
            groups[group] += 1
    
    print(f'  📂 По группам:')
    for group, count in groups.items():
        print(f'    {group}: {count}')
        
except Exception as e:
    print(f'ERROR: {e}')
" 2>/dev/null)
    
    echo "$SOURCE_STATS"
else
    echo "  ❌ Файл config/sources.yaml не найден"
fi

echo ""

# Системные ресурсы
echo "💻 СИСТЕМНЫЕ РЕСУРСЫ:"
echo "----------------------------------------"

# CPU и память для наших процессов
if [ -n "$RSS_CORE_PID" ] || [ -n "$USER_SERVICE_PID" ]; then
    echo "  🖥️ Использование ресурсов процессами RSS Media Bus:"
    
    if [ -n "$RSS_CORE_PID" ]; then
        RSS_CORE_CPU=$(ps -o %cpu= -p $RSS_CORE_PID | tr -d ' ')
        RSS_CORE_MEM=$(ps -o %mem= -p $RSS_CORE_PID | tr -d ' ')
        RSS_CORE_VSZ=$(ps -o vsz= -p $RSS_CORE_PID | tr -d ' ')
        echo "    RSS Core: CPU ${RSS_CORE_CPU}%, RAM ${RSS_CORE_MEM}%, VSZ ${RSS_CORE_VSZ}KB"
    fi
    
    if [ -n "$USER_SERVICE_PID" ]; then
        USER_SERVICE_CPU=$(ps -o %cpu= -p $USER_SERVICE_PID | tr -d ' ')
        USER_SERVICE_MEM=$(ps -o %mem= -p $USER_SERVICE_PID | tr -d ' ')
        USER_SERVICE_VSZ=$(ps -o vsz= -p $USER_SERVICE_PID | tr -d ' ')
        echo "    User Service: CPU ${USER_SERVICE_CPU}%, RAM ${USER_SERVICE_MEM}%, VSZ ${USER_SERVICE_VSZ}KB"
    fi
fi

# Общие системные ресурсы
LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | tr -d ' ')
echo "  ⚖️ Load Average: $LOAD_AVG"

DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}')
echo "  💾 Использование диска: $DISK_USAGE"

FREE_MEM=$(free -h | awk '/^Mem:/ {print $3 "/" $2}')
echo "  🧠 Память: $FREE_MEM"

echo ""

# Последняя активность
echo "📊 ПОСЛЕДНЯЯ АКТИВНОСТЬ:"
echo "----------------------------------------"

# Последние логи RSS Core (если есть)
if [ -f "rss_bus_core.log" ]; then
    echo "  📝 Последние действия RSS Core:"
    tail -n 3 rss_bus_core.log | sed 's/^/    /'
fi

# Последние логи User Service (если есть)
if [ -f "user_notification.log" ]; then
    echo "  📝 Последние действия User Service:"
    tail -n 3 user_notification.log | sed 's/^/    /'
fi

# Последние записи в БД
if [ -f "rss_media_bus.db" ]; then
    echo "  📰 Последние статьи в БД:"
    sqlite3 rss_media_bus.db "
    SELECT '    ' || datetime(created_at, 'localtime') || ' - ' || 
           feed_id || ': ' || substr(title, 1, 50) || '...'
    FROM articles 
    ORDER BY created_at DESC 
    LIMIT 3;
    " 2>/dev/null | while read line; do
        echo "$line"
    done
fi

echo ""

# Рекомендации и предупреждения
echo "⚠️ РЕКОМЕНДАЦИИ:"
echo "----------------------------------------"

WARNINGS=0

# Проверка процессов
if [ -z "$RSS_CORE_PID" ]; then
    echo "  🚨 RSS Bus Core не запущен - запустите: python3 start_rss_bus.py"
    WARNINGS=$((WARNINGS + 1))
fi

if [ -z "$USER_SERVICE_PID" ]; then
    echo "  🚨 User Notification Service не запущен"
    WARNINGS=$((WARNINGS + 1))
fi

# Проверка активности
if [ -f "rss_media_bus.db" ]; then
    RECENT_ARTICLES=$(sqlite3 rss_media_bus.db "SELECT COUNT(*) FROM articles WHERE created_at > datetime('now', '-30 minutes');" 2>/dev/null || echo "0")
    if [ "$RECENT_ARTICLES" -eq 0 ]; then
        echo "  ⚠️ Нет новых статей за последние 30 минут - проверьте RSS источники"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# Проверка пользователей
if [ -f "config/users.yaml" ]; then
    TELEGRAM_USERS=$(python3 -c "
import yaml
try:
    with open('config/users.yaml', 'r', encoding='utf-8') as f:
        users = yaml.safe_load(f) or {}
    telegram_enabled = sum(1 for u in users.values() 
                          if u and u.get('active') and 
                          u.get('telegram', {}).get('enabled'))
    print(telegram_enabled)
except:
    print(0)
" 2>/dev/null)
    
    if [ "$TELEGRAM_USERS" -eq 0 ]; then
        echo "  ⚠️ Нет активных пользователей с Telegram - добавьте пользователей"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# Проверка размера БД
if [ -f "rss_media_bus.db" ]; then
    DB_SIZE_MB=$(du -m rss_media_bus.db | cut -f1)
    if [ "$DB_SIZE_MB" -gt 1000 ]; then
        echo "  💾 База данных >1GB - рассмотрите архивирование старых записей"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

if [ "$WARNINGS" -eq 0 ]; then
    echo "  ✅ Всё работает отлично!"
fi

echo ""
echo "=============================================="
echo "📊 Мониторинг завершен - найдено предупреждений: $WARNINGS"
echo "🔄 Для постоянного мониторинга: watch -n 60 './scripts/monitor_system.sh'"
echo "🚀 RSS Media Bus v3.0 Status: $([ "$WARNINGS" -eq 0 ] && echo "HEALTHY" || echo "NEEDS ATTENTION")" 
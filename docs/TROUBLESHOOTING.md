# 🛠️ RSS Media Bus v3.1 - Решение проблем

**Полное руководство по диагностике и исправлению проблем**

## 🚨 Критические проблемы v3.1 (ИСПРАВЛЕНЫ)

### ✅ Проблема 1: Неправильные временные зоны

**Симптомы:**
- User Service "находит" 0 новых статей
- В логах: `📰 Статей найдено ПОСЛЕ last_check: 0`
- RSS Core добавляет статьи, но они не отправляются

**Причина:**
User Service сравнивал Moscow время с UTC базой данных:
```sql
-- НЕПРАВИЛЬНО:
WHERE published_date > ?   -- Moscow время vs UTC база
```

**Диагностика:**
```bash
# Проверить что есть новые статьи в базе
sqlite3 rss_media_bus.db "SELECT datetime(added_date, 'localtime'), feed_id FROM articles ORDER BY added_date DESC LIMIT 5;"

# Проверить last_check пользователя
python3 -c "
from user_notification_service import UserNotificationService
import asyncio
async def check():
    service = UserNotificationService()
    await service.initialize_database()
    await service.load_users()
    print('last_check:', service.last_check_time)
asyncio.run(check())
"
```

**Исправление (УЖЕ СДЕЛАНО):**
```python
# В user_notification_service.py добавлена корректная конвертация:
moscow_tz = pytz.timezone('Europe/Moscow')
if last_check.tzinfo is None:
    moscow_time = moscow_tz.localize(last_check)
else:
    moscow_time = last_check
utc_time = moscow_time.astimezone(pytz.UTC)
utc_str = utc_time.strftime('%Y-%m-%d %H:%M:%S')
cursor.execute(query, (utc_str,))
```

### ✅ Проблема 2: Спам старыми новостями

**Симптомы:**
- При перезапуске User Service отправляет сотни старых статей
- В логах: `📤 Отправлено статей: 443`
- Пользователь получает "завал" старых новостей

**Причина:**
```python
# БЫЛО (плохо):
self.last_check_time[user_id] = datetime.now() - timedelta(hours=3)
```

**Исправление (УЖЕ СДЕЛАНО):**
```python
# СТАЛО (правильно):
self.last_check_time[user_id] = datetime.now()  # Только новые статьи после запуска
```

### ✅ Проблема 3: Дублирование процессов

**Симптомы:**
- Каждая новость приходит 2+ раза
- Команда показывает несколько процессов: `ps aux | grep python3 | grep rss_bus_core | wc -l` > 1

**Причина:**
Множественные экземпляры RSS Core/User Service работали параллельно

**Исправление (УЖЕ СДЕЛАНО):**
Создан скрипт `start_system.sh` с проверкой единственности процессов

### ✅ Проблема 4: "Зависание" RSS Core

**Симптомы:**
- RSS Core показывается как запущенный, но не парсит новые статьи
- Последние статьи в базе старые (час+ назад)
- RSS источники содержат свежие новости

**Исправление (УЖЕ СДЕЛАНО):**
Корректный перезапуск через `start_system.sh`

## 📊 Базовая диагностика

### Быстрая проверка системы

```bash
# 1. Запущены ли процессы? (должно быть ровно 2)
ps aux | grep python3 | grep -E "(rss_bus_core|user_notification)" | wc -l

# 2. Есть ли свежие статьи? (должны быть последние 5-10 минут)
sqlite3 rss_media_bus.db "SELECT datetime(added_date, 'localtime'), feed_id, title FROM articles ORDER BY added_date DESC LIMIT 3;"

# 3. Отправляются ли уведомления? (должны быть в логах)
tail -10 user_service.log | grep "Отправлено статей"

# 4. Нет ли дубликатов? (должен быть пустой результат)
sqlite3 rss_media_bus.db "SELECT title, COUNT(*) FROM articles WHERE added_date > datetime('now', '-1 hour') GROUP BY title HAVING COUNT(*) > 1;"
```

### Проверка RSS источников

```bash
# Проверить доступность RSS источников вручную
curl -s "https://ria.ru/export/rss2/archive/index.xml" | head -20 | grep -E "(title>|pubDate>)"
curl -s "https://tass.ru/rss/v2.xml" | head -20 | grep -E "(title>|pubDate>)"

# Должны быть свежие заголовки с временем последних часов
```

## 🔧 Стандартные решения

### Система не работает

**Первый шаг - полный перезапуск:**
```bash
# Используйте умный скрипт запуска
./start_system.sh
```

Если не помогает:
```bash
# Принудительная очистка и перезапуск
pkill -9 -f "rss_bus_core.py"
pkill -9 -f "user_notification_service.py"
sleep 2
./start_system.sh
```

### RSS Core не парсит

**Диагностика:**
```bash
# Проверить логи RSS Core
tail -20 rss_core.log

# Проверить доступность источников
timeout 10s curl -s "https://ria.ru/export/rss2/archive/index.xml" | head -5

# Проверить конфигурацию источников
python3 -c "
import yaml
with open('config/sources.yaml', 'r', encoding='utf-8') as f:
    sources = yaml.safe_load(f)
print(f'📡 Источников в конфигурации: {len(sources)}')
"
```

**Решение:**
```bash
# Перезапуск только RSS Core
pkill -f "rss_bus_core.py"
sleep 2
nohup python3 rss_bus_core.py > rss_core.log 2>&1 &
```

### User Service не отправляет

**Диагностика:**
```bash
# Проверить конфигурацию пользователя
python3 -c "
from user_notification_service import UserNotificationService
import asyncio

async def check():
    service = UserNotificationService()
    await service.initialize_database()
    await service.load_users()
    
    print(f'👥 Активных пользователей: {len(service.users)}')
    for user_id, last_check in service.last_check_time.items():
        print(f'🕐 {user_id}: last_check = {last_check}')

asyncio.run(check())
"

# Проверить Telegram бота
curl -s "https://api.telegram.org/bot<TOKEN>/getMe"

# Проверить доступ к чату
curl -s "https://api.telegram.org/bot<TOKEN>/getChat?chat_id=<CHAT_ID>"
```

**Решение:**
```bash
# Перезапуск только User Service
pkill -f "user_notification_service.py"
sleep 2
nohup python3 user_notification_service.py > user_service.log 2>&1 &
```

## 🚨 Специфические проблемы

### Дублирование новостей

**Проверка:**
```bash
# Количество процессов (должно быть 2)
ps aux | grep python3 | grep -E "(rss_bus_core|user_notification)" | wc -l

# Дубликаты в базе данных
sqlite3 rss_media_bus.db "
SELECT title, COUNT(*) as count
FROM articles 
WHERE added_date > datetime('now', '-1 hour') 
GROUP BY title 
HAVING COUNT(*) > 1
LIMIT 10;
"
```

**Решение:**
```bash
# Остановить ВСЕ и перезапустить правильно
./start_system.sh
```

### Telegram API ошибки

**Симптомы:**
- В логах: `TelegramError`, `Rate limit`, `Forbidden`

**Диагностика:**
```bash
# Проверить бота
curl -s "https://api.telegram.org/bot<TOKEN>/getMe"

# Проверить права в чате
curl -s "https://api.telegram.org/bot<TOKEN>/getChatMember?chat_id=<CHAT_ID>&user_id=<BOT_ID>"
```

**Решения:**
1. **Rate Limit:** User Service автоматически ждет. Проверить логи на `⏳ Rate limit`
2. **Forbidden:** Бот был удален из чата или потерял права администратора
3. **Invalid token:** Проверить токен бота в `config/users.yaml`

### База данных заблокирована

**Симптомы:**
- `database is locked`
- `unable to open database file`

**Решение:**
```bash
# Проверить блокировки
fuser rss_media_bus.db 2>/dev/null || echo "База не заблокирована"

# Остановить все процессы
pkill -f "rss_bus_core.py"
pkill -f "user_notification_service.py"
sleep 5

# Проверить целостность базы
sqlite3 rss_media_bus.db "PRAGMA integrity_check;"

# Перезапустить
./start_system.sh
```

### Конфигурация повреждена

**Симптомы:**
- `yaml.parser.ParserError`
- `FileNotFoundError`
- `KeyError` при загрузке конфигурации

**Диагностика:**
```bash
# Проверить синтаксис YAML
python3 -c "
import yaml
try:
    with open('config/users.yaml', 'r', encoding='utf-8') as f:
        yaml.safe_load(f)
    print('✅ users.yaml OK')
except Exception as e:
    print(f'❌ users.yaml error: {e}')

try:
    with open('config/sources.yaml', 'r', encoding='utf-8') as f:
        yaml.safe_load(f)
    print('✅ sources.yaml OK')
except Exception as e:
    print(f'❌ sources.yaml error: {e}')
"

# Проверить JSON
python3 -c "
import json
try:
    with open('config/topics_mapping.json', 'r', encoding='utf-8') as f:
        json.load(f)
    print('✅ topics_mapping.json OK')
except Exception as e:
    print(f'❌ topics_mapping.json error: {e}')
"
```

## 📈 Мониторинг и предотвращение

### Автоматический мониторинг

**Скрипт проверки здоровья:**
```bash
#!/bin/bash
# /opt/rss_media_bus/health_check.sh

LOG_FILE="/var/log/rss_health.log"
WORK_DIR="/opt/rss_media_bus"

cd $WORK_DIR

# Проверить процессы
PROCESS_COUNT=$(ps aux | grep python3 | grep -E "(rss_bus_core|user_notification)" | wc -l)

if [ $PROCESS_COUNT -ne 2 ]; then
    echo "$(date): CRITICAL - Found $PROCESS_COUNT processes, expected 2. Restarting..." >> $LOG_FILE
    ./start_system.sh >> $LOG_FILE 2>&1
    exit 1
fi

# Проверить свежесть статей (должны быть новее 10 минут)
RECENT_ARTICLES=$(sqlite3 rss_media_bus.db "SELECT COUNT(*) FROM articles WHERE added_date > datetime('now', '-10 minutes');")

if [ $RECENT_ARTICLES -eq 0 ]; then
    echo "$(date): WARNING - No new articles in last 10 minutes" >> $LOG_FILE
fi

# Проверить дубликаты
DUPLICATES=$(sqlite3 rss_media_bus.db "SELECT COUNT(*) FROM (SELECT title, COUNT(*) FROM articles WHERE added_date > datetime('now', '-1 hour') GROUP BY title HAVING COUNT(*) > 1);")

if [ $DUPLICATES -gt 0 ]; then
    echo "$(date): WARNING - Found $DUPLICATES duplicate articles in last hour" >> $LOG_FILE
fi

echo "$(date): OK - System healthy ($PROCESS_COUNT processes, $RECENT_ARTICLES recent articles)" >> $LOG_FILE
```

**Добавить в crontab:**
```bash
# Проверка каждые 5 минут
*/5 * * * * /opt/rss_media_bus/health_check.sh

# Ротация логов каждый день
0 2 * * * logrotate -f /etc/logrotate.d/rss-media-bus
```

### Логротация

**Конфигурация logrotate:**
```bash
# /etc/logrotate.d/rss-media-bus
/opt/rss_media_bus/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

## 🎯 Профилактика

### Еженедельное обслуживание

```bash
# Скрипт еженедельного обслуживания
#!/bin/bash
# weekly_maintenance.sh

echo "=== RSS Media Bus Weekly Maintenance $(date) ==="

# Очистка старых статей (старше 30 дней)
sqlite3 rss_media_bus.db "DELETE FROM articles WHERE added_date < datetime('now', '-30 days');"
DELETED=$(sqlite3 rss_media_bus.db "SELECT changes();")
echo "Удалено старых статей: $DELETED"

# Вакуум базы данных
sqlite3 rss_media_bus.db "VACUUM;"
echo "База данных оптимизирована"

# Размер базы данных
DB_SIZE=$(du -h rss_media_bus.db | cut -f1)
echo "Размер базы данных: $DB_SIZE"

# Статистика за неделю
WEEKLY_ARTICLES=$(sqlite3 rss_media_bus.db "SELECT COUNT(*) FROM articles WHERE added_date > datetime('now', '-7 days');")
echo "Статей за неделю: $WEEKLY_ARTICLES"

# Перезапуск системы для свежести
echo "Перезапуск системы..."
./start_system.sh

echo "=== Обслуживание завершено ==="
```

### Мониторинг производительности

```bash
# Проверка использования ресурсов
ps aux | grep -E "(rss_bus_core|user_notification)" | grep -v grep | \
awk '{print "Process: " $11 ", CPU: " $3 "%, MEM: " $4 "%, RSS: " $6 "KB"}'

# Размер лог файлов
ls -lh *.log | awk '{print $9 ": " $5}'

# Статистика базы данных
sqlite3 rss_media_bus.db "
SELECT 
    'Total articles: ' || COUNT(*),
    'Last hour: ' || COUNT(CASE WHEN added_date > datetime('now', '-1 hour') THEN 1 END),
    'Today: ' || COUNT(CASE WHEN added_date > datetime('now', '-1 day') THEN 1 END)
FROM articles;
"
```

## 🆘 Экстренное восстановление

### Полное восстановление системы

```bash
#!/bin/bash
# emergency_recovery.sh

echo "🆘 ЭКСТРЕННОЕ ВОССТАНОВЛЕНИЕ RSS MEDIA BUS"

# Убить все процессы принудительно
pkill -9 -f "rss_bus_core.py"
pkill -9 -f "user_notification_service.py"
sleep 2

# Проверить целостность базы данных
echo "Проверка базы данных..."
sqlite3 rss_media_bus.db "PRAGMA integrity_check;"

# Создать резервную копию
echo "Создание резервной копии..."
cp rss_media_bus.db rss_media_bus_backup_$(date +%Y%m%d_%H%M%S).db

# Очистить логи
echo "Очистка логов..."
> rss_core.log
> user_service.log

# Перезапуск системы
echo "Запуск системы..."
./start_system.sh

echo "✅ Восстановление завершено"
```

---

🎯 **RSS Media Bus v3.1** - все критические проблемы исправлены! Используйте это руководство для диагностики и предотвращения проблем. 
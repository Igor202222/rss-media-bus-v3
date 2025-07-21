# 🔄 RSS Media Bus v3.1 - Управление процессами

**Руководство по корректному запуску, мониторингу и управлению процессами**

## 🚀 Запуск системы

### ⚡ Рекомендуемый способ (start_system.sh)

```bash
# Умный запуск с автоматической проверкой единственности
./start_system.sh
```

**Преимущества скрипта:**
- ✅ Останавливает все старые процессы RSS Media Bus
- ✅ Запускает RSS Bus Core (строго 1 экземпляр)
- ✅ Запускает User Notification Service (строго 1 экземпляр)
- ✅ Проверяет отсутствие дублирования процессов
- ✅ Выводит PID процессов и пути к логам
- ✅ Финальная валидация количества процессов

**Вывод успешного запуска:**
```
🚀 ЗАПУСК RSS MEDIA BUS СИСТЕМЫ
===============================
🛑 Останавливаем старые процессы...
✅ Все старые процессы остановлены

📡 Запуск RSS Bus Core...
   PID: 12345
📬 Запуск User Notification Service...
   PID: 12346

✅ СИСТЕМА ЗАПУЩЕНА УСПЕШНО!
📊 Статус процессов:
   📡 RSS Bus Core: PID 12345
   📬 User Notification Service: PID 12346

🔍 Финальная проверка процессов...
📊 Запущенных процессов: 2
✅ Идеально! Запущено ровно 2 процесса (по одному каждого типа)
```

### 🔧 Ручной запуск (только для отладки)

```bash
# 1. Остановить все старые процессы
pkill -f "rss_bus_core.py"
pkill -f "user_notification_service.py"

# 2. Запустить RSS Bus Core
nohup python3 rss_bus_core.py > rss_core.log 2>&1 &
RSS_PID=$!

# 3. Запустить User Notification Service  
nohup python3 user_notification_service.py > user_service.log 2>&1 &
USER_PID=$!

# 4. Проверить что запустились
ps aux | grep python3 | grep -E "(rss_bus_core|user_notification)"
```

## 📊 Мониторинг процессов

### Проверка статуса

```bash
# Количество запущенных процессов (должно быть ровно 2)
ps aux | grep python3 | grep -E "(rss_bus_core|user_notification)" | wc -l

# Детальная информация о процессах
ps aux | grep python3 | grep -E "(rss_bus_core|user_notification)"

# Проверка что процессы живы по PID
kill -0 <PID> && echo "Процесс жив" || echo "Процесс мертв"
```

### Мониторинг логов

```bash
# RSS Bus Core - парсинг источников
tail -f rss_core.log

# User Notification Service - отправка уведомлений
tail -f user_service.log

# Мониторинг в реальном времени
watch -n 30 'tail -5 rss_core.log && echo "---" && tail -5 user_service.log'
```

### Проверка здоровья системы

```bash
# 1. Процессы запущены и работают
ps aux | grep python3 | grep -E "(rss_bus_core|user_notification)"

# 2. RSS Core добавляет новые статьи  
sqlite3 rss_media_bus.db "
SELECT datetime(added_date, 'localtime') as time, feed_id, title 
FROM articles 
ORDER BY added_date DESC 
LIMIT 3;
"

# 3. User Service отправляет уведомления
tail -10 user_service.log | grep "Отправлено статей"

# 4. Нет дублирования статей
sqlite3 rss_media_bus.db "
SELECT title, COUNT(*) as count 
FROM articles 
WHERE added_date > datetime('now', '-1 hour') 
GROUP BY title 
HAVING COUNT(*) > 1;
"
```

## 🛑 Остановка системы

### Корректная остановка

```bash
# Остановить все процессы RSS Media Bus
pkill -f 'rss_bus_core.py|user_notification_service.py'

# Проверить что остановлены (должен быть пустой вывод)
ps aux | grep python3 | grep -E "(rss_bus_core|user_notification)"
```

### Принудительная остановка

```bash
# Принудительное завершение если обычная остановка не работает
pkill -9 -f "rss_bus_core.py"
pkill -9 -f "user_notification_service.py"

# Финальная проверка
ps aux | grep python3 | grep -E "(rss_bus_core|user_notification)" || echo "Все процессы остановлены"
```

## 🔄 Перезапуск системы

### Полный перезапуск

```bash
# Простой и надежный способ
./start_system.sh
```

### Перезапуск отдельного компонента

```bash
# Только RSS Bus Core
pkill -f "rss_bus_core.py"
sleep 2
nohup python3 rss_bus_core.py > rss_core.log 2>&1 &

# Только User Notification Service
pkill -f "user_notification_service.py"
sleep 2
nohup python3 user_notification_service.py > user_service.log 2>&1 &
```

## 🚨 Проблемы и решения

### Дублирование процессов

**Проблема:** Несколько экземпляров RSS Core/User Service работают параллельно

**Симптомы:**
```bash
$ ps aux | grep python3 | grep -E "(rss_bus_core|user_notification)" | wc -l
4  # Должно быть 2!
```

**Решение:**
```bash
# Остановить ВСЕ процессы и перезапустить корректно
./start_system.sh
```

### Зависшие процессы

**Проблема:** Процесс показывается как запущенный, но не работает

**Диагностика:**
```bash
# Проверить активность процесса
strace -p <PID> 2>&1 | head -10

# Проверить использование ресурсов
top -p <PID>

# Проверить логи на ошибки
tail -50 rss_core.log | grep -i error
tail -50 user_service.log | grep -i error
```

**Решение:**
```bash
# Перезапуск зависшего процесса
kill <PID>
sleep 2
./start_system.sh
```

### Процессы не запускаются

**Возможные причины:**
1. Неверная конфигурация
2. Отсутствующие зависимости
3. Права доступа к файлам
4. Заблокированные порты

**Диагностика:**
```bash
# Проверить зависимости
pip install -r requirements.txt

# Проверить конфигурацию
python3 -c "import yaml; print('YAML OK')"
python3 -c "from user_notification_service import UserNotificationService; print('Import OK')"

# Проверить права на файлы
ls -la config/
ls -la *.py

# Запуск в foreground для диагностики
python3 rss_bus_core.py
# В другом терминале:
python3 user_notification_service.py
```

## 📈 Автоматизация и мониторинг

### Автозапуск при загрузке системы

**Через systemd:**
```ini
# /etc/systemd/system/rss-media-bus.service
[Unit]
Description=RSS Media Bus v3.1
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=root
WorkingDirectory=/opt/rss_media_bus
ExecStart=/opt/rss_media_bus/start_system.sh
ExecStop=/usr/bin/pkill -f 'rss_bus_core.py|user_notification_service.py'

[Install]
WantedBy=multi-user.target
```

**Активация:**
```bash
sudo systemctl enable rss-media-bus
sudo systemctl start rss-media-bus
sudo systemctl status rss-media-bus
```

### Мониторинг с автоперезапуском

**Cron скрипт для проверки каждые 5 минут:**
```bash
#!/bin/bash
# check_rss_health.sh

RSS_PROCESSES=$(ps aux | grep python3 | grep -E "(rss_bus_core|user_notification)" | wc -l)

if [ $RSS_PROCESSES -ne 2 ]; then
    echo "$(date): CRITICAL - Found $RSS_PROCESSES processes, expected 2. Restarting..." >> /var/log/rss_health.log
    cd /opt/rss_media_bus
    ./start_system.sh >> /var/log/rss_health.log 2>&1
else
    echo "$(date): OK - System healthy" >> /var/log/rss_health.log
fi
```

**Добавить в crontab:**
```bash
*/5 * * * * /opt/rss_media_bus/check_rss_health.sh
```

### Мониторинг производительности

```bash
# Скрипт мониторинга ресурсов
#!/bin/bash
# monitor_performance.sh

echo "=== RSS Media Bus Performance $(date) ==="

# CPU и память процессов
ps aux | grep -E "(rss_bus_core|user_notification)" | grep -v grep | \
while read USER PID CPU MEM VSZ RSS TTY STAT START TIME COMMAND; do
    echo "Process: $COMMAND"
    echo "  PID: $PID, CPU: $CPU%, MEM: $MEM%, RSS: ${RSS}KB"
done

# Статистика базы данных
echo ""
echo "Database statistics:"
sqlite3 rss_media_bus.db "
SELECT 
    COUNT(*) as total_articles,
    COUNT(CASE WHEN added_date > datetime('now', '-1 hour') THEN 1 END) as last_hour,
    COUNT(CASE WHEN added_date > datetime('now', '-1 day') THEN 1 END) as last_day
FROM articles;
"

# Размер лог файлов
echo ""
echo "Log file sizes:"
ls -lh *.log 2>/dev/null | awk '{print $9, $5}'
```

## 🔧 Конфигурация процессов

### Переменные окружения

```bash
# Опциональные переменные для настройки
export RSS_CHECK_INTERVAL=300      # Интервал парсинга RSS (секунды)
export USER_CHECK_INTERVAL=30      # Интервал проверки уведомлений (секунды)
export LOG_LEVEL=INFO              # Уровень логирования
export MAX_WORKERS=10              # Максимум воркеров для RSS парсинга
```

### Настройка логирования

```python
# В начале rss_bus_core.py и user_notification_service.py
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('system.log'),
        logging.StreamHandler()
    ]
)
```

## 📊 Архитектура процессов

### RSS Bus Core (процесс 1)

**Назначение:** Парсинг RSS источников и сохранение в БД

**Основной цикл:**
```
1. Загрузка списка источников из config/sources.yaml
2. Асинхронный парсинг всех источников (5 минут)
3. Сохранение новых статей в SQLite БД
4. Обновление статистики источников
5. Пауза и повтор
```

**Файлы:**
- `rss_bus_core.py` - главный файл
- `core/` - модули парсинга
- `rss_core.log` - лог файл

### User Notification Service (процесс 2)

**Назначение:** Мониторинг новых статей и отправка уведомлений

**Основной цикл:**
```
1. Загрузка пользователей из config/users.yaml
2. Проверка новых статей в БД (каждые 30 секунд)
3. Фильтрация по источникам пользователя
4. Отправка в Telegram с соблюдением rate limits
5. Обновление last_check времени
6. Пауза и повтор
```

**Файлы:**
- `user_notification_service.py` - главный файл
- `outputs/` - модули отправки
- `user_service.log` - лог файл

### Взаимодействие процессов

```
RSS Sources → RSS Bus Core → SQLite DB → User Service → Telegram
```

**Изолированность:**
- Процессы **независимы** друг от друга
- Единственная точка взаимодействия - SQLite БД
- Остановка одного процесса не влияет на другой
- Каждый процесс имеет свой лог файл

---

🎯 **RSS Media Bus v3.1** обеспечивает стабильную работу через правильное управление процессами и исключение дублирования! 
# 🚀 RSS Media Bus v3.1 - Быстрый старт

**Исправленная и стабильная система мониторинга RSS**

## ⚡ Мгновенный запуск (рекомендуется)

### 1️⃣ Подготовка окружения

```bash
# Клонирование репозитория
git clone <repository-url>
cd rss_media_bus

# Установка зависимостей
pip install -r requirements.txt

# Проверка Python версии (требуется 3.7+)
python3 --version
```

### 2️⃣ Запуск системы одной командой

```bash
# Умный запуск без дублирования процессов
./start_system.sh
```

**✅ Что происходит автоматически:**
- 🛑 Останавливаются все старые процессы RSS Media Bus
- 📡 Запускается RSS Bus Core (1 экземпляр)
- 📬 Запускается User Notification Service (1 экземпляр)
- 🔍 Проверяется отсутствие дублирования процессов
- 📊 Выводится статус и пути к логам

### 3️⃣ Проверка работы

```bash
# Проверить запущенные процессы (должно быть ровно 2)
ps aux | grep python3 | grep -E "(rss_bus_core|user_notification)"

# Мониторинг логов в реальном времени
tail -f rss_core.log        # RSS парсинг
tail -f user_service.log    # Отправка уведомлений
```

**Expected output:**
```
✅ СИСТЕМА ЗАПУЩЕНА УСПЕШНО!
📊 Статус процессов:
   📡 RSS Bus Core: PID 12345
   📬 User Notification Service: PID 12346

📋 Логи:
   RSS Core: tail -f rss_core.log
   User Service: tail -f user_service.log

✅ Идеально! Запущено ровно 2 процесса (по одному каждого типа)
```

## 🔧 Конфигурация пользователя

### Обязательные файлы конфигурации

#### 1. `config/users.yaml` - Пользователи системы
```yaml
all_sources_rss_user:
  telegram:
    chat_id: -1002883915655            # ID Telegram супергруппы
    bot_token: "1234567890:ABC..."     # Токен вашего бота
  sources:
    - tass.ru
    - ria.ru
    - rbc.ru
    - lenta.ru
    - iz.ru
    # ... остальные 41 источник
  processors: []
```

#### 2. `config/topics_mapping.json` - Маппинг источников в топики
```json
{
  "tass.ru": 1,
  "ria.ru": 2, 
  "rbc.ru": 3,
  "lenta.ru": 4,
  "iz.ru": 5
  // ... маппинг для всех 46 источников → 49 топиков
}
```

#### 3. `config/sources.yaml` - RSS источники
```yaml
# Российские источники
- url: "https://tass.ru/rss/v2.xml"
  name: "ТАСС"
  domain: "tass.ru"

- url: "https://ria.ru/export/rss2/archive/index.xml"
  name: "РИА Новости"
  domain: "ria.ru"

# ... остальные источники
```

## 🚨 Исправленные проблемы v3.1

### ✅ Временные зоны
**Проблема:** User Service неправильно сравнивал Moscow время с UTC базой
```python
# БЫЛО (неправильно):
cursor.execute(query, (last_check,))  # Moscow время vs UTC база

# СТАЛО (исправлено):
moscow_tz = pytz.timezone('Europe/Moscow')
moscow_time = moscow_tz.localize(last_check)
utc_time = moscow_time.astimezone(pytz.UTC)
utc_str = utc_time.strftime('%Y-%m-%d %H:%M:%S')
cursor.execute(query, (utc_str,))
```

### ✅ Спам старыми новостями
**Проблема:** При перезапуске отправлялись сотни старых статей
```python
# БЫЛО (плохо):
self.last_check_time[user_id] = datetime.now() - timedelta(hours=3)  # 443 старые статьи

# СТАЛО (правильно):
self.last_check_time[user_id] = datetime.now()  # Только новые статьи после запуска
```

### ✅ Дублирование процессов
**Проблема:** Несколько экземпляров RSS Core/User Service работали параллельно
```bash
# БЫЛО (дублирование):
python3 rss_bus_core.py &           # Процесс 1
python3 rss_bus_core.py &           # Процесс 2 (дублирует новости!)

# СТАЛО (единственность):
./start_system.sh                   # Умная проверка единственности
```

### ✅ "Зависание" RSS Core
**Проблема:** RSS Core переставал парсить новые статьи
```bash
# Решение:
./start_system.sh                   # Корректный перезапуск с мониторингом
```

## 📊 Мониторинг системы

### Проверка здоровья системы

```bash
# 1. Все ли процессы запущены?
ps aux | grep python3 | grep -E "(rss_bus_core|user_notification)"
# Ожидается: ровно 2 процесса

# 2. Добавляются ли новые статьи?
sqlite3 rss_media_bus.db "
SELECT datetime(added_date, 'localtime') as time, feed_id, title 
FROM articles 
ORDER BY added_date DESC 
LIMIT 5;
"

# 3. Нет ли дублирования статей?
sqlite3 rss_media_bus.db "
SELECT title, COUNT(*) as count 
FROM articles 
WHERE added_date > datetime('now', '-1 hour') 
GROUP BY title 
HAVING COUNT(*) > 1;
"
# Ожидается: пустой результат

# 4. Отправляет ли User Service новости?
tail -f user_service.log | grep "Отправлено статей"
```

### Диагностические команды

```bash
# Проверить конфигурацию пользователя
python3 -c "
from user_notification_service import UserNotificationService
import asyncio

async def check_config():
    service = UserNotificationService()
    await service.initialize_database()
    await service.load_users()
    
    print(f'👥 Активных пользователей: {len(service.users)}')
    for user_id, last_check in service.last_check_time.items():
        print(f'🕐 {user_id}: last_check = {last_check}')

asyncio.run(check_config())
"

# Проверить RSS источники вручную
curl -s "https://ria.ru/export/rss2/archive/index.xml" | head -20
curl -s "https://tass.ru/rss/v2.xml" | head -20
```

## 🛠️ Troubleshooting

### Система не запускается

```bash
# Проверить зависимости
pip install -r requirements.txt

# Проверить конфигурацию
ls -la config/users.yaml config/sources.yaml config/topics_mapping.json

# Принудительно очистить процессы и перезапустить
pkill -9 -f "rss_bus_core.py"
pkill -9 -f "user_notification_service.py"
./start_system.sh
```

### RSS Core не парсит статьи

```bash
# Проверить доступность RSS источников
timeout 10s curl -s "https://ria.ru/export/rss2/archive/index.xml" | head -5

# Проверить логи RSS Core
tail -f rss_core.log

# Перезапустить систему
./start_system.sh
```

### User Service не отправляет уведомления

```bash
# Проверить Telegram бота
curl -s "https://api.telegram.org/bot<TOKEN>/getMe"

# Проверить доступ к чату
curl -s "https://api.telegram.org/bot<TOKEN>/getChat?chat_id=<CHAT_ID>"

# Проверить last_check время
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

### Дублирование новостей

```bash
# Проверить количество процессов
ps aux | grep python3 | grep -E "(rss_bus_core|user_notification)" | wc -l
# Должно быть: 2

# Если больше - перезапустить
./start_system.sh

# Проверить отсутствие дубликатов в БД
sqlite3 rss_media_bus.db "
SELECT title, COUNT(*) 
FROM articles 
WHERE added_date > datetime('now', '-1 hour') 
GROUP BY title 
HAVING COUNT(*) > 1;
"
```

## 🎯 Проверка успешного запуска

После запуска `./start_system.sh` через 2-3 минуты вы должны увидеть:

### 1. Процессы запущены
```bash
$ ps aux | grep python3 | grep -E "(rss_bus_core|user_notification)"
root  12345  python3 rss_bus_core.py
root  12346  python3 user_notification_service.py
```

### 2. RSS парсинг работает
```bash
$ tail -5 rss_core.log
✅ https://ria.ru/export/rss2/archive/index.xml: 3 новых статей
✅ https://tass.ru/rss/v2.xml: 2 новых статей
📊 Обработано: 46 успешно, 0 с ошибками
📰 Всего новых статей: 15
```

### 3. User Service отправляет уведомления
```bash
$ tail -5 user_service.log
📤 all_sources_rss_user: В Домодедово сняли временные ограничения → ria.ru (топик 2)
📱 Отправка в топик 2
📤 all_sources_rss_user: Глазьев: Европа дорого заплатила... → tass.ru (топик 1)
📊 Цикл уведомлений завершен за 5.2с:
  📤 Отправлено статей: 7
```

### 4. Новые статьи в базе данных
```bash
$ sqlite3 rss_media_bus.db "SELECT datetime(added_date, 'localtime'), feed_id, title FROM articles ORDER BY added_date DESC LIMIT 3;"
2025-07-20 22:46:32|rbc.ru|МВД начало проверку после смертельного ДТП
2025-07-20 22:46:31|ria.ru|Симоньян рассказала, как армяне могут сохранить
2025-07-20 22:46:30|tass.ru|"Рубин" обыграл "Ахмат" в матче чемпионата
```

## 📱 Telegram Integration

### Настройка супергруппы

1. **Создать супергруппу** с топиками
2. **Добавить бота** как администратора
3. **Включить топики** в настройках группы
4. **Создать 49 топиков** для разных источников новостей
5. **Получить chat_id** группы (отрицательное число)

### Формат отправляемых сообщений

```
📰 В Домодедово сняли временные ограничения

В аэропорту Домодедово сняли временные ограничения на прилеты и вылеты самолетов, введенные из-за тумана.

🔗 Подробнее: https://ria.ru/20250720/domodedovo-123456.html
🏷️ #ria_ru #авиация #москва
```

## 🔄 Остановка системы

```bash
# Остановить все процессы RSS Media Bus
pkill -f 'rss_bus_core.py|user_notification_service.py'

# Проверить что остановлены
ps aux | grep python3 | grep -E "(rss_bus_core|user_notification)"
# Должен быть пустой результат
```

## 📚 Дополнительная документация

- **[README.md](README.md)** - Полная документация системы
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Детальная архитектура
- **[docs/SCALABILITY.md](docs/SCALABILITY.md)** - Масштабирование системы
- **[docs/PROCESSES.md](docs/PROCESSES.md)** - Управление процессами

---

🎯 **RSS Media Bus v3.1 готов к работе!** Все критические проблемы исправлены, система стабильна и не дублирует новости. 
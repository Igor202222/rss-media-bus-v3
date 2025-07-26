# 🛡️ Система обработки ошибок RSS v2.0

## 📋 Обзор

Новая централизованная система обработки ошибок RSS источников с специальной логикой для разных типов проблем и детальным логированием.

## 🔧 Компоненты системы

### 1. **ErrorManager** (`core/error_manager.py`)
Центральный компонент для управления ошибками:
- ✅ Счетчики ошибок по источникам
- ✅ Детальное логирование в `rss_errors.log`
- ✅ Специальная логика для 403 ошибок
- ✅ Экспоненциальные задержки для проблемных источников
- ✅ Рекомендации по исправлению

### 2. **RSS Error Viewer** (`rss_error_viewer.py`)
Утилита для просмотра и анализа ошибок:
```bash
python3 rss_error_viewer.py           # Полный отчет
python3 rss_error_viewer.py log 50    # Последние 50 записей
python3 rss_error_viewer.py export    # Экспорт в JSON
python3 rss_error_viewer.py help      # Справка
```

### 3. **Health Check** (`check_rss_health.sh`)
Быстрая диагностика системы:
```bash
./check_rss_health.sh                 # Проверка здоровья системы
```

## 🚨 Типы ошибок и реакция системы

### **HTTP 403 Forbidden** - Умная обработка
```
Ошибка 1-2: Рекомендация "user_agent" → попробовать другой User-Agent
Ошибка 3-4: Рекомендация "proxy" → использовать прокси
Ошибка 5+:  Рекомендация "both" → прокси + User-Agent
```

### **HTTP 404 Not Found** - Немедленная остановка
- Источник записывается в ошибки
- Парсинг прекращается (return 0)
- Требует ручного исправления URL

### **Таймауты и сетевые ошибки** - Ретраи
- 3 попытки с задержками: 2s → 4s → 8s
- При исчерпании попыток - запись в ошибки
- Экспоненциальные задержки между циклами

### **Ошибки парсинга** - Логирование
- Детальная информация об ошибке
- Рекомендации по исправлению

## 📊 Логика пропуска источников

```python
if error_count >= 5:
    delay_minutes = min(60, 2 ** error_count)
    # 2^5=32мин, 2^6=60мин (макс), 2^7=60мин...
```

**Восстановление:** При успешном запросе все счетчики сбрасываются

## 📁 Файлы логов

### **rss_errors.log** - Детальные ошибки
```
2025-07-26 21:16:53 | ERROR | Test Feed | forbidden | HTTP 403 | Test 403 error | Ошибок: 1
```

### **rss_core.log** - Общий лог парсера
```
📡 Начинаю парсинг 46 источников...
✅ SciTechDaily Earth: 2 новых
```

### **user_service.log** - Лог уведомлений
```
Отправлено статей: 15 для eco_scan_bot
```

## 🎯 Практические команды

### Мониторинг в реальном времени
```bash
tail -f rss_errors.log                # Ошибки RSS
tail -f rss_core.log                  # Парсинг
tail -f user_service.log              # Отправка
```

### Диагностика проблем
```bash
./check_rss_health.sh                 # Общее состояние
python3 rss_error_viewer.py           # Детальный анализ
grep "403\|timeout" rss_errors.log    # Поиск проблем
```

### Статистика из БД
```bash
sqlite3 rss_media_bus.db "
SELECT feed_id, COUNT(*) 
FROM articles 
WHERE added_date > datetime('now', '-1 hour') 
GROUP BY feed_id ORDER BY COUNT(*) DESC;"
```

## 🔧 Исправление частых проблем

### **403 ошибки**
1. **В sources.yaml добавить прокси:**
```yaml
source_name.com:
  url: "https://example.com/rss"
  active: true
  proxy_required: true
  proxy_settings:
    type: "http"
    url: "http://user:pass@proxy:port"
    region: "usa"
```

2. **Проверить User-Agent в AsyncRSSParser**
3. **Временно отключить: `active: false`**

### **Таймауты**
1. **Увеличить timeout в `config.py`:**
```python
HTTP_TIMEOUT = 60  # вместо 30
```

2. **Добавить прокси для стабильности**

### **404 ошибки**
1. **Найти новый URL RSS на сайте**
2. **Обновить URL в sources.yaml**
3. **Или отключить: `active: false`**

## 📈 Мониторинг и алерты

### Создание простого алерта
```bash
# Добавить в crontab для проверки каждые 5 минут
*/5 * * * * cd /opt/rss_media_bus && python3 -c "
from core.error_manager import ErrorManager
from core.database import DatabaseManager
import sys

db = DatabaseManager()
error_mgr = ErrorManager(db)
stats = error_mgr.get_error_statistics()

if stats['total_errors'] > 10:
    print(f'ALERT: {stats[\"total_errors\"]} ошибок RSS!')
    sys.exit(1)
"
```

### Webhook уведомления
```python
# Добавить в ErrorManager для отправки в Slack/Discord
def send_critical_alert(self, error_count):
    if error_count > 5:
        # Отправить webhook
        pass
```

## 🎛️ Конфигурация

### Настройки в ErrorManager
```python
max_errors = 5           # Порог для пропуска источника
max_delay_minutes = 60   # Максимальная задержка
log_retention = 10       # Хранить последние N ошибок
```

### Интеграция с Telegram
```python
# В user_notification_service.py можно добавить
if error_count > threshold:
    await send_admin_notification(f"Источник {feed_name} недоступен")
```

## 📚 API ErrorManager

### Основные методы
```python
error_manager.record_error(url, name, type, status, message)
error_manager.reset_errors(url)
should_skip, reason = error_manager.should_skip_feed(url)
recommendation = error_manager.should_try_alternative_method(url, 403)
stats = error_manager.get_error_statistics()
```

---

**📞 Поддержка:** При проблемах с системой ошибок запустите `./check_rss_health.sh` для диагностики. 
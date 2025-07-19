# 🏗️ Архитектура RSS Media Bus v3.0

## 📊 **Принципы архитектуры**

### **🎯 Основная концепция:**
```
RSS Sources → RSS Media Bus → Processors → Users
```

**Эволюция от v2.0:**
- ❌ **Было:** N экземпляров = N копий кода = неэффективность
- ✅ **Стало:** 1 шина сообщений = централизованная обработка = масштабируемость

## 🔄 **Схема потоков данных**

### **📡 RSS мониторинг:**
```
config/sources.yaml → rss_monitoring.py → source_manager.py → MockDBManager
                                     ↓
                          debug_chat_logger.py → Telegram топик
```

### **👥 Управление пользователями:**
```
Telegram Bot (@rss_media_bus_user_bot) 
    ↓ /start
user_bot/telegram_user_bot.py 
    ↓ автоматическая регистрация
config/users.yaml (единое хранение)
```

### **📊 Логирование:**
```
RSS процессы → debug_chat_logger.py → Telegram чат (-1002756550488)
                                         ↓
                                   Топик "📡 RSS МОНИТОРИНГ" (ID: 3)
```

## 📁 **Структура проекта и статусы**

```
/opt/rss_media_bus/
├── 🔧 main.py                    # ✅ MVP тестирование
├── 📊 rss_monitoring.py          # ✅ РАБОТАЕТ: Фоновый RSS мониторинг
├── 📄 requirements.txt           # ✅ ГОТОВО: feedparser, requests, telegram
│
├── 📁 config/                    # ✅ ГОТОВО
│   ├── sources.yaml             # ✅ 6 RSS источников, 5 мин интервал
│   └── users.yaml              # ✅ Единое хранение пользователей
│
├── 📁 core/                     # ✅ ГОТОВО (из v2.0)
│   ├── source_manager.py        # ✅ AsyncRSSParser
│   ├── database.py             # ✅ DatabaseManager (SQLite)
│   ├── config_hot_reload.py    # ✅ Горячая перезагрузка
│   ├── long_term_monitor.py    # ✅ Долгосрочная аналитика
│   └── processors/             # 🚧 ПУСТАЯ: keyword_filter.py TODO
│
├── 📁 outputs/                  # ✅ ГОТОВО
│   ├── telegram_sender.py       # ✅ Telegram интеграция (9.2KB)
│   ├── telegram_health_reporter.py # ✅ Отчеты состояния (14KB)
│   └── debug_chat_logger.py    # ✅ РАБОТАЕТ: Логи в топики
│
├── 📁 user_bot/                 # ✅ ГОТОВО
│   └── telegram_user_bot.py    # ✅ РАБОТАЕТ: Авто-регистрация
│
├── 📁 subscribers/              # 🚧 ПУСТАЯ: user_manager.py TODO
├── 📁 legacy_bridge/            # 🚧 ПУСТАЯ: миграция с v2.0 TODO
├── 📁 web_dashboard/           # 🚧 ПУСТАЯ: веб-интерфейс TODO
└── 📁 docs/                    # ✅ ГОТОВО: актуализированная документация
```

## 💾 **Схема хранения данных**

### **👥 Пользователи (единое хранение)**

**Файл:** `config/users.yaml`
```yaml
users:
  test_user:                    # Тестовый пользователь
    name: "Test Monitor"
    sources: [tass_main, ria_main, rbc_main]
    telegram: { enabled: false }
    
  yrcnw_user:                   # ✅ Автоматически через бота
    name: "И Monitor"
    telegram_id: 2337404
    username: "yrcnw"
    sources: [tass_main, ria_main]
    registration_method: "telegram_bot"
    created_at: "2025-07-19T15:12:54"
    telegram: 
      chat_id: "2337404"
      enabled: false            # Нет bot_token пока
```

### **📡 RSS Источники (централизованная конфигурация)**

**Файл:** `config/sources.yaml`
```yaml
sources:
  tass_main:                   # ✅ АКТИВЕН
    url: "https://tass.ru/rss/v2.xml"
    name: "ТАСС - Главные новости"
    update_interval: 300       # 5 минут (унифицировано)
    active: true
    
  ria_main:                    # ✅ АКТИВЕН
    url: "https://ria.ru/export/rss2/archive/index.xml"
    update_interval: 300
    
  # ... еще 4 источника (всего 6 активных)

source_groups:                 # Группировка источников
  russian_news: [tass_main, ria_main, rbc_main]
  international_sustainability: [reuters, bbc, techcrunch]
```

### **🗄️ База данных (текущий статус)**

**Текущая:** MockDBManager (в памяти)
```python
class MockDBManager:
    def __init__(self):
        self.articles = []        # Список статей
        self.feeds_info = {}      # Информация об источниках
    
    def article_exists(link) → bool     # ✅ РАБОТАЕТ
    def add_article(...) → int          # ✅ РАБОТАЕТ
    def update_feed_info(...) → None    # ✅ РАБОТАЕТ
```

**Планируется:** DatabaseManager (SQLite)
```sql
-- core/database.py - готов к использованию
articles(id, feed_id, title, link, description, content, author, published_date)
feeds(id, title, url, last_check, status)
```

## 🔄 **Процессы и их состояния**

### **✅ Работающие процессы:**

#### **📊 RSS мониторинг:**
- **Файл:** `rss_monitoring.py`
- **Режим:** Фоновый (nohup)
- **PID:** Переменный (проверять через `ps aux | grep rss_monitoring`)
- **Интервал:** 5 минут
- **Логи:** `rss_monitor.log`
- **Статус:** ✅ Работает, парсит новости, отправляет отчеты в Telegram

#### **🤖 Пользовательский бот:**
- **Файл:** `user_bot/telegram_user_bot.py`
- **Токен:** `7441299677:AAFJn2pDdvQ4BsMVeTBvDzsT8kLpBNDGlwk`
- **Бот:** [@rss_media_bus_user_bot](https://t.me/rss_media_bus_user_bot)
- **Функции:** `/start` (регистрация), `/status`, `/sources`, `/help`
- **Статус:** ✅ Работает, регистрирует пользователей в `users.yaml`

#### **📊 Debug логирование:**
- **Файл:** `outputs/debug_chat_logger.py`
- **Токен:** `8171335651:AAFv3gO3dCZTLxu62JLtWsK6Gza7bdAoYVc`
- **Чат:** `-1002756550488`
- **Топики:** 
  - ID: 3 "📡 RSS МОНИТОРИНГ" ✅ Работает
  - Другие топики по мере необходимости
- **Статус:** ✅ Отправляет сводные отчеты каждые 5 минут

## 🔧 **Текущие ограничения и проблемы**

### **⚠️ Технические ограничения:**
1. **MockDBManager** - данные не сохраняются между перезапусками
2. **Hot reload отсутствует** - изменения кода требуют ручного перезапуска
3. **Нет обработки ошибок** при недоступности Telegram API
4. **Отсутствует keyword_filter.py** - нет фильтрации по ключевым словам

### **📝 Архитектурные решения:**
1. **Отдельные процессы** - RSS мониторинг независим от пользовательского бота
2. **Централизованные конфиги** - все настройки в `config/`
3. **Модульная структура** - каждый компонент можно развивать независимо
4. **Telegram-centric** - все уведомления и интерфейсы через Telegram

## 🎯 **Паттерны проектирования**

### **🔄 Publisher-Subscriber:**
```
RSS Sources (Publishers) → RSS Media Bus → Users (Subscribers)
```

### **🏭 Factory Pattern:**
```python
# Создание процессоров на основе конфигурации
processors = ProcessorFactory.create_from_config(user_config)
```

### **🔌 Plugin Architecture:**
```
core/processors/
├── keyword_filter.py    # Фильтрация
├── translator.py        # Перевод
├── sentiment_analyzer.py # Анализ тональности
└── custom_processor.py  # Пользовательские
```

## 📈 **Масштабируемость**

### **📊 Текущие ограничения:**
- **Пользователи:** ~100 (ограничено MockDBManager)
- **RSS источники:** ~20 (ограничено таймаутами)
- **Частота обновления:** 5 минут (настраивается)

### **🚀 Планы расширения:**
- **База данных:** SQLite → PostgreSQL для >1000 пользователей
- **Кэширование:** Redis для часто запрашиваемых данных
- **Очереди:** Celery для асинхронной обработки
- **Мониторинг:** Prometheus + Grafana для метрик

---

**🏗️ Архитектура готова к продакшену на 75% - требуется доработка процессоров**  
*Последнее обновление: Июль 2025* 
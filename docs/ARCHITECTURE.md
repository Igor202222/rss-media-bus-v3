# 🏗️ Архитектура RSS Media Bus v3.0

## 📊 **Принципы архитектуры v3.0**

### **🎯 Эволюция архитектуры:**
```
v1.0: RSS Parser → Direct Notifications (один пользователь)
v2.0: Multiple Parsers → Database → Users (дублирование)
v3.0: RSS Bus Core → Database ← User Notification Service (централизация)
```

**Ключевые изменения v3.0:**
- ✅ **Централизованная RSS шина:** Один процесс парсинга для всех пользователей
- ✅ **Независимые сервисы:** RSS Core + User Service работают автономно
- ✅ **Автоматическое масштабирование:** Новые пользователи без дублирования ресурсов
- ✅ **Отказоустойчивость:** Автоматический перезапуск компонентов

## 🔄 **Схема потоков данных v3.0**

### **📡 RSS Bus Core Flow:**
```
📋 config/sources.yaml (49 источников)
        ↓
🚌 RSS Bus Core (rss_bus_core.py)
        ↓ [каждые 5 минут]
🌐 HTTP requests → RSS Feeds
        ↓ [async парсинг]
📊 Rich Article Data (GUID, теги, медиа)
        ↓
🗄️ SQLite Database (articles table)
```

**Компоненты RSS Bus Core:**
- `core/async_rss_parser.py` - Асинхронный парсер RSS
- `core/source_manager.py` - Управление источниками  
- `core/database.py` - Интерфейс к SQLite БД
- `config/sources.yaml` - Конфигурация 49 источников

### **🔔 User Notification Service Flow:**
```
🗄️ SQLite Database
        ↓ [каждые 2 минуты]
🔔 User Notification Service (user_notification_service.py)
        ↓ [загрузка пользователей]
📋 config/users.yaml
        ↓ [фильтрация по пользователю]
🎯 User-specific Articles
        ↓ [процессоры]
processors/ (keyword_filter, telegram_formatter)
        ↓ [отправка]
📱 outputs/telegram_sender.py → Telegram Topics
```

**Компоненты User Notification Service:**
- `processors/keyword_filter.py` - Фильтрация по ключевым словам
- `processors/telegram_formatter.py` - Форматирование для Telegram
- `outputs/telegram_sender.py` - Отправка в Telegram API
- `config/users.yaml` - Конфигурации пользователей
- `config/topics_mapping.json` - Mapping источников → топики

### **🎛️ RSS Bus Manager Flow:**
```
🎛️ start_rss_bus.py (Manager Process)
        ↓ [fork processes]
🚌 RSS Bus Core Process (PID 1)
🔔 User Notification Service Process (PID 2)
        ↓ [monitoring]
📊 Health Checks
        ↓ [auto-restart on failure]
🔄 Process Recovery
```

## 🏛️ **Архитектурные компоненты**

### **1. 🚌 RSS Bus Core (Независимый сервис)**

**Назначение:** Централизованный парсинг всех RSS источников

**Характеристики:**
- **Интервал:** 5 минут (configurable)
- **Источников:** 49 (российские + green/climate)
- **Режим:** 24/7, независимо от пользователей
- **Технологии:** Python asyncio, feedparser, aiohttp

**Алгоритм работы:**
```python
while True:
    sources = load_sources()  # config/sources.yaml
    
    for source in sources:
        articles = await parse_rss_async(source.url)
        
        for article in articles:
            enriched_article = extract_metadata(article)
            save_to_database(enriched_article)
    
    await asyncio.sleep(300)  # 5 минут
```

**Обогащение данных:**
- GUID статьи (уникальный идентификатор)
- Полный текст и контент
- Теги и категории  
- Медиа вложения (изображения, видео)
- Дата модификации и источник

### **2. 🔔 User Notification Service (Пользовательский сервис)**

**Назначение:** Фильтрация и доставка новостей пользователям

**Характеристики:**
- **Интервал:** 2 минуты (configurable)
- **Пользователей:** N (масштабируется)
- **Режим:** Независимые фильтры для каждого пользователя
- **Технологии:** Python asyncio, Telegram Bot API

**Алгоритм работы:**
```python
while True:
    users = load_users()  # config/users.yaml
    
    for user in users:
        if not user.telegram.enabled:
            continue
            
        new_articles = get_new_articles_for_user(user)
        
        for article in new_articles:
            if should_send_article_to_user(article, user):
                await send_article_to_user(article, user)
                
        update_last_check_time(user)
    
    await asyncio.sleep(120)  # 2 минуты
```

**Фильтрация пользователей:**
- Источники: каждый пользователь выбирает нужные RSS
- Процессоры: keyword_filter, content_filter, etc.
- Форматирование: markdown, HTML, текст
- Доставка: Telegram топики, каналы, личные сообщения

### **3. 🎛️ RSS Bus Manager (Управляющий процесс)**

**Назначение:** Оркестрация и мониторинг всех сервисов

**Характеристики:**
- **Процессы:** RSS Core + User Service
- **Мониторинг:** Health checks каждые 30 секунд
- **Восстановление:** Автоматический перезапуск при сбоях
- **Управление:** Graceful shutdown, логирование

**Алгоритм управления:**
```python
def start_rss_bus():
    # Запуск процессов
    rss_core_process = subprocess.Popen([
        'python3', 'rss_bus_core.py'
    ])
    
    user_service_process = subprocess.Popen([
        'python3', 'user_notification_service.py'
    ])
    
    # Мониторинг
    while True:
        if not rss_core_process.is_alive():
            restart_rss_core()
            
        if not user_service_process.is_alive():
            restart_user_service()
            
        time.sleep(30)
```

## 🗄️ **Схема базы данных**

### **Таблица `articles` (Центральное хранилище)**

```sql
CREATE TABLE articles (
    -- Основные поля
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feed_id TEXT NOT NULL,              -- Источник (tass.ru, ria.ru)
    title TEXT NOT NULL,
    link TEXT UNIQUE NOT NULL,
    description TEXT,
    content TEXT,
    author TEXT,
    published_date TIMESTAMP,
    
    -- RSS v3.0 расширения
    guid TEXT,                          -- Уникальный GUID от источника
    full_text TEXT,                     -- Полный текст статьи
    category TEXT,                      -- Категория (политика, спорт)
    tags TEXT,                          -- JSON: ["тег1", "тег2"]
    media_attachments TEXT,             -- JSON: [{"type": "image", "url": "..."}]
    modification_date TIMESTAMP,        -- Последнее изменение
    news_id TEXT,                       -- ID статьи в источнике
    content_type TEXT,                  -- article, video, photo
    newsline TEXT,                      -- Лента (главные, спорт, экономика)
    
    -- Системные поля
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Индексы для производительности
    INDEX idx_feed_published (feed_id, published_date),
    INDEX idx_created_at (created_at),
    INDEX idx_guid (guid)
);
```

### **Конфигурационные файлы**

**config/sources.yaml** - RSS источники (49 штук)
```yaml
sources:
  tass.ru:
    name: "ТАСС - Главные новости"
    url: "https://tass.ru/rss/v2.xml"
    active: true
    group: "russian_news"
    parse_full_content: true
    
  ria.ru:
    name: "РИА Новости"
    url: "https://ria.ru/export/rss2/archive/index.xml"
    active: true
    group: "russian_news"
    
  # ... 47 других источников
```

**config/users.yaml** - Пользователи системы
```yaml
all_sources_rss_user:
  name: "All Sources RSS Monitor"
  active: true
  created_at: "2025-07-20T18:10:00.000000"
  
  telegram:
    chat_id: "-1002883915655"
    bot_token: "7000553711:AAGa4WKSGJGheJcydtR9V0L9vnxlK89Twgo"
    enabled: true
    
  sources: [tass.ru, ria.ru, rbc.ru, ...]  # 46 источников
  
  processors:
    - name: "telegram_sender"
      config:
        format: "markdown"
        send_all: true
```

**config/topics_mapping.json** - Mapping источников к топикам
```json
{
  "tass.ru": {
    "topic_id": 3,
    "topic_name": "🇷🇺 ТАСС - Главные новости"
  },
  "ria.ru": {
    "topic_id": 4, 
    "topic_name": "🇷🇺 РИА Новости"
  }
}
```

## 🔄 **Паттерны взаимодействия**

### **1. RSS → Database (Push модель)**

RSS Bus Core **активно** парсит источники и **проталкивает** данные в БД:

```
RSS Sources → RSS Bus Core → Database
```

**Преимущества:**
- Непрерывный мониторинг источников
- Актуальные данные в БД
- Независимость от пользователей

### **2. Database → Users (Pull модель)**

User Notification Service **пассивно** читает из БД для каждого пользователя:

```
Database ← User Notification Service ← User Configs
```

**Преимущества:**
- Масштабируемость (N пользователей)
- Индивидуальные фильтры
- Независимые интервалы опроса

### **3. Manager → Processes (Orchestration)**

RSS Bus Manager **оркестрирует** жизненный цикл всех процессов:

```
Manager → RSS Core Process
        → User Service Process
        → Health Monitoring
        → Auto Restart
```

## ⚡ **Производительность и масштабирование**

### **📊 Характеристики производительности:**

**RSS Bus Core:**
- 49 источников за ~30 секунд (async парсинг)
- ~200-500 новых статей в час (в зависимости от активности)
- Потребление памяти: ~50-100 MB
- CPU загрузка: 5-15% во время парсинга

**User Notification Service:**
- 1 пользователь: ~2-5 секунд обработки
- N пользователей: линейное масштабирование
- Telegram Rate Limits: 30 сообщений/секунду
- Потребление памяти: ~20-50 MB на пользователя

### **🚀 Горизонтальное масштабирование:**

**Добавление пользователей:**
1. Один RSS Bus Core обслуживает неограниченное количество пользователей
2. User Notification Service автоматически подхватывает новых пользователей
3. Никакого дублирования RSS парсинга
4. Время добавления: ~2 минуты

**Добавление источников:**
1. Обновление config/sources.yaml
2. RSS Bus Core подхватывает при следующем цикле
3. Автоматическое создание топиков в Telegram
4. Обновление mapping файлов

### **🛡️ Отказоустойчивость:**

**Уровень 1 - Process Level:**
- RSS Bus Manager перезапускает упавшие процессы
- Health checks каждые 30 секунд
- Graceful shutdown при Ctrl+C

**Уровень 2 - Component Level:**
- RSS Bus Core: retry логика для HTTP запросов
- User Service: обработка Telegram API ошибок
- Database: SQLite ACID транзакции

**Уровень 3 - System Level:**
- Логирование всех операций
- Метрики производительности
- Мониторинг состояния БД

## 🔮 **Планы развития архитектуры**

### **v3.1 - Microservices готовность:**
- REST API для управления
- Контейнеризация (Docker)
- Service discovery
- Метрики и мониторинг (Prometheus)

### **v3.2 - Распределенная архитектура:**
- Message Queues (Redis/RabbitMQ)
- Horizontal scaling User Services
- Load balancing
- Multi-database support

### **v3.3 - ML и аналитика:**
- Content classification
- User behavior analytics  
- Smart filtering
- Recommendation engine

---

**RSS Media Bus v3.0 Architecture** - готова к production deployment! 🚀 
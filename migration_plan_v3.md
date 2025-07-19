# Миграция к RSS Media Bus v3.0 🚀

## 🎯 Концепция новой архитектуры

### **RSS Media Bus** - Центральная шина сообщений
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   RSS Sources   │───▶│  RSS Media Bus   │───▶│   Subscribers   │
│                 │    │                  │    │                 │
│ • TASS          │    │ • Source Manager │    │ • User_1 (vape) │
│ • RIA           │    │ • Article Queue  │    │ • User_2 (ESG)  │
│ • Lenta         │    │ • Processors     │    │ • User_N (...)  │
│ • BBC           │    │ • Auth Service   │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🏗️ Новая структура проекта

```
/opt/rss_media_bus/
├── core/                          # Ядро системы
│   ├── source_manager.py         # Управление RSS источниками
│   ├── article_queue.py          # Очередь обработки статей
│   ├── processors/               # Обработчики контента
│   │   ├── keyword_filter.py    # Фильтр по ключевым словам
│   │   ├── translator.py        # Переводчик
│   │   ├── sentiment_analyzer.py # Анализ тональности
│   │   └── summarizer.py        # Автосуммаризация
│   └── database.py              # Централизованная БД
├── subscribers/                  # Система подписчиков
│   ├── user_manager.py          # Управление пользователями
│   ├── subscription_engine.py   # Движок подписок
│   └── auth_service.py          # Аутентификация
├── outputs/                     # Система вывода
│   ├── telegram_sender.py       # Telegram интеграция
│   ├── email_sender.py          # Email рассылка
│   ├── webhook_sender.py        # Webhook уведомления
│   └── api_server.py           # REST API
├── config/                      # Конфигурации
│   ├── sources.yaml            # RSS источники
│   ├── users.yaml              # Пользователи и подписки
│   └── processors.yaml         # Настройки обработчиков
├── web_dashboard/              # Веб-интерфейс управления
│   ├── app.py                 # Flask/FastAPI приложение
│   ├── templates/             # HTML шаблоны
│   └── static/               # CSS/JS ресурсы
└── legacy_bridge/             # Мост с текущей системой
    ├── vapes_bridge.py       # Мост для vapes
    └── esg_bridge.py        # Мост для esg-all-news
```

## 📋 Этапы миграции

### **Этап 1: Подготовка (1-2 дня)**
```bash
# Создаем новую папку рядом с текущей
mkdir /opt/rss_media_bus
cd /opt/rss_media_bus

# Копируем лучшие компоненты из текущего проекта
cp /opt/media_monitoring/src/rss_parser.py core/source_manager.py
cp /opt/media_monitoring/src/database.py core/database.py
cp /opt/media_monitoring/src/telegram_sender.py outputs/telegram_sender.py
```

### **Этап 2: Минимальный MVP (3-5 дней)**
- ✅ Централизованный RSS парсер
- ✅ Базовая система подписчиков
- ✅ Telegram вывод
- ✅ Миграция одного пользователя (например, vapes)

### **Этап 3: Параллельная работа (1 неделя)**
- ✅ Два экземпляра работают параллельно
- ✅ Мост между старой и новой системой
- ✅ Постепенный перенос пользователей

### **Этап 4: Полная миграция (2-3 недели)**
- ✅ Веб-интерфейс для управления
- ✅ API для интеграций
- ✅ Отключение старой системы

## 💡 Ключевые преимущества v3.0

### **🚀 Масштабируемость:**
```yaml
# Новый пользователь добавляется за 30 секунд
users:
  john_doe:
    telegram_chat: "-123456789"
    filters: ["crypto", "blockchain"]
    processors: ["translate_to_en", "summarize"]
    sources: ["coindesk", "cryptonews"]
```

### **🔧 Гибкость обработки:**
```python
# Пример цепочки обработки
article → keyword_filter → translator → sentiment_analyzer → telegram
```

### **📊 Централизованная аналитика:**
- Общая статистика по всем источникам
- Анализ популярности тем
- Мониторинг качества источников

## 🛡️ Безопасность миграции

### **Сохранение данных:**
```bash
# Бэкап текущих БД
cp instances/vapes/vapes_monitor.db backups/
cp instances/esg-all-news/esg-all-news_monitor.db backups/
```

### **Параллельная работа:**
- Старая система продолжает работать
- Новая система тестируется на копии данных
- Постепенное переключение пользователей

### **Rollback план:**
- Возможность быстрого возврата к старой системе
- Синхронизация данных между системами

## 🎯 Первые шаги

1. **Создать новую папку проекта**
2. **Извлечь переиспользуемые компоненты**
3. **Создать MVP с одним пользователем**
4. **Протестировать параллельную работу**

## 📝 Конфигурация пользователя в новой системе

```yaml
# /opt/rss_media_bus/config/users.yaml
users:
  vapes_user:
    name: "Vapes Monitor"
    telegram:
      chat_id: "-4838608452"
      bot_token: "7741366879:AAF..."
    sources:
      - "tass_health"
      - "ria_health"
      - "interfax_health"
    processors:
      - name: "keyword_filter"
        config:
          keywords: ["вейп", "электронные сигареты"]
          mode: "include"
      - name: "telegram_sender"
        config:
          format: "markdown"
    
  esg_user:
    name: "ESG News Monitor"
    telegram:
      chat_id: "-1002349478884"
      topic_id: 2
    sources:
      - "reuters_sustainability"
      - "bloomberg_green"
      - "euronews_green"
    processors:
      - name: "keyword_filter"
        config:
          keywords: ["ESG", "sustainability", "green energy"]
      - name: "translator"
        config:
          target_language: "ru"
      - name: "telegram_sender"
```

---

*План создан AI Assistant для безопасной эволюции системы RSS мониторинга* 
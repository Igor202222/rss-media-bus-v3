# 📱 Управление Telegram топиками RSS Media Bus

## 🎯 **Обзор**

RSS Media Bus поддерживает автоматическое создание и управление топиками в Telegram супергруппах для организации RSS лент по тематикам.

## 🔧 **Автоматическое создание топиков**

### **Скрипт `create_topics.py`**

```bash
# Создание топиков автоматически
python3 create_topics.py
```

**Что делает скрипт:**
1. ✅ Создает топики в Telegram чате через Bot API
2. ✅ Отправляет описание RSS источника в каждый топик  
3. ✅ Закрепляет информационное сообщение
4. ✅ Сохраняет результаты в `created_topics_result.json`

### **Требования для бота:**

**Права администратора:**
- `manage_topics` - создание/редактирование топиков
- `pin_messages` - закрепление сообщений
- `can_post_messages` - отправка сообщений

**Формат чата:**
- Супергруппа с включенными топиками
- Chat ID в формате: `-100{original_id}`

## 📋 **Процесс добавления новых источников**

### **1. Добавить RSS источник**

```yaml
# config/sources.yaml
new_source.com:
  url: "https://new-source.com/rss"
  name: "New Source Name"
  active: true
```

### **2. Создать топик**

Отредактируйте `create_topics.py`:

```python
topics = [
    {
        "name": "📰 New Source",           # Название топика
        "icon_color": 0x17A2B8,           # Цвет иконки
        "pin_message": """📡 RSS: New Source
🔗 Источник: https://new-source.com/rss
📝 Описание источника"""
    }
]
```

### **3. Запустить создание**

```bash
python3 create_topics.py
```

### **4. Добавить mapping**

```yaml
# config/users.yaml
ip_scan_bot:
  topics_mapping:
    new_source.com: <topic_id_из_результата>
```

## 🎨 **Настройка топиков**

### **Цвета иконок (icon_color):**

```python
0x6FB9F0  # 🔵 Голубой      - Общие новости
0x00C851  # 🟢 Зеленый     - Экология, ESG  
0x007BFF  # 🔷 Синий       - Технологии
0x000000  # ⚫ Черный      - Пиратство
0x6C757D  # 🔘 Серый       - Правовые
0xDC3545  # 🔴 Красный     - Патенты, USPTO
0xFF6B6B  # 🌸 Розовый     - Россия
0xFFC107  # 🟡 Желтый      - Авторские права
0x28A745  # 🟤 Темно-зеленый - Официальные
0x17A2B8  # 🔶 Бирюзовый  - AI, ChatGPT
0x6F42C1  # 🟣 Фиолетовый - Специальные
```

### **Шаблон описания:**

```
📡 RSS: <Название источника>
🔗 Источник: <URL RSS ленты>
📝 <Краткое описание тематики>
```

## 📊 **Текущие топики RSS Media Bus**

### **IP/Copyright топики (ip_scan_bot):**

| Топик | ID | Источник | Тематика |
|-------|----|-----------| ---------|
| 🏛️ World Trademark Review | 2 | worldtrademarkreview.com | Товарные знаки |
| 🤖 ChatGPT World | 4 | chatgptiseatingtheworld.com | AI новости |
| 🌍 WIPO News | 6 | wipo.int | ВОИС |
| 🏴‍☠️ TorrentFreak | 8 | torrentfreak.com | Пиратство |
| ⚖️ Bloomberg IP Law | 10 | bloomberglaw.com | IP право |
| 🇺🇸 USPTO | 12 | uspto.gov | USPTO |
| 🇷🇺 РАПСИ Новости | 14 | rapsinews.ru | Правовые РФ |
| 📄 Copyright Lately | 16 | copyrightlately.com | Авторские права |
| 🏛️ US Copyright Office | 18 | *.copyright.gov | Объединенный топик |

### **Объединенные источники:**

**🏛️ US Copyright Office (ID: 18):**
- `copyright_case_act.gov`
- `copyright_creativity.gov` 
- `copyright_eservice.gov`
- `copyright_legislation.gov`
- `copyright_events.gov`

## 🛠️ **Устранение проблем**

### **"Chat not found"**
```python
# ❌ Неправильно:
CHAT_ID = -2874882097

# ✅ Правильно для супергрупп:  
CHAT_ID = -1002874882097
```

### **"Not enough rights"**
- Бот должен быть администратором
- Нужны права: `manage_topics`, `pin_messages`

### **Rate Limiting (429)**
```bash
# Подождите указанное время и повторите
sleep 30
python3 create_topics.py
```

### **Топик создался, сообщение не отправилось**
- Проверьте права на отправку сообщений
- Убедитесь что топики включены в группе

## 📁 **Файлы результатов**

### **`created_topics_result.json`**
```json
[
  {
    "name": "🏛️ World Trademark Review",
    "topic_id": 2,
    "message_id": 3
  }
]
```

### **Использование результатов:**
```python
import json

# Загрузка результатов
with open('created_topics_result.json') as f:
    topics = json.load(f)

# Автоматическое добавление в users.yaml
for topic in topics:
    print(f"{topic['source']}: {topic['topic_id']}")
```

## 🔄 **Hot Reload конфигурации**

После изменения `topics_mapping` в `users.yaml`:

```bash
# Перезагрузка конфигурации пользователей
kill -USR2 <user_service_pid>
```

## 📅 **История изменений**

- **25.07.2025:** Создан скрипт автоматического создания топиков
- **25.07.2025:** Добавлено 9 топиков для IP/Copyright источников
- **25.07.2025:** Создана документация по управлению топиками

---

**💡 Совет:** Сохраняйте резервные копии `created_topics_result.json` для восстановления маппингов при необходимости. 
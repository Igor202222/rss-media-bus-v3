#!/usr/bin/env python3
"""
🤖 Скрипт для автоматического создания топиков в Telegram

📋 НАЗНАЧЕНИЕ:
   Автоматически создает топики в Telegram супергруппе через Bot API
   для новых RSS источников, отправляет описание и закрепляет сообщения.

🔧 ИСПОЛЬЗОВАНИЕ:
   1. Настройте BOT_TOKEN, CHAT_ID и список topics
   2. Запустите: python3 create_topics.py
   3. Скрипт создаст топики, отправит описания и закрепит сообщения
   4. Результаты сохранятся в created_topics_result.json

⚠️ ТРЕБОВАНИЯ:
   - Бот должен быть администратором в чате
   - Чат должен быть супергруппой с включенными топиками
   - Нужны права: manage_topics, pin_messages

📅 ИСТОРИЯ:
   - Создан: 25 июля 2025
   - Использован для создания 9 топиков для IP/copyright источников
   - Топики: 2, 4, 6, 8, 10, 12, 14, 16, 18

💡 СОВЕТЫ:
   - При rate limiting (429) просто подождите и запустите заново
   - Можно изменить icon_color для разных цветов топиков
   - Формат CHAT_ID для супергрупп: -100{original_id}
"""

import requests
import time
import json

# Конфигурация
BOT_TOKEN = "7505196648:AAE7ijtIAHS91ZvQyT3OPyCH6g9N42zSWuY"
CHAT_ID = -1002874882097
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Топики для создания
topics = [
    {
        "name": "🏛️ World Trademark Review",
        "icon_color": 0x6FB9F0,
        "pin_message": """📡 RSS: World Trademark Review
🔗 Источник: https://www.worldtrademarkreview.com/rss
📝 Новости о товарных знаках и интеллектуальной собственности"""
    },
    {
        "name": "🤖 ChatGPT World", 
        "icon_color": 0x00C851,
        "pin_message": """📡 RSS: ChatGPT is Eating the World
🔗 Источник: https://chatgptiseatingtheworld.com/feed/
📝 Новости об AI и ChatGPT"""
    },
    {
        "name": "🌍 WIPO News",
        "icon_color": 0x007BFF,
        "pin_message": """📡 RSS: WIPO - World Intellectual Property Organization
🔗 Источник: https://www.wipo.int/portal/en/rss
📝 Официальные новости ВОИС"""
    },
    {
        "name": "🏴‍☠️ TorrentFreak",
        "icon_color": 0x000000,
        "pin_message": """📡 RSS: TorrentFreak
🔗 Источник: https://torrentfreak.com/feed
📝 Новости о пиратстве и авторских правах"""
    },
    {
        "name": "⚖️ Bloomberg IP Law",
        "icon_color": 0x6C757D,
        "pin_message": """📡 RSS: Bloomberg Law - IP Law
🔗 Источник: https://news.bloomberglaw.com/rss/ip-law
📝 Правовые новости в сфере IP"""
    },
    {
        "name": "🇺🇸 USPTO",
        "icon_color": 0xDC3545,
        "pin_message": """📡 RSS: USPTO - US Patent and Trademark Office
🔗 Источник: https://www.uspto.gov/rss.xml
📝 Официальные новости USPTO"""
    },
    {
        "name": "🇷🇺 РАПСИ Новости",
        "icon_color": 0xFF6B6B,
        "pin_message": """📡 RSS: РАПСИ Новости
🔗 Источник: http://rapsinews.ru/export/rss2/index.xml
📝 Российское агентство правовой и судебной информации"""
    },
    {
        "name": "📄 Copyright Lately",
        "icon_color": 0xFFC107,
        "pin_message": """📡 RSS: Copyright Lately
🔗 Источник: https://copyrightlately.com/rss
📝 Новости об авторских правах"""
    },
    {
        "name": "🏛️ US Copyright Office",
        "icon_color": 0x28A745,
        "pin_message": """📡 RSS: US Copyright Office (объединенная лента)
🔗 Источники:
• Case Act: https://www.copyright.gov/rss/case_act.xml
• Creativity: https://www.copyright.gov/rss/creativity.xml
• eService: https://www.copyright.gov/rss/eservice.xml
• Legislation: https://www.copyright.gov/rss/legislation.xml
• Events: https://www.copyright.gov/rss/events.xml
📝 Официальные новости Бюро авторских прав США"""
    }
]

def create_topic(name, icon_color):
    """Создает топик в Telegram чате"""
    url = f"{BASE_URL}/createForumTopic"
    data = {
        "chat_id": CHAT_ID,
        "name": name,
        "icon_color": icon_color
    }
    
    response = requests.post(url, json=data)
    return response.json()

def send_message(message_thread_id, text):
    """Отправляет сообщение в топик"""
    url = f"{BASE_URL}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "message_thread_id": message_thread_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    response = requests.post(url, json=data)
    return response.json()

def pin_message(message_thread_id, message_id):
    """Закрепляет сообщение в топике"""
    url = f"{BASE_URL}/pinChatMessage"
    data = {
        "chat_id": CHAT_ID,
        "message_id": message_id,
        "disable_notification": True
    }
    
    response = requests.post(url, json=data)
    return response.json()

def main():
    print("🚀 Создание топиков для RSS источников...")
    print(f"📱 Чат: {CHAT_ID}")
    print(f"🤖 Бот: {BOT_TOKEN[:10]}...")
    print()
    
    created_topics = []
    
    for i, topic in enumerate(topics, 1):
        print(f"📝 Создаю топик {i}/9: {topic['name']}")
        
        # Создаем топик
        result = create_topic(topic['name'], topic['icon_color'])
        
        if result.get('ok'):
            topic_id = result['result']['message_thread_id']
            print(f"✅ Топик создан! ID: {topic_id}")
            
            # Ждем немного
            time.sleep(1)
            
            # Отправляем сообщение с информацией об RSS
            print(f"📌 Отправляю информацию об RSS...")
            msg_result = send_message(topic_id, topic['pin_message'])
            
            if msg_result.get('ok'):
                message_id = msg_result['result']['message_id']
                print(f"✅ Сообщение отправлено! ID: {message_id}")
                
                # Закрепляем сообщение
                time.sleep(1)
                pin_result = pin_message(topic_id, message_id)
                
                if pin_result.get('ok'):
                    print(f"📌 Сообщение закреплено!")
                else:
                    print(f"⚠️ Не удалось закрепить: {pin_result}")
                
                created_topics.append({
                    'name': topic['name'],
                    'topic_id': topic_id,
                    'message_id': message_id
                })
            else:
                print(f"❌ Ошибка отправки сообщения: {msg_result}")
        else:
            print(f"❌ Ошибка создания топика: {result}")
        
        print()
        time.sleep(2)  # Пауза между созданием топиков
    
    print("=" * 50)
    print("🎉 РЕЗУЛЬТАТЫ СОЗДАНИЯ ТОПИКОВ:")
    print("=" * 50)
    
    for topic in created_topics:
        print(f"📝 {topic['name']}")
        print(f"   🆔 Topic ID: {topic['topic_id']}")
        print(f"   💬 Message ID: {topic['message_id']}")
        print()
    
    print(f"✅ Создано топиков: {len(created_topics)}/{len(topics)}")
    
    # Сохраняем результаты в файл
    with open('created_topics_result.json', 'w', encoding='utf-8') as f:
        json.dump(created_topics, f, ensure_ascii=False, indent=2)
    
    print("💾 Результаты сохранены в created_topics_result.json")

if __name__ == "__main__":
    main()

# ============================================================================
# 📖 ДОКУМЕНТАЦИЯ И ПРИМЕРЫ
# ============================================================================

"""
🎯 ПРИМЕР ДОБАВЛЕНИЯ НОВЫХ ТОПИКОВ:

1. Добавьте новый источник в config/sources.yaml:
   new_source.com:
     url: "https://new-source.com/rss"
     name: "New Source"
     active: true

2. Добавьте топик в список topics выше:
   {
       "name": "📰 New Source",
       "icon_color": 0x17A2B8,  # Цвет иконки (hex)
       "pin_message": '''📡 RSS: New Source
🔗 Источник: https://new-source.com/rss
📝 Описание нового источника'''
   }

3. Запустите скрипт: python3 create_topics.py

4. Добавьте mapping в config/users.yaml:
   ip_scan_bot:
     topics_mapping:
       new_source.com: <полученный_topic_id>

🎨 ДОСТУПНЫЕ ЦВЕТА ИКОНОК:
   0x6FB9F0  # Голубой
   0x00C851  # Зеленый  
   0x007BFF  # Синий
   0x000000  # Черный
   0x6C757D  # Серый
   0xDC3545  # Красный
   0xFF6B6B  # Розовый
   0xFFC107  # Желтый
   0x28A745  # Темно-зеленый
   0x17A2B8  # Бирюзовый
   0x6F42C1  # Фиолетовый

🔧 TROUBLESHOOTING:

- Ошибка "chat not found":
  Проверьте формат CHAT_ID. Для супергрупп: -100{id}

- Ошибка "not enough rights":
  Бот должен быть админом с правами manage_topics

- Ошибка 429 "Too Many Requests":
  Подождите указанное время и запустите заново

- Топик создался, но сообщение не отправилось:
  Проверьте права bot на отправку сообщений

📁 РЕЗУЛЬТАТЫ:
   created_topics_result.json - содержит ID созданных топиков
   Используйте эти ID для mapping в users.yaml
""" 
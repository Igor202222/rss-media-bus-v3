#!/usr/bin/env python3
"""
Скрипт для создания оставшихся топиков
"""

import requests
import time
import json

# Конфигурация
BOT_TOKEN = "7505196648:AAE7ijtIAHS91ZvQyT3OPyCH6g9N42zSWuY"
CHAT_ID = -1002874882097
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Оставшиеся топики
remaining_topics = [
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
    print("🚀 Создание оставшихся топиков...")
    
    created_topics = []
    
    for i, topic in enumerate(remaining_topics, 1):
        print(f"📝 Создаю топик {i}/2: {topic['name']}")
        
        # Создаем топик
        result = create_topic(topic['name'], topic['icon_color'])
        
        if result.get('ok'):
            topic_id = result['result']['message_thread_id']
            print(f"✅ Топик создан! ID: {topic_id}")
            
            # Ждем немного
            time.sleep(2)
            
            # Отправляем сообщение с информацией об RSS
            print(f"📌 Отправляю информацию об RSS...")
            msg_result = send_message(topic_id, topic['pin_message'])
            
            if msg_result.get('ok'):
                message_id = msg_result['result']['message_id']
                print(f"✅ Сообщение отправлено! ID: {message_id}")
                
                # Закрепляем сообщение
                time.sleep(2)
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
        time.sleep(5)  # Больше времени между топиками
    
    print("=" * 50)
    print("🎉 ОСТАВШИЕСЯ ТОПИКИ СОЗДАНЫ:")
    print("=" * 50)
    
    for topic in created_topics:
        print(f"📝 {topic['name']}")
        print(f"   🆔 Topic ID: {topic['topic_id']}")
        print(f"   💬 Message ID: {topic['message_id']}")
        print()
    
    print(f"✅ Создано дополнительно: {len(created_topics)}/2")

if __name__ == "__main__":
    main() 
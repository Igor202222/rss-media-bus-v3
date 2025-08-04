#!/usr/bin/env python3
"""
🤖 Скрипт для создания топиков в Telegram для magazine_scan_270725_bot

📋 НАЗНАЧЕНИЕ:
   Создает топики для 15 новых RSS источников в супергруппе -1002804553475
   Названия топиков: только названия источников без дополнений
   
🔧 ИСПОЛЬЗОВАНИЕ:
   python3 create_magazine_topics.py

⚠️ ТРЕБОВАНИЯ:
   - Бот @magazine_scan_270725_bot должен быть администратором в чате
   - Чат должен быть супергруппой с включенными топиками
   - Нужны права: manage_topics, pin_messages

📅 Создан: 27 июля 2025 для RSS Media Bus v3.1
"""

import requests
import time
import json

# Конфигурация нового бота
BOT_TOKEN = "8308777401:AAGRKAXL1eOAU756BrkZgcn5ChuguGjps3g"
CHAT_ID = -1002804553475
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Топики для создания (только названия источников, без дополнений)
topics = [
    {
        "name": "Futurism",
        "source_id": "futurism.com",
        "url": "https://futurism.com/feed",
        "icon_color": 0x6FB9F0
    },
    {
        "name": "The Decoder", 
        "source_id": "the-decoder.com",
        "url": "https://the-decoder.com/feed/",
        "icon_color": 0x00C851
    },
    {
        "name": "Mpost",
        "source_id": "mpost.io", 
        "url": "https://mpost.io/rss",
        "icon_color": 0x007BFF
    },
    {
        "name": "Design Milk",
        "source_id": "design-milk.com",
        "url": "https://design-milk.com/feed/",
        "icon_color": 0xFF6B6B
    },
    {
        "name": "Hypebeast",
        "source_id": "hypebeast.com",
        "url": "http://feeds.feedburner.com/hypebeast/feed",
        "icon_color": 0x000000
    },
    {
        "name": "Dezeen",
        "source_id": "dezeen.com",
        "url": "https://www.dezeen.com/feed/",
        "icon_color": 0x6C757D
    },
    {
        "name": "Artnet News",
        "source_id": "artnet.com",
        "url": "https://news.artnet.com/feed",
        "icon_color": 0xDC3545
    },
    {
        "name": "It's Nice That",
        "source_id": "itsnicethat.com",
        "url": "http://feeds2.feedburner.com/itsnicethat/SlXC",
        "icon_color": 0xFFC107
    },
    {
        "name": "Creative Bloq",
        "source_id": "creativebloq.com",
        "url": "https://www.creativebloq.com/feed",
        "icon_color": 0x28A745
    },
    {
        "name": "Wired",
        "source_id": "wired.com",
        "url": "https://www.wired.com/feed",
        "icon_color": 0x17A2B8
    },
    {
        "name": "Variety",
        "source_id": "variety.com",
        "url": "https://variety.com/v/digital/feed/",
        "icon_color": 0x6F42C1
    },
    {
        "name": "The Verge",
        "source_id": "theverge_full.com",
        "url": "https://www.theverge.com/rss/index.xml",
        "icon_color": 0xE83E8C
    },
    {
        "name": "The Register",
        "source_id": "theregister.com", 
        "url": "https://www.theregister.com/headlines.atom",
        "icon_color": 0x20C997
    },
    {
        "name": "TechCrunch",
        "source_id": "techcrunch_full.com",
        "url": "https://techcrunch.com/feed/",
        "icon_color": 0xFD7E14
    },
    {
        "name": "Fast Company",
        "source_id": "fastcompany.com",
        "url": "https://www.fastcompany.com/rss",
        "icon_color": 0x6610F2
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
        "parse_mode": "HTML",
        "disable_web_page_preview": True
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
    print("🚀 Создание топиков для magazine_scan_270725_bot...")
    print(f"📱 Чат: {CHAT_ID}")
    print(f"🤖 Бот: @magazine_scan_270725_bot")
    print(f"📊 Топиков к созданию: {len(topics)}")
    print()
    
    created_topics = []
    
    for i, topic in enumerate(topics, 1):
        print(f"📝 Создаю топик {i}/{len(topics)}: {topic['name']}")
        
        # Создаем топик
        result = create_topic(topic['name'], topic['icon_color'])
        
        if result.get('ok'):
            topic_id = result['result']['message_thread_id']
            print(f"✅ Топик создан! ID: {topic_id}")
            
            # Ждем 2 секунды (таймаут)
            time.sleep(2)
            
            # Формируем сообщение с информацией об RSS
            pin_message_text = f"""📡 RSS: {topic['name']}
🔗 Источник: {topic['url']}
🆔 Source ID: {topic['source_id']}"""
            
            print(f"📌 Отправляю информацию об RSS...")
            msg_result = send_message(topic_id, pin_message_text)
            
            if msg_result.get('ok'):
                message_id = msg_result['result']['message_id']
                print(f"✅ Сообщение отправлено! ID: {message_id}")
                
                # Закрепляем сообщение (с таймаутом)
                time.sleep(1)
                pin_result = pin_message(topic_id, message_id)
                
                if pin_result.get('ok'):
                    print(f"📌 Сообщение закреплено!")
                else:
                    print(f"⚠️ Не удалось закрепить: {pin_result}")
                
                created_topics.append({
                    'name': topic['name'],
                    'source_id': topic['source_id'],
                    'topic_id': topic_id,
                    'message_id': message_id,
                    'url': topic['url']
                })
            else:
                print(f"❌ Ошибка отправки сообщения: {msg_result}")
                # Все равно сохраняем ID топика
                created_topics.append({
                    'name': topic['name'],
                    'source_id': topic['source_id'],
                    'topic_id': topic_id,
                    'message_id': None,
                    'url': topic['url']
                })
        else:
            print(f"❌ Ошибка создания топика: {result}")
            if result.get('error_code') == 429:
                retry_after = result.get('parameters', {}).get('retry_after', 30)
                print(f"⏳ Rate limit! Жду {retry_after} секунд...")
                time.sleep(retry_after)
                # Повторяем попытку
                result = create_topic(topic['name'], topic['icon_color'])
                if result.get('ok'):
                    topic_id = result['result']['message_thread_id']
                    print(f"✅ Топик создан после ожидания! ID: {topic_id}")
                    created_topics.append({
                        'name': topic['name'],
                        'source_id': topic['source_id'],
                        'topic_id': topic_id,
                        'message_id': None,
                        'url': topic['url']
                    })
        
        print()
        # Таймаут между созданием топиков
        if i < len(topics):  # Не ждем после последнего
            time.sleep(3)
    
    print("=" * 60)
    print("🎉 РЕЗУЛЬТАТЫ СОЗДАНИЯ ТОПИКОВ:")
    print("=" * 60)
    
    for topic in created_topics:
        print(f"📝 {topic['name']}")
        print(f"   🆔 Topic ID: {topic['topic_id']}")
        print(f"   🔗 Source ID: {topic['source_id']}")
        if topic['message_id']:
            print(f"   💬 Message ID: {topic['message_id']}")
        print()
    
    print(f"✅ Создано топиков: {len(created_topics)}/{len(topics)}")
    
    # Сохраняем результаты в файл
    result_filename = 'magazine_topics_result.json'
    with open(result_filename, 'w', encoding='utf-8') as f:
        json.dump(created_topics, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Результаты сохранены в {result_filename}")
    
    # Создаем маппинг для users.yaml
    print()
    print("=" * 60)
    print("📋 МАППИНГ ДЛЯ config/users.yaml:")
    print("=" * 60)
    print("magazine_scan_270725_bot:")
    print("  topics_mapping:")
    for topic in created_topics:
        print(f"    {topic['source_id']}: {topic['topic_id']}")
    print()

if __name__ == "__main__":
    main() 
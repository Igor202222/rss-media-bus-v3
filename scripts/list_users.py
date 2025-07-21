#!/usr/bin/env python3

"""
list_users.py - Список пользователей RSS Media Bus v3.0
"""

import yaml
import sys
from datetime import datetime

def load_users():
    """Загрузка пользователей из config/users.yaml"""
    try:
        with open('config/users.yaml', 'r', encoding='utf-8') as f:
            users = yaml.safe_load(f)
        return users if users else {}
    except FileNotFoundError:
        print("❌ Файл config/users.yaml не найден")
        return {}
    except Exception as e:
        print(f"❌ Ошибка чтения config/users.yaml: {e}")
        return {}

def format_datetime(dt_str):
    """Форматирование даты для отображения"""
    if not dt_str:
        return "неизвестно"
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime('%d.%m.%Y %H:%M')
    except:
        return dt_str

def main():
    print("👥 RSS Media Bus v3.0 - Список пользователей")
    print("=" * 50)
    
    users = load_users()
    
    if not users:
        print("😔 Пользователи не найдены")
        print("\n💡 Добавить пользователя:")
        print("   ./scripts/add_user.sh \"user_id\" \"Имя\" \"chat_id\" \"bot_token\"")
        return
    
    # Статистика
    total = len(users)
    active = sum(1 for u in users.values() if u and u.get('active'))
    telegram_enabled = sum(1 for u in users.values() 
                          if u and u.get('active') and 
                          u.get('telegram', {}).get('enabled'))
    
    print(f"📊 Статистика:")
    print(f"   Всего пользователей: {total}")
    print(f"   Активных: {active}")
    print(f"   С включенным Telegram: {telegram_enabled}")
    print()
    
    # Список пользователей
    print("📋 Список пользователей:")
    print("-" * 50)
    
    for user_id, user_data in users.items():
        if not user_data:
            continue
            
        # Базовая информация
        name = user_data.get('name', 'Без имени')
        active_status = "✅" if user_data.get('active') else "❌"
        created_at = format_datetime(user_data.get('created_at'))
        
        # Telegram информация
        telegram = user_data.get('telegram', {})
        telegram_enabled = telegram.get('enabled', False)
        chat_id = telegram.get('chat_id', 'не указан')
        telegram_status = "✅" if telegram_enabled else "❌"
        
        # Источники
        sources = user_data.get('sources', [])
        sources_count = len(sources)
        
        # Процессоры
        processors = user_data.get('processors', [])
        processors_list = [p.get('name', 'unnamed') for p in processors]
        
        print(f"👤 {user_id}")
        print(f"   📝 Имя: {name}")
        print(f"   🔄 Активен: {active_status}")
        print(f"   📱 Telegram: {telegram_status} ({chat_id})")
        print(f"   📡 Источников: {sources_count}")
        if sources_count <= 10:
            print(f"   📋 Источники: {', '.join(sources[:5])}{'...' if sources_count > 5 else ''}")
        print(f"   🔧 Процессоры: {', '.join(processors_list)}")
        print(f"   📅 Создан: {created_at}")
        print(f"   📄 Метод: {user_data.get('registration_method', 'unknown')}")
        
        # Дополнительная информация
        if user_data.get('description'):
            print(f"   💬 Описание: {user_data['description']}")
        
        print()
    
    # Рекомендации
    print("💡 Управление пользователями:")
    print(f"   Добавить: ./scripts/add_user.sh \"new_user\" \"Имя\" \"chat_id\" \"bot_token\"")
    print(f"   Мониторинг: ./scripts/monitor_system.sh")
    print(f"   Перезапуск User Service: kill $(ps aux | grep user_notification | awk '{{print $2}}')")

if __name__ == "__main__":
    main() 
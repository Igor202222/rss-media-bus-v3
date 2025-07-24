#!/usr/bin/env python3
"""
Скрипт для обновления topics_mapping в users.yaml
на основе созданных топиков из topics_mapping_result.json
"""

import json
import yaml
from pathlib import Path

def update_users_config():
    """Обновляет topics_mapping в config/users.yaml"""
    
    # Загружаем результат создания топиков
    topics_file = Path("topics_mapping_result.json")
    if not topics_file.exists():
        print("❌ Файл topics_mapping_result.json не найден")
        return False
    
    with open(topics_file, 'r', encoding='utf-8') as f:
        topics_mapping = json.load(f)
    
    if not topics_mapping:
        print("❌ topics_mapping пустой")
        return False
    
    print(f"📋 Загружено {len(topics_mapping)} топиков")
    
    # Загружаем текущую конфигурацию пользователей
    users_file = Path("config/users.yaml")
    
    with open(users_file, 'r', encoding='utf-8') as f:
        users_config = yaml.safe_load(f)
    
    # Обновляем topics_mapping для активного пользователя
    updated_count = 0
    
    for user_id, user_data in users_config.items():
        telegram_configs = user_data.get('telegram_configs', {})
        
        for config_id, telegram_config in telegram_configs.items():
            # Обновляем topics_mapping
            telegram_config['topics_mapping'] = topics_mapping.copy()
            updated_count += 1
            
            print(f"✅ Обновлен mapping для {user_id}::{config_id}")
            print(f"   📊 Топиков: {len(topics_mapping)}")
    
    # Сохраняем обновленную конфигурацию
    with open(users_file, 'w', encoding='utf-8') as f:
        yaml.dump(users_config, f, default_flow_style=False, indent=2, allow_unicode=True)
    
    print(f"\n💾 Конфигурация сохранена")
    print(f"✅ Обновлено конфигураций: {updated_count}")
    
    # Показываем пример обновленного mapping
    print(f"\n🎯 Пример созданных топиков:")
    for i, (source, topic_id) in enumerate(list(topics_mapping.items())[:10]):
        print(f"  {source}: {topic_id}")
    if len(topics_mapping) > 10:
        print(f"  ... и еще {len(topics_mapping) - 10}")
    
    return True

if __name__ == "__main__":
    print("🔧 Обновление topics_mapping в users.yaml")
    print("=" * 50)
    
    success = update_users_config()
    
    if success:
        print("\n🎉 Обновление завершено успешно!")
        print("🔄 Можете перезапускать RSS Bus систему")
    else:
        print("\n❌ Обновление не удалось") 
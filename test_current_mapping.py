import yaml

# Загружаем текущий конфиг
with open('config/users.yaml', 'r') as f:
    config = yaml.safe_load(f)

print("🔍 ПРОВЕРКА ТОПИКОВ ДЛЯ WORLDTRADEMARKREVIEW.COM")
print("=" * 60)

# Проверяем для всех ботов
bots = config['smm_gov_redaktor']['telegram_configs']

for bot_name, bot_config in bots.items():
    topics_mapping = bot_config.get('topics_mapping', {})
    
    if 'worldtrademarkreview.com' in topics_mapping:
        topic = topics_mapping['worldtrademarkreview.com']
        if isinstance(topic, dict):
            topic_id = topic.get('topic_id')
            translate = topic.get('translate', False)
            print(f"✅ {bot_name}: топик {topic_id}, перевод {translate}")
        else:
            print(f"✅ {bot_name}: топик {topic}")
    else:
        print(f"❌ {bot_name}: НЕ НАЙДЕН")

print("\n🔍 ПРОВЕРКА BLOOMBERG_ESG.COM")
print("=" * 60)

for bot_name, bot_config in bots.items():
    topics_mapping = bot_config.get('topics_mapping', {})
    
    if 'bloomberg_esg.com' in topics_mapping:
        topic = topics_mapping['bloomberg_esg.com']
        if isinstance(topic, dict):
            topic_id = topic.get('topic_id')
            translate = topic.get('translate', False)
            print(f"✅ {bot_name}: топик {topic_id}, перевод {translate}")
        else:
            print(f"✅ {bot_name}: топик {topic}")
    else:
        print(f"❌ {bot_name}: НЕ НАЙДЕН")

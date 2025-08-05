import yaml

# Загружаем конфиг
with open('config/users.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Тестируем маппинг для main_all_sources
user_data = config['smm_gov_redaktor']['telegram_configs']['main_all_sources']
topics_mapping = user_data['topics_mapping']

print("=== ТЕСТ МАППИНГА ТОПИКОВ ===")
test_sources = ['bloomberg_esg.com', 'rg.ru', 'google_alerts_feed_2.com']

for source in test_sources:
    if source in topics_mapping:
        topic = topics_mapping[source]
        if isinstance(topic, dict):
            topic_id = topic.get('topic_id')
            translate = topic.get('translate', False)
            print(f"✅ {source}: топик {topic_id}, перевод {translate}")
        else:
            print(f"✅ {source}: топик {topic}")
    else:
        print(f"❌ {source}: НЕ НАЙДЕН в topics_mapping")

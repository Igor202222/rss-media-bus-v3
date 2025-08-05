import yaml

with open('config/users.yaml', 'r') as f:
    config = yaml.safe_load(f)

print("🌐 ПРОВЕРКА АВТОПЕРЕВОДА ДЛЯ ВСЕХ БОТОВ")
print("=" * 60)

test_sources = [
    'bloomberg_esg.com', 'techcrunch.com', 'bbc.co.uk', 
    'reuters.com', 'tass.ru', 'ria.ru'  # Mix английских и русских
]

bots = config['smm_gov_redaktor']['telegram_configs']

for bot_name, bot_config in bots.items():
    print(f"\n🤖 {bot_name}:")
    
    # Проверяем есть ли translation_settings
    has_translation = 'translation_settings' in bot_config
    print(f"   Translation settings: {'✅' if has_translation else '❌'}")
    
    topics_mapping = bot_config.get('topics_mapping', {})
    
    for source in test_sources:
        if source in topics_mapping:
            topic = topics_mapping[source]
            if isinstance(topic, dict):
                topic_id = topic.get('topic_id')
                translate = topic.get('translate', False)
                status = '🌐' if translate else '🇷🇺'
                print(f"   {status} {source}: топик {topic_id}")
            else:
                print(f"   🇷🇺 {source}: топик {topic}")

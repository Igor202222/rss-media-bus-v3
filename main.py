#!/usr/bin/env python3
"""
RSS Media Bus v3.0 - MVP версия для тестирования
"""

import asyncio
import yaml
from pathlib import Path
from colorama import init, Fore, Style

init()

async def main():
    print(f"{Fore.CYAN}🚀 RSS Media Bus v3.0 - MVP{Style.RESET_ALL}")
    
    # Загрузка конфигураций
    config_dir = Path(__file__).parent / "config"
    
    # Источники
    sources_file = config_dir / "sources.yaml"
    with open(sources_file, 'r', encoding='utf-8') as f:
        sources_config = yaml.safe_load(f)
        sources = sources_config.get('sources', {})
    
    # Пользователи  
    users_file = config_dir / "users.yaml"
    with open(users_file, 'r', encoding='utf-8') as f:
        users_config = yaml.safe_load(f)
        users = users_config.get('users', {})
    
    print(f"✅ Загружено {len(sources)} источников")
    print(f"✅ Загружено {len(users)} пользователей")
    
    # Показ конфигурации
    for user_id, user_config in users.items():
        print(f"\n🔧 Пользователь: {user_config.get('name')}")
        user_sources = user_config.get('sources', [])
        print(f"  📡 Источников: {len(user_sources)}")
        for source_id in user_sources:
            if source_id in sources:
                print(f"    - {sources[source_id].get('name', source_id)}")

if __name__ == "__main__":
    asyncio.run(main())

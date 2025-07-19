#!/usr/bin/env python3
"""
Создание топика для RSS мониторинга
"""

import asyncio
from outputs.debug_chat_logger import debug_logger

async def create_rss_topic():
    """Создание топика RSS мониторинга"""
    print("🔧 Создание топика для RSS мониторинга...")
    
    success = await debug_logger.create_topic(
        name="📡 RSS Мониторинг", 
        icon_emoji="📡"
    )
    
    if success:
        print("✅ Топик создан успешно!")
        
        # Отправляем тестовое сообщение в новый топик
        await debug_logger.log_rss(
            "Топик RSS мониторинга создан", 
            "Готов к получению логов парсинга источников"
        )
    else:
        print("❌ Не удалось создать топик")

if __name__ == "__main__":
    asyncio.run(create_rss_topic()) 
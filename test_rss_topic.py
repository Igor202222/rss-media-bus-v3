#!/usr/bin/env python3
"""
Тест отправки логов в RSS топик
"""

import asyncio
from outputs.debug_chat_logger import log_rss

async def test_rss_topic():
    """Тест отправки в RSS топик"""
    print("🧪 Тестирование RSS топика...")
    
    # Отправляем тестовое сообщение
    await log_rss(
        "Тест RSS топика",
        "Проверка отправки сводного отчета RSS мониторинга в топик"
    )
    
    # Отправляем сводный отчет (имитация)
    test_report = """📈 Статистика:
• Всего источников: 6
• Доступны: 4
• Недоступны: 2
• Новых статей: 15
• Время цикла: 45.2с

✅ Доступные источники:
• ТАСС: 8 новых
• РИА Новости: 5 новых
• РБК: 2 новых
• TechCrunch: без новых

❌ Недоступные источники:
• Reuters: timeout
• BBC: connection error"""
    
    await log_rss("Сводный отчет RSS мониторинга", test_report)
    
    print("✅ Тест завершен - проверьте топик в Telegram!")

if __name__ == "__main__":
    asyncio.run(test_rss_topic()) 
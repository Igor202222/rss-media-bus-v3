#!/usr/bin/env python3
"""
RSS Media Bus - Debug Chat Logger v3.0
Отправка логов в Telegram чат с топиками
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Optional
from telegram import Bot
from telegram.constants import ParseMode

class LogLevel(Enum):
    SYSTEM = "🔧 СИСТЕМА"
    USER = "👤 ПОЛЬЗОВАТЕЛИ" 
    RSS = "📡 RSS МОНИТОРИНГ"
    ERROR = "❌ ОШИБКИ"

class DebugChatLogger:
    def __init__(self):
        # Telegram Bot для логирования
        self.bot_token = "8171335651:AAFv3gO3dCZTLxu62JLtWsK6Gza7bdAoYVc"
        self.chat_id = "-1002756550488"  # Обновленный ID супергруппы
        
        # Топики для разных типов логов
        self.topics = {
            LogLevel.SYSTEM: None,      # Общий топик
            LogLevel.USER: None,        # Создать топик "Пользователи"
            LogLevel.RSS: 3,            # Топик "RSS Мониторинг" (создан)
            LogLevel.ERROR: None,       # Создать топик "Ошибки"
        }
        
        self.bot = Bot(token=self.bot_token)
        self.logger = logging.getLogger(__name__)
        
    async def log(self, level: LogLevel, message: str, details: Optional[str] = None):
        """Отправить лог в Telegram чат"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Формируем сообщение
            full_message = f"{level.value} [{timestamp}]\n\n{message}"
            
            if details:
                full_message += f"\n\n📝 Детали:\n{details}"
            
            # Отправляем в соответствующий топик
            topic_id = self.topics.get(level)
            
            # Отправляем сообщение
            kwargs = {
                "chat_id": self.chat_id,
                "text": full_message,
                "parse_mode": ParseMode.MARKDOWN_V2 if self._is_markdown_safe(full_message) else None
            }
            
            # Добавляем топик только если он задан
            if topic_id is not None:
                kwargs["message_thread_id"] = topic_id
                
            await self.bot.send_message(**kwargs)
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки лога: {e}")
    
    def _is_markdown_safe(self, text: str) -> bool:
        """Проверка безопасности Markdown"""
        dangerous_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        return not any(char in text for char in dangerous_chars)
    
    async def log_system(self, message: str, details: str = None):
        """Системные логи"""
        await self.log(LogLevel.SYSTEM, message, details)
    
    async def log_user(self, message: str, details: str = None):
        """Логи пользователей"""
        await self.log(LogLevel.USER, message, details)
    
    async def log_rss(self, message: str, details: str = None):
        """Логи RSS мониторинга"""
        await self.log(LogLevel.RSS, message, details)
    
    async def log_error(self, message: str, details: str = None):
        """Логи ошибок"""
        await self.log(LogLevel.ERROR, message, details)
    
    async def create_topic(self, name: str, icon_emoji: str = "📡") -> bool:
        """Создание топика в чате"""
        try:
            # Создаем топик через Bot API
            response = await self.bot.create_forum_topic(
                chat_id=self.chat_id,
                name=name,
                icon_custom_emoji_id=icon_emoji if icon_emoji else None
            )
            
            topic_id = response.message_thread_id
            print(f"✅ Создан топик '{name}' с ID: {topic_id}")
            
            # Сохраняем ID топика для RSS логов
            if "RSS" in name or "мониторинг" in name.lower():
                self.topics[LogLevel.RSS] = topic_id
                print(f"📡 Топик RSS установлен: {topic_id}")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания топика '{name}': {e}")
            return False

# Глобальный экземпляр логгера
debug_logger = DebugChatLogger()

# Быстрые функции для логирования
async def log_system(message: str, details: str = None):
    await debug_logger.log_system(message, details)

async def log_user(message: str, details: str = None):
    await debug_logger.log_user(message, details)
    
async def log_rss(message: str, details: str = None):
    await debug_logger.log_rss(message, details)

async def log_error(message: str, details: str = None):
    await debug_logger.log_error(message, details)

# Тестирование
async def test_logger():
    """Тест отправки логов"""
    await log_system("Debug логгер запущен", "Версия: v3.0")
    await log_rss("Тестирование RSS мониторинга", "Проверка отправки в топик RSS")
    
if __name__ == "__main__":
    asyncio.run(test_logger()) 
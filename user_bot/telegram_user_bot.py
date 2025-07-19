#!/usr/bin/env python3
"""
RSS Media Bus - Простой пользовательский бот для базовой авторизации
"""

import asyncio
import json
import yaml
import sys
from pathlib import Path
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Добавляем путь к outputs для импорта debug_chat_logger
sys.path.append(str(Path(__file__).parent.parent / "outputs"))

try:
    from debug_chat_logger import create_debug_logger
except ImportError:
    print("⚠️ Debug логгер не найден, логирование отключено")
    def create_debug_logger():
        return None

class TelegramUserBot:
    def __init__(self, bot_token: str):
        """
        bot_token: Токен бота для пользователей
        """
        self.bot_token = bot_token
        self.config_dir = Path(__file__).parent.parent / "config"
        self.users_file = self.config_dir / "users.yaml"
        # Используем единое хранение в config/users.yaml
        
        # База пользователей
        self.users = self._load_users_from_yaml()
        
        # Debug логгер
        self.debug_logger = create_debug_logger()
        if self.debug_logger:
            print("📊 Debug логгер подключен")
        
    def _load_users_from_yaml(self) -> dict:
        """Загрузка пользователей из config/users.yaml"""
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                users = config.get('users', {})
                # Конвертируем в формат для работы бота (по telegram_id)
                users_by_telegram_id = {}
                for user_key, user_data in users.items():
                    if 'telegram_id' in user_data:
                        telegram_id = str(user_data['telegram_id'])
                        users_by_telegram_id[telegram_id] = {
                            "user_id": user_key,
                            "telegram_id": user_data['telegram_id'],
                            "username": user_data.get('username', 'unknown'),
                            "first_name": user_data.get('first_name', ''),
                            "created_at": user_data.get('created_at', ''),
                            "name": user_data.get('name', ''),
                            "active": user_data.get('active', True),
                            "sources": user_data.get('sources', []),
                            "telegram": user_data.get('telegram', {})
                        }
                return users_by_telegram_id
        except Exception as e:
            print(f"❌ Ошибка загрузки пользователей: {e}")
            return {}
    
    def _save_users_to_yaml(self):
        """Сохранение пользователей в config/users.yaml"""
        try:
            # Загружаем полный конфиг
            with open(self.users_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if 'users' not in config:
                config['users'] = {}
            
            # Обновляем пользователей из бота
            for telegram_id, user_data in self.users.items():
                user_key = user_data['user_id']
                config['users'][user_key] = {
                    'name': user_data['name'],
                    'description': f"Автоматически зарегистрированный пользователь через бота",
                    'active': user_data['active'],
                    'registration_method': 'telegram_bot',
                    'telegram_id': user_data['telegram_id'],
                    'username': user_data['username'],
                    'first_name': user_data['first_name'],
                    'created_at': user_data['created_at'],
                    'telegram': user_data['telegram'],
                    'sources': user_data['sources'],
                    'processors': [
                        {
                            'name': 'telegram_sender',
                            'config': {
                                'format': 'markdown',
                                'include_source': True,
                                'max_preview_length': 200
                            }
                        }
                    ]
                }
            
            # Сохраняем обновленный конфиг
            with open(self.users_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, ensure_ascii=False, indent=2)
                
            print(f"✅ Пользователи сохранены в {self.users_file}")
            
        except Exception as e:
            print(f"❌ Ошибка сохранения пользователей: {e}")
    
    def _is_user_exists(self, user_id: int) -> bool:
        """Проверка существования пользователя"""
        return str(user_id) in self.users
    
    def _create_user_id(self, telegram_id: int, username: str = None) -> str:
        """Создание уникального ID пользователя"""
        if username:
            base_id = f"user_{username}_{telegram_id}"
        else:
            base_id = f"user_{telegram_id}"
        return base_id[:50]
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start - простая авторизация"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "unknown"
        first_name = update.effective_user.first_name or ""
        
        if self._is_user_exists(user_id):
            # Пользователь уже существует
            user_data = self.users[str(user_id)]
            keyboard = [
                [KeyboardButton("📊 Мои источники"), KeyboardButton("📈 Статистика")],
                [KeyboardButton("🆘 Помощь"), KeyboardButton("⚙️ Настройки")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            # Логируем возвращение пользователя
            if self.debug_logger:
                await self.debug_logger.log_user_action(
                    user_id, 
                    "Возвращение в систему",
                    f"Пользователь @{username} вернулся в систему"
                )
            
            await update.message.reply_text(
                f"👋 С возвращением, {first_name}!\n\n"
                f"🆔 Ваш ID: `{user_data['user_id']}`\n"
                f"📅 Регистрация: {user_data['created_at'][:10]}\n"
                f"📡 Источников: {len(user_data.get('sources', []))}\n\n"
                f"Используйте меню для управления.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            # Новый пользователь - простая регистрация
            user_data = {
                "user_id": self._create_user_id(user_id, username),
                "telegram_id": user_id,
                "username": username,
                "first_name": first_name,
                "created_at": datetime.now().isoformat(),
                "name": f"{first_name} Monitor",
                "active": True,
                "sources": ["tass_main", "ria_main"],  # Базовый набор
                "telegram": {
                    "chat_id": str(user_id),
                    "enabled": False  # Включится после настройки токена
                }
            }
            
            # Сохраняем пользователя
            self.users[str(user_id)] = user_data
            self._save_users_to_yaml()
            
            # Логируем регистрацию нового пользователя
            if self.debug_logger:
                await self.debug_logger.log_user_registration(user_id, username, first_name)
            
            await update.message.reply_text(
                f"🎉 **Добро пожаловать в RSS Media Bus!**\n\n"
                f"Привет, {first_name}! Вы зарегистрированы в системе.\n"
                f"🆔 Ваш ID: `{user_data['user_id']}`\n"
                f"📡 Назначено источников: {len(user_data['sources'])}\n\n"
                f"**Следующие шаги:**\n"
                f"1. Создайте бота через @BotFather\n"
                f"2. Настройте токен: `/set_token ВАШ_ТОКЕН`\n"
                f"3. Проверьте настройки: `/status`",
                parse_mode='Markdown'
            )
    
    async def set_token_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /set_token - настройка бот-токена"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "unknown"
        
        if not self._is_user_exists(user_id):
            await update.message.reply_text("❌ Сначала зарегистрируйтесь командой /start")
            return
        
        if not context.args:
            # Логируем попытку настройки токена без аргументов
            if self.debug_logger:
                await self.debug_logger.log_user_action(
                    user_id,
                    "Неудачная попытка настройки токена",
                    "Команда /set_token без аргументов"
                )
            
            await update.message.reply_text(
                "**Использование:** `/set_token ВАШ_ТОКЕН`\n\n"
                "**Пример:** `/set_token 123456789:ABCdef...`\n\n"
                "**Как получить токен:**\n"
                "1. Напишите @BotFather в Telegram\n"
                "2. Выполните команду /newbot\n"
                "3. Задайте имя и username бота\n"
                "4. Скопируйте токен",
                parse_mode='Markdown'
            )
            return
        
        token = context.args[0]
        
        # Простая валидация токена
        if not token or len(token) < 10 or ':' not in token:
            # Логируем неудачную настройку токена
            if self.debug_logger:
                await self.debug_logger.log_token_setup(user_id, username, False)
            
            await update.message.reply_text("❌ Неверный формат токена")
            return
        
        # Обновляем данные пользователя
        self.users[str(user_id)]["telegram"]["bot_token"] = token
        self.users[str(user_id)]["telegram"]["enabled"] = True
        self._save_users_to_yaml()
        
        # Логируем успешную настройку токена
        if self.debug_logger:
            await self.debug_logger.log_token_setup(user_id, username, True)
        
        await update.message.reply_text(
            f"✅ **Токен бота сохранен!**\n\n"
            f"Теперь ваш мониторинг готов к работе.\n"
            f"Используйте /status для проверки настроек.",
            parse_mode='Markdown'
        )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /status - показать настройки пользователя"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "unknown"
        
        if not self._is_user_exists(user_id):
            await update.message.reply_text("❌ Сначала зарегистрируйтесь командой /start")
            return
        
        # Логируем просмотр статуса
        if self.debug_logger:
            await self.debug_logger.log_user_action(
                user_id,
                "Просмотр статуса",
                f"Пользователь @{username} запросил статус"
            )
        
        user_data = self.users[str(user_id)]
        
        # Загружаем источники для расшифровки
        sources_file = self.config_dir / "sources.yaml"
        with open(sources_file, 'r', encoding='utf-8') as f:
            sources_config = yaml.safe_load(f)
            sources = sources_config.get('sources', {})
        
        message = f"📊 **Ваши настройки:**\n\n"
        message += f"🆔 ID: `{user_data['user_id']}`\n"
        message += f"📅 Создан: {user_data['created_at'][:10]}\n"
        message += f"✅ Активен: {'Да' if user_data.get('active', False) else 'Нет'}\n"
        message += f"🤖 Токен: {'Настроен' if user_data.get('telegram', {}).get('bot_token') else 'Не настроен'}\n\n"
        
        user_sources = user_data.get('sources', [])
        message += f"📡 **RSS Источники ({len(user_sources)}):**\n"
        for source_id in user_sources:
            if source_id in sources:
                source_name = sources[source_id].get('name', source_id)
                source_url = sources[source_id].get('url', 'нет URL')
                message += f"  • **{source_name}**\n    `{source_url}`\n\n"
            else:
                message += f"  • {source_id} (неизвестный)\n"
        
        # Показываем общую статистику
        total_users = len(self.users)
        message += f"📈 **Статистика системы:**\n"
        message += f"👥 Всего пользователей: {total_users}\n"
        message += f"📡 Доступно источников: {len(sources)}"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def sources_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /sources - список всех доступных источников"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "unknown"
        
        if not self._is_user_exists(user_id):
            await update.message.reply_text("❌ Сначала зарегистрируйтесь командой /start")
            return
        
        # Логируем просмотр источников
        if self.debug_logger:
            await self.debug_logger.log_user_action(
                user_id,
                "Просмотр источников",
                f"Пользователь @{username} запросил список источников"
            )
        
        # Загружаем все источники
        sources_file = self.config_dir / "sources.yaml"
        with open(sources_file, 'r', encoding='utf-8') as f:
            sources_config = yaml.safe_load(f)
            sources = sources_config.get('sources', {})
        
        user_data = self.users[str(user_id)]
        user_sources = set(user_data.get('sources', []))
        
        message = f"📡 **Доступные RSS источники:**\n\n"
        
        for source_id, source_config in sources.items():
            name = source_config.get('name', source_id)
            category = source_config.get('category', 'unknown')
            language = source_config.get('language', 'unknown')
            active = source_config.get('active', True)
            
            # Отмечаем активные у пользователя
            marker = "✅" if source_id in user_sources else "⭕"
            status = "🟢" if active else "🔴"
            
            message += f"{marker} {status} **{name}**\n"
            message += f"   🏷️ {category} | 🌐 {language}\n"
            message += f"   `{source_id}`\n\n"
        
        message += f"**Обозначения:**\n"
        message += f"✅ - подключен к вам\n"
        message += f"⭕ - доступен\n"
        message += f"🟢 - активен | 🔴 - неактивен"
        
        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help - справка"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "unknown"
        
        # Логируем запрос справки
        if self.debug_logger:
            await self.debug_logger.log_user_action(
                user_id,
                "Запрос справки",
                f"Пользователь @{username} запросил справку"
            )
        
        message = """🆘 **Справка RSS Media Bus**

**Основные команды:**
• `/start` - регистрация в системе
• `/status` - ваши настройки и источники
• `/sources` - все доступные RSS источники
• `/set_token ТОКЕН` - настроить бот для уведомлений

**Создание бота для уведомлений:**
1. Напишите @BotFather в Telegram
2. Выполните `/newbot`
3. Задайте имя: "Мой RSS Monitor"
4. Задайте username: "my_rss_monitor_bot"
5. Скопируйте токен
6. Выполните `/set_token ТОКЕН`

**Статус системы:**
• `/help` - эта справка

RSS Media Bus v3.0 - централизованный мониторинг новостей"""

        await update.message.reply_text(message, parse_mode='Markdown')
    
    async def init_debug_logger(self):
        """Инициализация debug логгера и топиков"""
        if self.debug_logger:
            try:
                await self.debug_logger.init_topics()
                await self.debug_logger.log_system_start("v3.0-user-bot")
                print("✅ Debug логгер инициализирован")
            except Exception as e:
                print(f"❌ Ошибка инициализации debug логгера: {e}")
    
    def run(self):
        """Запуск пользовательского бота"""
        app = Application.builder().token(self.bot_token).build()
        
        # Регистрация обработчиков
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("set_token", self.set_token_command))
        app.add_handler(CommandHandler("status", self.status_command))
        app.add_handler(CommandHandler("sources", self.sources_command))
        app.add_handler(CommandHandler("help", self.help_command))
        
        print(f"🤖 Пользовательский бот RSS Media Bus запущен!")
        print(f"📝 База пользователей: {self.users_file}")
        print(f"👥 Зарегистрировано: {len(self.users)} пользователей")
        
        # Инициализируем debug логгер в фоне
        if self.debug_logger:
            asyncio.create_task(self.init_debug_logger())
        
        # Запуск бота
        app.run_polling()

if __name__ == "__main__":
    # Конфигурация пользовательского бота
    USER_BOT_TOKEN = "7441299677:AAFJn2pDdvQ4BsMVeTBvDzsT8kLpBNDGlwk"  # t.me/rss_media_bus_user_bot
    
    if not USER_BOT_TOKEN or USER_BOT_TOKEN == "YOUR_USER_BOT_TOKEN_HERE":
        print("❌ Настройте USER_BOT_TOKEN перед запуском!")
        print("📝 Создайте бота через @BotFather и добавьте токен")
        exit(1)
    
    bot = TelegramUserBot(USER_BOT_TOKEN)
    bot.run() 
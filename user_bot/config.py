#!/usr/bin/env python3
"""
Конфигурация пользовательского бота RSS Media Bus v3.0
"""

# ============= ОСНОВНЫЕ НАСТРОЙКИ =============

# Токен бота для пользователей (создать через @BotFather)
# ✅ НАСТРОЕНО: 
USER_BOT_TOKEN = "7441299677:AAFJn2pDdvQ4BsMVeTBvDzsT8kLpBNDGlwk"

# Бот: t.me/rss_media_bus_user_bot
# Статус: Готов к тестированию!

# ============= НАСТРОЙКИ АВТОМАТИЧЕСКОЙ РЕГИСТРАЦИИ =============

# Автоматическая регистрация новых пользователей
AUTO_REGISTRATION = True

# Шаблон по умолчанию для новых пользователей
DEFAULT_TEMPLATE = "basic_news"

# Максимальное количество пользователей
MAX_USERS = 1000

# Минимальная длина имени пользователя
MIN_USERNAME_LENGTH = 3

# ============= СООБЩЕНИЯ =============

MESSAGES = {
    "welcome_new": """🎉 **Добро пожаловать в RSS Media Bus!**

Привет, {first_name}! Вы новый пользователь.
🆔 Ваш Telegram ID: `{user_id}`

Выберите шаблон настроек для начала работы:""",

    "welcome_back": """👋 С возвращением, {first_name}!

🆔 Ваш ID: `{user_id}`
📅 Регистрация: {created_at}
📡 Источников: {sources_count}

Используйте меню для управления настройками.""",

    "user_created": """✅ **Пользователь создан!**

🆔 ID: `{user_id}`
📋 Шаблон: {template_name}
📡 Источников: {sources_count}

Теперь настройте ваш бот-токен командой:
`/set_token ВАШ_ТОКЕН`

Создайте бота через @BotFather если его нет.""",

    "token_saved": """✅ Токен бота сохранен!

Теперь ваш мониторинг готов к работе.
Используйте /status для проверки настроек.""",

    "help_text": """🆘 **Справка RSS Media Bus**

**Основные команды:**
• `/start` - регистрация в системе
• `/status` - ваши настройки
• `/set_token ТОКЕН` - настроить бот для уведомлений

**Управление источниками:**
• `/sources` - список доступных источников
• `/add_source ID` - добавить источник
• `/remove_source ID` - убрать источник

**Настройка фильтров:**
• `/keywords` - показать ключевые слова
• `/set_keywords слово1,слово2` - настроить фильтр

**Создание бота:**
1. Напишите @BotFather в Telegram
2. Выполните /newbot
3. Скопируйте токен
4. Используйте /set_token ТОКЕН"""
}

# ============= ВАЛИДАЦИЯ =============

def validate_config():
    """Проверка корректности конфигурации"""
    errors = []
    
    if not USER_BOT_TOKEN or USER_BOT_TOKEN == "YOUR_USER_BOT_TOKEN_HERE":
        errors.append("❌ Настройте USER_BOT_TOKEN")
    
    if errors:
        print("\n".join(errors))
        print("\n📝 Инструкция по настройке:")
        print("1. Создайте бота через @BotFather")
        print("2. Скопируйте токен в USER_BOT_TOKEN")
        print("3. Запустите бота")
        return False
    
    return True

if __name__ == "__main__":
    if validate_config():
        print("✅ Конфигурация корректна!")
    else:
        print("❌ Конфигурация требует настройки") 
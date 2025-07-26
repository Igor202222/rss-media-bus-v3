#!/usr/bin/env python3
"""
RSS Error Viewer - Утилита для просмотра ошибок RSS источников
Показывает статистику, логи и рекомендации по исправлению
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from core.error_manager import ErrorManager
from core.database import DatabaseManager

def print_separator(title="", char="=", width=80):
    """Печать разделителя с заголовком"""
    if title:
        print(f"\n{char * 10} {title} {char * (width - len(title) - 12)}")
    else:
        print(char * width)

def format_time_ago(timestamp_str):
    """Форматирование времени 'X минут назад'"""
    if not timestamp_str:
        return "неизвестно"
    
    try:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now()
        if timestamp.tzinfo:
            timestamp = timestamp.replace(tzinfo=None)
        
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days} дн. назад"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} ч. назад"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} мин. назад"
        else:
            return "только что"
    except:
        return timestamp_str

def get_status_emoji(error_count, last_error_time):
    """Получить эмодзи статуса источника"""
    if error_count == 0:
        return "✅"
    elif error_count <= 2:
        return "⚠️"
    elif error_count <= 5:
        return "🔴"
    else:
        return "💀"

def show_current_errors():
    """Показать текущие ошибки в памяти"""
    print_separator("ТЕКУЩИЕ ОШИБКИ В ПАМЯТИ")
    
    try:
        db = DatabaseManager()
        error_manager = ErrorManager(db)
        
        stats = error_manager.get_error_statistics()
        
        if stats['total_feeds_with_errors'] == 0:
            print("🎉 Нет активных ошибок!")
            return
        
        print(f"📊 Источников с ошибками: {stats['total_feeds_with_errors']}")
        print(f"📊 Всего ошибок: {stats['total_errors']}")
        
        print_separator("ДЕТАЛИ ПО ИСТОЧНИКАМ")
        
        # Сортируем по количеству ошибок
        sorted_feeds = sorted(
            stats['feeds'].items(), 
            key=lambda x: x[1]['error_count'], 
            reverse=True
        )
        
        for feed_url, data in sorted_feeds:
            status = get_status_emoji(data['error_count'], data['last_error_time'])
            feed_name = data['feed_name'][:50] + "..." if len(data['feed_name']) > 50 else data['feed_name']
            
            print(f"\n{status} {feed_name}")
            print(f"   URL: {feed_url}")
            print(f"   Ошибок: {data['error_count']}")
            print(f"   Последняя: {format_time_ago(data['last_error_time'])}")
            print(f"   Тип: {data['last_error_type']}")
            
            if data['last_status_code']:
                print(f"   HTTP: {data['last_status_code']}")
            
            # Показываем последние ошибки
            if data['recent_errors']:
                print("   Последние ошибки:")
                for err in data['recent_errors'][-3:]:
                    time_ago = format_time_ago(err['timestamp'])
                    print(f"     • {err['error_type']} ({time_ago})")
    
    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")

def show_error_log(lines=50):
    """Показать последние записи из лога ошибок"""
    print_separator(f"ПОСЛЕДНИЕ {lines} ЗАПИСЕЙ ЛОГА ОШИБОК")
    
    log_file = Path("rss_errors.log")
    
    if not log_file.exists():
        print("📝 Лог файл не найден. Ошибок пока не было.")
        return
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        if not all_lines:
            print("📝 Лог файл пустой.")
            return
        
        # Берем последние N строк
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        for line in recent_lines:
            line = line.strip()
            if line:
                # Раскрашиваем по типу
                if "ERROR" in line:
                    print(f"🔴 {line}")
                elif "INFO" in line and "Восстановлен" in line:
                    print(f"✅ {line}")
                else:
                    print(f"📝 {line}")
    
    except Exception as e:
        print(f"❌ Ошибка чтения лога: {e}")

def show_recommendations():
    """Показать рекомендации по исправлению"""
    print_separator("РЕКОМЕНДАЦИИ ПО ИСПРАВЛЕНИЮ")
    
    print("""
🔧 ЧАСТЫЕ ПРОБЛЕМЫ И РЕШЕНИЯ:

1. HTTP 403 Forbidden:
   • Добавить прокси: proxy_required: true
   • Проверить User-Agent в настройках парсера
   • Возможна блокировка по IP/геолокации

2. HTTP 404 Not Found:  
   • Проверить корректность URL RSS
   • Источник мог изменить адрес ленты
   • Временно отключить: active: false

3. Таймауты (TimeoutError):
   • Увеличить timeout в настройках
   • Добавить прокси для стабильности
   • Проверить доступность сервера

4. Сетевые ошибки (ClientError):
   • Проблемы с DNS или сетью
   • Попробовать прокси
   • Проверить интернет-соединение

5. Ошибки парсинга:
   • RSS может быть поврежден
   • Неправильная кодировка
   • Проверить содержимое вручную

📁 ФАЙЛЫ ЛОГОВ:
   • rss_errors.log - детальные ошибки источников
   • rss_core.log - общий лог RSS парсера  
   • user_service.log - лог отправки уведомлений
""")

def export_report():
    """Экспортировать отчет об ошибках"""
    print_separator("ЭКСПОРТ ОТЧЕТА")
    
    try:
        db = DatabaseManager()
        error_manager = ErrorManager(db)
        
        filepath = error_manager.export_error_report()
        print(f"📄 Отчет сохранен: {filepath}")
        
        # Показываем краткую статистику
        stats = error_manager.get_error_statistics()
        print(f"📊 Источников с ошибками: {stats['total_feeds_with_errors']}")
        print(f"📊 Всего ошибок: {stats['total_errors']}")
        
    except Exception as e:
        print(f"❌ Ошибка экспорта: {e}")

def main():
    """Главная функция"""
    print("🛡️ RSS Error Viewer - Просмотр ошибок источников")
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "log":
            lines = int(sys.argv[2]) if len(sys.argv) > 2 else 50
            show_error_log(lines)
        elif command == "export":
            export_report()
        elif command == "help":
            show_recommendations()
        else:
            print(f"❌ Неизвестная команда: {command}")
            print("Доступные команды: log [N], export, help")
            return
    else:
        # По умолчанию показываем все
        show_current_errors()
        show_error_log(20)
        show_recommendations()

if __name__ == "__main__":
    main() 
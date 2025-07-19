#!/usr/bin/env python3
"""
Отправка отчетов о здоровье RSS источников в Telegram
"""

import json
import requests
import sqlite3
import os
from datetime import datetime, timedelta
from long_term_monitor import LongTermMonitor

class TelegramHealthReporter:
    def __init__(self, instance_path='.'):
        self.instance_path = instance_path
        self.config_file = os.path.join(instance_path, 'config.yaml')
        
        # Загружаем конфиг Telegram
        self.load_telegram_config()
        
        # Инициализируем мониторинг
        self.monitor = LongTermMonitor(instance_path)
        
    def load_telegram_config(self):
        """Загружает настройки Telegram из config.yaml"""
        try:
            import yaml
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            telegram_config = config.get('telegram', {})
            self.bot_token = telegram_config.get('bot_token')
            self.chat_id = telegram_config.get('chat_id')
            
            if not self.bot_token or not self.chat_id:
                raise ValueError("Не найдены настройки Telegram в config.yaml")
                
        except Exception as e:
            print(f"❌ Ошибка загрузки конфигурации: {e}")
            # Fallback - попытка прочитать из других источников
            self.bot_token = None
            self.chat_id = None
            
    def send_telegram_message(self, message, topic_id=None):
        """Отправляет сообщение в Telegram"""
        if not self.bot_token or not self.chat_id:
            print("❌ Telegram не настроен")
            return False
            
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        data = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        
        # Добавляем топик если указан
        if topic_id:
            data['message_thread_id'] = topic_id
            
        try:
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                print("✅ Отчет отправлен в Telegram")
                return True
            else:
                print(f"❌ Ошибка отправки: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка отправки в Telegram: {e}")
            return False
            
    def generate_daily_report(self):
        """Генерирует ежедневный отчет"""
        # Обновляем статистику
        self.monitor.parse_current_logs(24)
        self.monitor.update_daily_stats()
        
        # Получаем отчет
        report = self.monitor.generate_report(7)
        
        # Формируем сообщение
        instance_name = os.path.basename(self.instance_path)
        
        message = f"📊 <b>Ежедневный отчет RSS</b>\n"
        message += f"🏷️ Экземпляр: <code>{instance_name}</code>\n"
        message += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        
        # Общая статистика
        summary = report['summary']
        message += f"📡 Всего источников: <b>{summary['total_sources']}</b>\n"
        message += f"🟢 Отличных: <b>{summary['excellent_sources']}</b>\n"
        message += f"🔴 Проблемных: <b>{summary['problematic_sources']}</b>\n"
        message += f"📈 Средняя надежность: <b>{summary['avg_reliability']}%</b>\n\n"
        
        # Проблемные источники
        problematic = [(url, data) for url, data in report['sources'].items() 
                      if data['category'] in ['problematic', 'critical']]
        
        if problematic:
            problematic.sort(key=lambda x: x[1]['reliability_score'])
            message += f"⚠️ <b>Требуют внимания ({len(problematic)}):</b>\n"
            
            for url, data in problematic[:5]:  # Топ-5 проблемных
                domain = data['domain']
                reliability = data['reliability_score']
                status_emoji = "🔴" if data['category'] == 'critical' else "🟠"
                
                message += f"{status_emoji} <code>{domain}</code>\n"
                message += f"   └ Надежность: <b>{reliability}%</b>\n"
                
                # Добавляем главную рекомендацию
                if data['recommendations']:
                    rec = data['recommendations'][0]
                    message += f"   └ {rec}\n"
                    
                message += "\n"
                
            if len(problematic) > 5:
                message += f"   ... и еще {len(problematic) - 5} источников\n\n"
        else:
            message += "✅ <b>Все источники работают стабильно!</b>\n\n"
            
        # Статистика за последний час
        message += self.get_recent_activity()
        
        return message
        
    def get_recent_activity(self):
        """Получает статистику за последний час"""
        log_file = os.path.join(self.instance_path, 'monitor.log')
        
        if not os.path.exists(log_file):
            return ""
            
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Анализируем последние 100 строк
            recent_lines = lines[-100:]
            current_hour = datetime.now().strftime('%H')
            
            success_count = 0
            error_count = 0
            articles_count = 0
            
            for line in recent_lines:
                if current_hour in line:
                    if '✅' in line and 'новых статей' in line:
                        success_count += 1
                        # Извлекаем количество статей
                        import re
                        match = re.search(r'(\d+) новых статей', line)
                        if match:
                            articles_count += int(match.group(1))
                    elif '❌' in line or '⚠️' in line:
                        error_count += 1
                        
            activity = f"📊 <b>За последний час:</b>\n"
            activity += f"✅ Успешных запросов: <b>{success_count}</b>\n"
            activity += f"❌ Ошибок: <b>{error_count}</b>\n"
            activity += f"📰 Найдено статей: <b>{articles_count}</b>\n"
            
            # Оценка состояния
            if error_count == 0:
                activity += "🟢 Статус: <b>Отлично</b>"
            elif error_count <= success_count:
                activity += "🟡 Статус: <b>Норма</b>"
            else:
                activity += "🔴 Статус: <b>Требует внимания</b>"
                
            return activity
            
        except Exception as e:
            return f"⚠️ Ошибка анализа активности: {e}"
            
    def generate_weekly_report(self):
        """Генерирует еженедельный подробный отчет"""
        # Обновляем статистику
        self.monitor.parse_current_logs(168)  # 7 дней
        self.monitor.update_daily_stats()
        
        # Получаем отчет за 14 дней
        report = self.monitor.generate_report(14)
        
        instance_name = os.path.basename(self.instance_path)
        
        message = f"📊 <b>Еженедельный отчет RSS</b>\n"
        message += f"🏷️ Экземпляр: <code>{instance_name}</code>\n"
        message += f"📅 За период: {report['period']['start_date']} - {report['period']['end_date']}\n\n"
        
        # Подробная статистика
        summary = report['summary']
        message += f"📊 <b>Общая статистика:</b>\n"
        message += f"📡 Источников: {summary['total_sources']}\n"
        message += f"🟢 Отличных: {summary['excellent_sources']}\n"
        message += f"🟡 Хороших: {summary['total_sources'] - summary['excellent_sources'] - summary['problematic_sources']}\n"
        message += f"🔴 Проблемных: {summary['problematic_sources']}\n"
        message += f"📈 Средняя надежность: {summary['avg_reliability']}%\n\n"
        
        # Топ источники по статьям
        top_sources = sorted(
            [(url, data) for url, data in report['sources'].items() if data['articles_found'] > 0],
            key=lambda x: x[1]['articles_found'],
            reverse=True
        )[:5]
        
        if top_sources:
            message += f"🏆 <b>Топ-5 по статьям:</b>\n"
            for url, data in top_sources:
                domain = data['domain']
                articles = data['articles_found']
                reliability = data['reliability_score']
                message += f"📰 <code>{domain}</code>: {articles} статей ({reliability}%)\n"
            message += "\n"
            
        # Критические проблемы
        critical = [(url, data) for url, data in report['sources'].items() 
                   if data['category'] == 'critical']
        
        if critical:
            message += f"🚨 <b>Критические проблемы ({len(critical)}):</b>\n"
            for url, data in critical:
                domain = data['domain']
                reliability = data['reliability_score']
                message += f"🔴 <code>{domain}</code> ({reliability}%)\n"
                
                # Основные ошибки
                if data['main_errors']:
                    errors = ', '.join(data['main_errors'][:2])
                    message += f"   └ Ошибки: {errors}\n"
                    
            message += "\n"
            
        message += f"📄 Подробный отчет сохранен в файл\n"
        message += f"🔍 Для анализа используйте команды мониторинга"
        
        return message
        
    def send_daily_report(self, topic_id=None):
        """Отправляет ежедневный отчет"""
        print("📊 Генерация ежедневного отчета...")
        message = self.generate_daily_report()
        return self.send_telegram_message(message, topic_id)
        
    def send_weekly_report(self, topic_id=None):
        """Отправляет еженедельный отчет"""
        print("📊 Генерация еженедельного отчета...")
        message = self.generate_weekly_report()
        return self.send_telegram_message(message, topic_id)
        
    def send_alert_if_critical(self, topic_id=None):
        """Отправляет уведомление если есть критические проблемы"""
        # Быстрый анализ текущего состояния
        self.monitor.parse_current_logs(2)  # За последние 2 часа
        report = self.monitor.generate_report(1)  # За сегодня
        
        # Ищем критические проблемы
        critical_sources = [data for data in report['sources'].values() 
                          if data['category'] == 'critical' and data['is_active']]
        
        if len(critical_sources) >= 3:  # Если 3+ источников в критическом состоянии
            instance_name = os.path.basename(self.instance_path)
            
            message = f"🚨 <b>КРИТИЧЕСКОЕ УВЕДОМЛЕНИЕ</b>\n"
            message += f"🏷️ Экземпляр: <code>{instance_name}</code>\n\n"
            message += f"❌ <b>{len(critical_sources)} источников не работают!</b>\n\n"
            
            for data in critical_sources[:5]:
                domain = data['domain']
                reliability = data['reliability_score']
                message += f"🔴 <code>{domain}</code> ({reliability}%)\n"
                
            message += f"\n⚠️ Требуется срочное вмешательство!"
            
            return self.send_telegram_message(message, topic_id)
            
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Telegram отчеты о здоровье RSS')
    parser.add_argument('--path', default='.', help='Путь к экземпляру')
    parser.add_argument('--daily', action='store_true', help='Ежедневный отчет')
    parser.add_argument('--weekly', action='store_true', help='Еженедельный отчет')
    parser.add_argument('--alert', action='store_true', help='Проверка критических проблем')
    parser.add_argument('--topic', type=int, help='ID топика для отправки')
    
    args = parser.parse_args()
    
    reporter = TelegramHealthReporter(args.path)
    
    if args.daily:
        reporter.send_daily_report(args.topic)
    elif args.weekly:
        reporter.send_weekly_report(args.topic)
    elif args.alert:
        reporter.send_alert_if_critical(args.topic)
    else:
        print("Укажите тип отчета: --daily, --weekly или --alert")

if __name__ == "__main__":
    main()
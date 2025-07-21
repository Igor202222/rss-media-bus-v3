#!/usr/bin/env python3
"""
RSS Media Bus - Независимый RSS мониторинг v3.0
Мониторинг RSS источников с debug логированием
"""

import asyncio
import yaml
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Импорты наших модулей
from core.source_manager import AsyncRSSParser
from outputs.debug_chat_logger import log_system, log_rss, log_error

class RSSMonitor:
    def __init__(self):
        self.sources = {}
        self.active_sources = []
        self.rss_parser = None
        self.running = False
    
    def extract_domain_from_url(self, url):
        """Извлекает основной домен из URL для использования как feed_id"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Убираем www. префикс
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Специальная обработка для известных поддоменов
            domain_mappings = {
                'static.feed.rbc.ru': 'rbc.ru',
                'feeds.bbci.co.uk': 'bbc.co.uk',
                'feeds.reuters.com': 'reuters.com'
            }
            
            if domain in domain_mappings:
                return domain_mappings[domain]
            
            # Для остальных извлекаем основной домен (последние 2 части)
            parts = domain.split('.')
            if len(parts) >= 2:
                # Для доменов вида news.example.com → example.com
                # Для доменов вида example.com → example.com
                return '.'.join(parts[-2:])
            
            return domain
        except Exception as e:
            print(f"⚠️ Ошибка извлечения домена из {url}: {e}")
            return url  # Возвращаем исходный URL как fallback
        
    async def load_sources(self):
        """Загрузка источников из config/sources.yaml"""
        try:
            sources_file = Path("config/sources.yaml")
            
            if not sources_file.exists():
                raise FileNotFoundError("Файл config/sources.yaml не найден")
            
            with open(sources_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            self.sources = data.get('sources', {})
            
            # Фильтруем только активные источники
            self.active_sources = []
            for source_id, source_data in self.sources.items():
                if source_data.get('active', False):
                    self.active_sources.append({
                        'id': source_id,
                        'name': source_data.get('name', source_id),
                        'url': source_data.get('url'),
                        'group': source_data.get('group', 'general')
                    })
            
            # Логи только в консоль, не в Telegram
            print(f"✅ RSS источники загружены: {len(self.sources)} всего, {len(self.active_sources)} активных")
            
            # Выводим список активных источников
            for source in self.active_sources:
                print(f"📡 {source['name']} ({source['group']}) - {source['url']}")
            
            return True
            
        except Exception as e:
            await log_error("Ошибка загрузки источников", str(e))
            print(f"❌ Ошибка загрузки источников: {e}")
            return False
    
    async def initialize_parser(self):
        """Инициализация RSS парсера с реальным Telegram sender"""
        try:
            # Импортируем реальный DatabaseManager
            from core.database import DatabaseManager
            from outputs.telegram_sender import TelegramSender
            import json
            
            # Создаем реальный DB manager с SQLite
            db_manager = DatabaseManager()
            print("✅ Реальная SQLite база данных инициализирована")
            
            # Загружаем конфигурацию пользователей
            try:
                with open('config/users.yaml', 'r', encoding='utf-8') as f:
                    users_config = yaml.safe_load(f)
                
                # Ищем активного пользователя с Telegram ботом
                telegram_sender = None
                topics_mapping = {}
                
                # Проверяем структуру файла (users в корне или в секции 'users')
                users_data = users_config.get('users', users_config)
                for user_id, user_data in users_data.items():
                    if not user_data.get('active'):
                        continue
                        
                    telegram_config = user_data.get('telegram', {})
                    if telegram_config.get('enabled') and telegram_config.get('bot_token'):
                        bot_token = telegram_config['bot_token']
                        chat_id = telegram_config['chat_id']
                        
                        # Создаем реальный Telegram sender
                        telegram_sender = TelegramSender(bot_token, chat_id)
                        print(f"✅ TelegramSender создан для пользователя: {user_data.get('name', user_id)}")
                        
                        # Загружаем mapping топиков
                        try:
                            with open('config/topics_mapping.json', 'r', encoding='utf-8') as f:
                                topics_mapping = json.load(f)
                            print(f"✅ Загружен mapping {len(topics_mapping)} топиков")
                        except Exception as e:
                            print(f"⚠️ Ошибка загрузки topics_mapping.json: {e}")
                        
                        break
                
                if not telegram_sender:
                    print("⚠️ Не найден активный пользователь с Telegram ботом, используем mock sender")
                    class MockTelegramSender:
                        def send_article(self, title, description, link, source, keywords=None, categories=None, topic_id=None):
                            print(f"📱 [MOCK] Отправка: {title[:40]}... от {source}")
                            return True
                    telegram_sender = MockTelegramSender()
                    
            except Exception as e:
                print(f"⚠️ Ошибка загрузки конфигурации пользователей: {e}")
                print("⚠️ Используем mock sender")
                class MockTelegramSender:
                    def send_article(self, title, description, link, source, keywords=None, categories=None, topic_id=None):
                        print(f"📱 [MOCK] Отправка: {title[:40]}... от {source}")
                        return True
                telegram_sender = MockTelegramSender()
                topics_mapping = {}
            
            # Сохраняем mapping топиков
            self.topics_mapping = topics_mapping
            
            # Создаем RSS парсер с реальным sender
            self.rss_parser = AsyncRSSParser(
                db_manager=db_manager,
                telegram_sender=telegram_sender,
                keywords=["новости", "важно"],  # Базовые ключевые слова
                config=None
            )
            
            print("✅ RSS парсер инициализирован с реальным Telegram")
            return True
            
        except Exception as e:
            await log_error("Ошибка инициализации парсера", str(e))
            return False
    
    async def monitor_cycle(self):
        """Один цикл мониторинга всех источников"""
        if not self.active_sources:
            await log_rss("Нет активных источников для мониторинга")
            return
        
        if not self.rss_parser:
            await log_error("RSS парсер не инициализирован")
            return
        
        cycle_start = datetime.now()
        
        # Статистика цикла
        stats = {
            'available': [],      # Доступные источники с кол-вом статей
            'unavailable': [],    # Недоступные источники с ошибками
            'total_articles': 0,  # Общее количество новых статей
            'errors': []          # Список ошибок
        }
        
        print(f"🔄 Обработка {len(self.active_sources)} источников...")
        
        for source in self.active_sources:
            try:
                print(f"📡 Проверка: {source['name']}")
                
                # Парсим RSS источник (возвращает количество статей)
                # Автоматически извлекаем домен из URL как feed_id
                domain_id = self.extract_domain_from_url(source['url'])
                
                # Определяем topic_id для этого источника
                topic_id = None
                if hasattr(self, 'topics_mapping') and self.topics_mapping:
                    # Ищем по source_id
                    if source['id'] in self.topics_mapping:
                        topic_id = self.topics_mapping[source['id']].get('topic_id')
                        print(f"📱 Топик для {source['name']}: {topic_id}")
                    else:
                        print(f"⚠️ Топик для {source['id']} не найден")
                
                # Передаем topic_id в RSS парсер (если поддерживается)
                try:
                    if topic_id:
                        # Устанавливаем topic_id в Telegram sender перед парсингом
                        if hasattr(self.rss_parser.telegram, 'topic_id'):
                            self.rss_parser.telegram.topic_id = topic_id
                    
                    articles_count = await self.rss_parser.parse_all_feeds_async([(domain_id, source['url'])])
                except AttributeError:
                    # Fallback если метод не поддерживает topic_id
                    articles_count = await self.rss_parser.parse_all_feeds_async([(domain_id, source['url'])])
                
                # Проверяем что получили число статей
                if isinstance(articles_count, int) and articles_count >= 0:
                    stats['available'].append({
                        'name': source['name'],
                        'articles': articles_count
                    })
                    stats['total_articles'] += articles_count
                    
                    if articles_count > 0:
                        print(f"✅ {source['name']}: {articles_count} новых статей")
                    else:
                        print(f"📡 {source['name']}: новых статей нет")
                else:
                    # Если вернулось что-то неожиданное
                    stats['unavailable'].append({
                        'name': source['name'],
                        'error': f"Неожиданный ответ парсера: {type(articles_count)}"
                    })
                    print(f"❌ {source['name']}: неожиданный ответ парсера")
                
                # Небольшая пауза между источниками
                await asyncio.sleep(2)
                
            except Exception as e:
                error_msg = str(e)[:100] + "..." if len(str(e)) > 100 else str(e)
                stats['unavailable'].append({
                    'name': source['name'],
                    'error': error_msg
                })
                stats['errors'].append(f"{source['name']}: {error_msg}")
                print(f"❌ {source['name']}: {error_msg}")
        
        cycle_duration = (datetime.now() - cycle_start).total_seconds()
        
        print(f"📊 Статистика цикла:")
        print(f"  • Доступных источников: {len(stats['available'])}")
        print(f"  • Недоступных источников: {len(stats['unavailable'])}")  
        print(f"  • Всего статей: {stats['total_articles']}")
        print(f"  • Время: {cycle_duration:.1f}с")
        
        # Формируем сводный отчет
        print("📤 Отправляю сводный отчет в RSS топик...")
        await self.send_cycle_summary(stats, cycle_duration)
    
    async def send_cycle_summary(self, stats, duration):
        """Отправка сводного отчета о цикле мониторинга"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Заголовок отчета
        report = f"📊 RSS Мониторинг - Отчет [{timestamp}]\n\n"
        
        # Статистика
        total_sources = len(stats['available']) + len(stats['unavailable'])
        available_count = len(stats['available'])
        unavailable_count = len(stats['unavailable'])
        
        report += f"📈 Статистика:\n"
        report += f"• Всего источников: {total_sources}\n"
        report += f"• Доступны: {available_count}\n"
        report += f"• Недоступны: {unavailable_count}\n"
        report += f"• Новых статей: {stats['total_articles']}\n"
        report += f"• Время цикла: {duration:.1f}с\n\n"
        
        # Доступные источники
        if stats['available']:
            report += f"✅ Доступные источники:\n"
            for source in stats['available']:
                if source['articles'] > 0:
                    report += f"• {source['name']}: {source['articles']} новых\n"
                else:
                    report += f"• {source['name']}: без новых\n"
            report += "\n"
        
        # Недоступные источники
        if stats['unavailable']:
            report += f"❌ Недоступные источники:\n"
            for source in stats['unavailable']:
                report += f"• {source['name']}: {source['error']}\n"
            report += "\n"
        
        # Отправляем сводный отчет
        await log_rss("Завершен цикл RSS мониторинга", report.strip())
    
    async def start_monitoring(self, interval_minutes=15):
        """Запуск непрерывного мониторинга"""
        self.running = True
        
        # Логи только в консоль
        print(f"✅ RSS мониторинг запущен")
        
        print(f"🚀 RSS мониторинг запущен")
        print(f"⏰ Интервал: {interval_minutes} минут")
        print(f"📡 Активных источников: {len(self.active_sources)}")
        print(f"🔄 Для остановки: Ctrl+C")
        
        try:
            while self.running:
                print(f"\n🔄 Начинаю цикл мониторинга - {datetime.now().strftime('%H:%M:%S')}")
                
                await self.monitor_cycle()
                
                # Ждем до следующего цикла
                sleep_seconds = interval_minutes * 60
                print(f"😴 Ожидание {interval_minutes} минут до следующего цикла...")
                
                for i in range(sleep_seconds):
                    if not self.running:
                        break
                    await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n🛑 Получен сигнал остановки")
            await self.stop_monitoring()
    
    async def stop_monitoring(self):
        """Остановка мониторинга"""
        self.running = False
        print(f"✅ RSS мониторинг остановлен")

async def main():
    """Главная функция"""
    print("🔧 RSS Media Bus - Мониторинг v3.0")
    print("=" * 50)
    
    monitor = RSSMonitor()
    
    # Загружаем источники
    if not await monitor.load_sources():
        print("❌ Не удалось загрузить источники")
        return
    
    # Инициализируем парсер
    if not await monitor.initialize_parser():
        print("❌ Не удалось инициализировать парсер")
        return
    
    # Запускаем мониторинг
    try:
        await monitor.start_monitoring(interval_minutes=5)  # Тест каждые 5 минут
    except KeyboardInterrupt:
        print("\n🛑 Мониторинг прерван пользователем")
    
    print("👋 Завершение работы")

if __name__ == "__main__":
    asyncio.run(main()) 
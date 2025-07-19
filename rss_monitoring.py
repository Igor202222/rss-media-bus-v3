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

# Импорты наших модулей
from core.source_manager import AsyncRSSParser
from outputs.debug_chat_logger import log_system, log_rss, log_error

class RSSMonitor:
    def __init__(self):
        self.sources = {}
        self.active_sources = []
        self.rss_parser = None
        self.running = False
        
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
        """Инициализация RSS парсера"""
        try:
            # Создаем простой mock DB manager
            class MockDBManager:
                def __init__(self):
                    self.articles = []
                    self.feeds_info = {}
                
                def is_article_new(self, url):
                    return url not in [a.get('url') for a in self.articles]
                
                def article_exists(self, link):
                    """Проверка существования статьи по ссылке (обратная логика к is_article_new)"""
                    if not link:
                        return False
                    return link in [a.get('link') for a in self.articles]
                
                def add_article(self, feed_id, title, link, description, content, author, published_date):
                    """Добавление статьи в mock базу"""
                    if self.article_exists(link):
                        return None  # Статья уже существует
                    
                    article_id = len(self.articles) + 1
                    article_data = {
                        'id': article_id,
                        'feed_id': feed_id,
                        'title': title,
                        'link': link,
                        'description': description,
                        'content': content,
                        'author': author,
                        'published_date': published_date
                    }
                    self.articles.append(article_data)
                    print(f"💾 Сохранена статья: {title[:50]}...")
                    return article_id
                
                def save_article(self, article_data):
                    self.articles.append(article_data)
                    print(f"💾 Сохранена статья: {article_data.get('title', 'Без заголовка')[:50]}...")
                
                def update_feed_info(self, feed_url=None, status=None, last_check=None, articles_count=0, error_msg=None, **kwargs):
                    """Обновление информации о RSS источнике - принимаем любые аргументы"""
                    if feed_url:
                        self.feeds_info[feed_url] = {
                            'status': status,
                            'last_check': last_check,
                            'articles_count': articles_count,
                            'error_msg': error_msg,
                            **kwargs
                        }
            
            # Создаем mock Telegram sender
            class MockTelegramSender:
                def send_article(self, title, description, link, source, keywords=None, categories=None, topic_id=None):
                    print(f"📱 [MOCK] Отправка: {title[:40]}... от {source}")
                    return True
            
            db_manager = MockDBManager()
            telegram_sender = MockTelegramSender()
            
            # Создаем RSS парсер
            self.rss_parser = AsyncRSSParser(
                db_manager=db_manager,
                telegram_sender=telegram_sender,
                keywords=["новости", "важно"],  # Базовые ключевые слова
                config=None
            )
            
            print("✅ RSS парсер инициализирован")
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
                articles_count = await self.rss_parser.parse_all_feeds_async([('source', source['url'])])
                
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
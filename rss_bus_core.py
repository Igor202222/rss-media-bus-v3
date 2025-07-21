#!/usr/bin/env python3
"""
RSS Media Bus Core v3.0 - Независимый парсинг RSS
Только парсинг источников и сохранение в БД. Никаких пользователей.
"""

import asyncio
import yaml
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Импорты наших модулей
from core.source_manager import AsyncRSSParser
from core.database import DatabaseManager

class RSSBusCore:
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
                return '.'.join(parts[-2:])
            
            return domain
        except Exception as e:
            print(f"⚠️ Ошибка извлечения домена из {url}: {e}")
            return url
        
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
            
            print(f"✅ RSS источники загружены: {len(self.sources)} всего, {len(self.active_sources)} активных")
            
            # Выводим краткий список активных источников
            for source in self.active_sources[:5]:
                print(f"📡 {source['name']}")
            if len(self.active_sources) > 5:
                print(f"📡 ... и еще {len(self.active_sources) - 5} источников")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка загрузки источников: {e}")
            return False
    
    async def initialize_parser(self):
        """Инициализация RSS парсера БЕЗ Telegram sender"""
        try:
            # Создаем реальный DB manager с SQLite
            db_manager = DatabaseManager()
            print("✅ База данных инициализирована")
            
            # Создаем RSS парсер БЕЗ Telegram sender
            self.rss_parser = AsyncRSSParser(
                db_manager=db_manager,
                telegram_sender=None,  # НЕТ Telegram логики!
                keywords=["новости", "важно"],  # Базовые ключевые слова для совместимости
                config=None
            )
            
            print("✅ RSS парсер инициализирован (только БД)")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка инициализации парсера: {e}")
            return False
    
    async def parse_cycle(self):
        """Один цикл парсинга всех источников (только сохранение в БД)"""
        if not self.active_sources:
            print("⚠️ Нет активных источников для парсинга")
            return
        
        if not self.rss_parser:
            print("❌ RSS парсер не инициализирован")
            return
        
        cycle_start = datetime.now()
        
        # Статистика цикла
        stats = {
            'available': [],
            'unavailable': [],
            'total_articles': 0,
            'errors': []
        }
        
        print(f"🔄 Начинаю парсинг {len(self.active_sources)} источников...")
        
        for source in self.active_sources:
            try:
                print(f"📡 {source['name'][:30]}...", end=" ")
                
                # Парсим RSS источник (только сохранение в БД)
                domain_id = self.extract_domain_from_url(source['url'])
                articles_count = await self.rss_parser.parse_all_feeds_async([(domain_id, source['url'])])
                
                if isinstance(articles_count, int) and articles_count >= 0:
                    stats['available'].append({
                        'name': source['name'],
                        'articles': articles_count
                    })
                    stats['total_articles'] += articles_count
                    
                    if articles_count > 0:
                        print(f"✅ {articles_count} новых")
                    else:
                        print("📡 без новых")
                else:
                    stats['unavailable'].append({
                        'name': source['name'],
                        'error': f"Неожиданный ответ: {type(articles_count)}"
                    })
                    print("❌ ошибка")
                
                # Пауза между источниками
                await asyncio.sleep(1)
                
            except Exception as e:
                error_msg = str(e)[:50] + "..." if len(str(e)) > 50 else str(e)
                stats['unavailable'].append({
                    'name': source['name'],
                    'error': error_msg
                })
                stats['errors'].append(f"{source['name']}: {error_msg}")
                print(f"❌ {error_msg}")
        
        cycle_duration = (datetime.now() - cycle_start).total_seconds()
        
        print(f"\n📊 Цикл завершен за {cycle_duration:.1f}с:")
        print(f"  ✅ Успешно: {len(stats['available'])}")
        print(f"  ❌ Ошибки: {len(stats['unavailable'])}")  
        print(f"  📰 Новых статей: {stats['total_articles']}")
        
        if stats['errors']:
            print(f"  ⚠️ Проблемные источники: {len(stats['errors'])}")
    
    async def start_parsing(self, interval_minutes=5):
        """Запуск непрерывного парсинга RSS (только БД)"""
        self.running = True
        
        print(f"🚀 RSS Bus Core запущен")
        print(f"⏰ Интервал: {interval_minutes} минут")
        print(f"📡 Активных источников: {len(self.active_sources)}")
        print(f"💾 Режим: только сохранение в БД")
        print(f"🔄 Для остановки: Ctrl+C")
        print("=" * 50)
        
        try:
            while self.running:
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"\n🔄 [{timestamp}] Начинаю цикл парсинга RSS")
                
                await self.parse_cycle()
                
                # Ждем до следующего цикла
                sleep_seconds = interval_minutes * 60
                print(f"😴 Ожидание {interval_minutes} минут...")
                
                for i in range(sleep_seconds):
                    if not self.running:
                        break
                    await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n🛑 Получен сигнал остановки")
            await self.stop_parsing()
    
    async def stop_parsing(self):
        """Остановка парсинга"""
        self.running = False
        print(f"✅ RSS Bus Core остановлен")

async def main():
    """Главная функция RSS Bus Core"""
    print("🚌 RSS Media Bus Core v3.0 - Независимый парсинг")
    print("=" * 60)
    
    bus_core = RSSBusCore()
    
    # Загружаем источники
    if not await bus_core.load_sources():
        print("❌ Не удалось загрузить источники")
        return
    
    # Инициализируем парсер
    if not await bus_core.initialize_parser():
        print("❌ Не удалось инициализировать парсер")
        return
    
    # Запускаем парсинг
    try:
        await bus_core.start_parsing(interval_minutes=5)
    except KeyboardInterrupt:
        print("\n🛑 Парсинг прерван пользователем")
    
    print("👋 RSS Bus Core завершен")

if __name__ == "__main__":
    asyncio.run(main()) 
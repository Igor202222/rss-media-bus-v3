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
from core.hot_reload import HotReloadManager

class RSSBusCore:
    def __init__(self):
        self.sources = {}
        self.active_sources = []
        self.rss_parser = None
        self.running = False
        
        # Hot Reload менеджер
        self.hot_reload = HotReloadManager("RSS Bus Core")
        self.hot_reload.register_callback('sources', self._on_sources_reload)
        self.hot_reload.setup_signal_handlers()
        
        print("🔄 Hot Reload поддержка включена (USR1 для sources.yaml)")
    
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
        
        # Готовим все источники для РЕАЛЬНО асинхронной обработки
        feeds_batch = []
        for source in self.active_sources:
            domain_id = self.extract_domain_from_url(source['url'])
            feeds_batch.append((domain_id, source['url'], source['name']))
        
        print(f"🚀 Запускаю параллельную обработку {len(feeds_batch)} источников...")
        
        # Парсим ВСЕ источники параллельно
        total_articles = await self.rss_parser.parse_all_feeds_async(feeds_batch)
        
        # Собираем статистику из парсера
        stats['total_articles'] = total_articles
        print(f"📊 Параллельная обработка завершена: {total_articles} новых статей")
        
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
    
    async def _on_sources_reload(self, new_sources):
        """Callback для перезагрузки источников"""
        print("🔄 Перезагружаю источники RSS Bus Core...")
        
        # Обновляем источники
        self.sources = new_sources
        
        # Фильтруем активные источники
        self.active_sources = []
        for source_id, source_data in self.sources.items():
            if source_data.get('active', False):
                self.active_sources.append({
                    'id': source_id,
                    'name': source_data.get('name', source_id),
                    'url': source_data.get('url'),
                    'group': source_data.get('group', 'general')
                })
        
        print(f"✅ Источники перезагружены: {len(self.sources)} всего, {len(self.active_sources)} активных")
        
        # Выводим обновленный список
        for source in self.active_sources[:5]:
            print(f"📡 {source['name']}")
        if len(self.active_sources) > 5:
            print(f"📡 ... и еще {len(self.active_sources) - 5} источников")
    
    async def add_source_dynamic(self, source_id, url, name=None, group="user_added"):
        """Динамическое добавление источника без перезапуска"""
        try:
            # Проверяем что источник не существует
            if source_id in self.sources:
                print(f"⚠️ Источник {source_id} уже существует")
                return False
            
            # Добавляем в память
            self.sources[source_id] = {
                'url': url,
                'name': name or source_id,
                'group': group,
                'active': True,
                'added_dynamically': True
            }
            
            # Добавляем в активные источники
            self.active_sources.append({
                'id': source_id,
                'name': name or source_id,
                'url': url,
                'group': group
            })
            
            # Сохраняем в файл для постоянства
            await self._save_sources_to_file()
            
            print(f"✅ Динамически добавлен источник: {name or source_id}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка добавления источника {source_id}: {e}")
            return False
    
    async def _save_sources_to_file(self):
        """Сохранение источников в YAML файл"""
        try:
            import yaml
            from pathlib import Path
            
            sources_file = Path("config/sources.yaml")
            
            # Читаем текущий файл для сохранения структуры
            with open(sources_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Обновляем секцию sources
            data['sources'] = self.sources
            
            # Записываем обратно
            with open(sources_file, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, ensure_ascii=False, default_flow_style=False, indent=2)
                
            print("💾 Конфигурация источников сохранена")
            
        except Exception as e:
            print(f"⚠️ Не удалось сохранить конфигурацию: {e}")
    
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
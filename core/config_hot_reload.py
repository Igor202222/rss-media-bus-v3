#!/usr/bin/env python3
"""
Config Hot Reload для RSS Media Monitoring System
Автоматическая перезагрузка конфигурации при изменении файлов
"""

import os
import asyncio
import time
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigReloadHandler(FileSystemEventHandler):
    """Обработчик изменений конфигурационных файлов"""
    
    def __init__(self, monitor_instance, event_loop=None):
        self.monitor = monitor_instance
        self.loop = event_loop
        self.last_reload = time.time()
        self.reload_cooldown = 2  # Защита от множественных перезагрузок
        
    def on_modified(self, event):
        """Вызывается при изменении файла"""
        if event.is_directory:
            return
            
        # Проверяем только нужные файлы
        filename = os.path.basename(event.src_path)
        if filename in ['config.py', 'feeds.txt', 'keywords.txt']:
            
            # Защита от множественных вызовов
            current_time = time.time()
            if current_time - self.last_reload < self.reload_cooldown:
                return
                
            self.last_reload = current_time
            
            print(f"\n🔄 Обнаружено изменение: {filename}")
            print(f"⏰ {datetime.now().strftime('%H:%M:%S')} - Начинаю перезагрузку конфигурации...")
            
            # Запускаем асинхронную перезагрузку thread-safe
            if self.loop:
                self.loop.call_soon_threadsafe(
                    lambda: asyncio.create_task(self.reload_config(filename))
                )
            else:
                print(f"⚠️ Event loop не доступен для {filename}")
            
    async def reload_config(self, changed_file):
        """Асинхронная перезагрузка конфигурации"""
        try:
            if changed_file == 'config.py':
                await self._reload_main_config()
            elif changed_file == 'feeds.txt':
                await self._reload_feeds()
            elif changed_file == 'keywords.txt':
                await self._reload_keywords()
                
            print(f"✅ Конфигурация перезагружена: {changed_file}")
            
        except Exception as e:
            print(f"❌ Ошибка перезагрузки {changed_file}: {e}")
    
    async def _reload_main_config(self):
        """Перезагрузка основной конфигурации"""
        # Перезагружаем модуль config
        import importlib
        import config
        importlib.reload(config)
        
        # Обновляем настройки в мониторе
        if hasattr(self.monitor, 'telegram') and self.monitor.telegram:
            # Обновляем настройки Telegram
            topic_id = getattr(config, 'TELEGRAM_TOPIC_ID', None)
            if topic_id != self.monitor.telegram.topic_id:
                self.monitor.telegram.topic_id = topic_id
                print(f"📱 Telegram топик обновлен: {topic_id}")
        
        # Проверяем SOURCE_MODES
        if hasattr(config, 'SOURCE_MODES'):
            self.monitor.parser.source_modes = config.SOURCE_MODES
            print(f"🎯 SOURCE_MODES обновлены: {len(config.SOURCE_MODES)} правил")
    
    async def _reload_feeds(self):
        """Перезагрузка списка RSS источников"""
        from config import load_feeds
        
        old_feeds = len(self.monitor.feeds)
        self.monitor.feeds = load_feeds()
        new_feeds = len(self.monitor.feeds)
        
        # Обновляем источники в базе данных
        await self.monitor._ensure_feeds_in_database()
        
        print(f"📡 RSS источники: {old_feeds} → {new_feeds}")
        
        # Обновляем парсер
        self.monitor.parser.feeds = self.monitor.feeds
    
    async def _reload_keywords(self):
        """Перезагрузка ключевых слов"""
        from config import load_keywords
        
        old_keywords = len(self.monitor.keywords)
        self.monitor.keywords = load_keywords()
        new_keywords = len(self.monitor.keywords)
        
        # Проверяем нужно ли изменить режим работы
        old_mode = self.monitor.forward_all_mode
        self.monitor.forward_all_mode = self.monitor._detect_working_mode()
        
        if old_mode != self.monitor.forward_all_mode:
            mode_name = "ВСЕ НОВОСТИ" if self.monitor.forward_all_mode else "ФИЛЬТРАЦИЯ"
            print(f"🔧 Режим изменен на: {mode_name}")
        
        print(f"🔑 Ключевые слова: {old_keywords} → {new_keywords}")
        
        # Обновляем парсер
        self.monitor.parser.keywords = self.monitor.keywords
        self.monitor.parser.forward_all_mode = self.monitor.forward_all_mode


class HotReloadMixin:
    """Mixin для добавления горячей перезагрузки в UniversalMediaMonitor"""
    
    def start_file_watcher(self):
        """Запуск наблюдателя за файлами"""
        try:
            # Получаем текущий event loop и передаем в handler
            loop = asyncio.get_running_loop()
            self.config_handler = ConfigReloadHandler(self, loop)
            self.file_observer = Observer()
            
            # Наблюдаем за текущей папкой
            watch_path = os.path.dirname(os.path.abspath(__file__))
            self.file_observer.schedule(
                self.config_handler, 
                watch_path, 
                recursive=False
            )
            
            self.file_observer.start()
            print(f"👁️ File Watcher запущен: {watch_path}")
            print(f"📋 Отслеживаемые файлы: config.py, feeds.txt, keywords.txt")
            
        except Exception as e:
            print(f"⚠️ Не удалось запустить File Watcher: {e}")
            print(f"💡 Установите: pip install watchdog")


# Пример интеграции в UniversalMediaMonitor
class UniversalMediaMonitorWithHotReload(HotReloadMixin):
    """Расширенная версия мониторинга с горячей перезагрузкой"""
    
    async def run(self):
        """Главный цикл с File Watcher"""
        if not await self.initialize():
            print(f"❌ Не удалось инициализировать систему")
            return 1
        
        # Запускаем File Watcher
        self.start_file_watcher()
        
        print(f"🎯 Универсальный мониторинг запущен с горячей перезагрузкой")
        print(f"⏰ Интервал проверки: {CHECK_INTERVAL_MINUTES} минут")
        print(f"🔧 Режим: {'🌐 ВСЕ НОВОСТИ' if self.forward_all_mode else '🔍 ФИЛЬТРАЦИЯ'}")
        print(f"🔄 Горячая перезагрузка: Включена")
        print(f"Для остановки нажмите Ctrl+C")
        
        try:
            # Стартовое сообщение в Telegram
            if self.telegram:
                await self._send_startup_message()
            
            # Главный цикл мониторинга
            while self.running:
                try:
                    new_articles = await self.monitoring_cycle()
                    
                    # Отправляем статус если нужно
                    if hasattr(config, 'SEND_STATUS_UPDATES') and config.SEND_STATUS_UPDATES:
                        await self._send_status_update(len(self.feeds), new_articles)
                    
                    # Ожидаем следующий цикл
                    await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)
                    
                except Exception as e:
                    print(f"❌ Ошибка в цикле мониторинга: {e}")
                    await asyncio.sleep(60)  # Ждем минуту при ошибке
                    
        except KeyboardInterrupt:
            print(f"\n🛑 Получен сигнал завершения")
        finally:
            self.stop_file_watcher()
            if self.telegram:
                topic_id = getattr(self.telegram, 'topic_id', None)
                self.telegram.send_message("👋 Универсальный мониторинг остановлен", topic_id=topic_id)
        
        return 0


# Пример использования
if __name__ == "__main__":
    # Проверяем установлен ли watchdog
    try:
        import watchdog
        print("✅ watchdog установлен")
    except ImportError:
        print("❌ Требуется установка: pip install watchdog")
        exit(1)
    
    # Тестируем File Watcher
    print("🧪 Тест File Watcher - измените config.py, feeds.txt или keywords.txt")
    
    class MockMonitor:
        def __init__(self):
            self.feeds = []
            self.keywords = []
            self.forward_all_mode = False
            self.telegram = None
            self.parser = None
    
    monitor = MockMonitor()
    handler = ConfigReloadHandler(monitor)
    
    observer = Observer()
    observer.schedule(handler, ".", recursive=False)
    observer.start()
    
    try:
        print("👁️ Наблюдение запущено. Нажмите Ctrl+C для остановки.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n👁️ File Watcher остановлен")
    
    observer.join()
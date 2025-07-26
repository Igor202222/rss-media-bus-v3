#!/usr/bin/env python3
"""
RSS Media Bus - User Notification Service v3.0
Читает новые статьи из БД и отправляет пользователям по их настройкам
"""

import asyncio
import sqlite3
import yaml
import signal
import json
import time
import pytz
from datetime import datetime, timedelta
from pathlib import Path

# Импорты наших модулей
from core.database import DatabaseManager
from outputs.telegram_sender import TelegramSender
from core.hot_reload import HotReloadManager
from processors.simple_keyword_filter import SimpleKeywordFilter


class UserNotificationService:
    def __init__(self):
        self.db = None
        self.users = {}
        self.running = False
        self.last_check_time = {}
        
        # Hot Reload менеджер
        self.hot_reload = HotReloadManager("User Notification Service")
        self.hot_reload.register_callback('users', self._on_users_reload)
        self.hot_reload.register_callback('topics', self._on_topics_reload)
        self.hot_reload.setup_signal_handlers()
        
        print("🔄 Hot Reload поддержка включена (USR2 для users.yaml)")
        import logging
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler("user_service_debug.log"), logging.StreamHandler()])
        self.logger = logging.getLogger(__name__)
        self.logger.info("User Notification Service initialized")
    
    async def load_users(self):
        """
        Загрузка активных пользователей и их telegram_configs из config/users.yaml
        """
        try:
            users_file = Path("config/users.yaml")
            if not users_file.exists():
                raise FileNotFoundError("Файл config/users.yaml не найден")
            with open(users_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            users_data = data.get('users', data)
            self.users = {}
            self.last_check_time = {}
            for user_id, user_data in users_data.items():
                if not user_data.get('active'):
                    continue
                telegram_configs = user_data.get('telegram_configs')
                if not telegram_configs:
                    # Для обратной совместимости — поддержка старого формата
                    telegram_configs = {}
                    telegram = user_data.get('telegram', {})
                    if telegram.get('enabled') and telegram.get('bot_token'):
                        telegram_configs['default'] = telegram
                for config_id, telegram_config in telegram_configs.items():
                    if not telegram_config.get('enabled') or not telegram_config.get('bot_token'):
                        continue
                    try:
                        telegram_sender = TelegramSender(
                            bot_token=telegram_config['bot_token'],
                            chat_id=telegram_config['chat_id']
                        )
                        # Получаем topics_mapping из самого конфига (приоритет) или глобального файла
                        topics_mapping = telegram_config.get('topics_mapping', {})
                        key = f"{user_id}::{config_id}"
                        # Используем processors из telegram_config, если есть, иначе из user_data
                        processors = telegram_config.get('processors', user_data.get('processors', []))
                        
                        # Поддержка фильтрации по ключевым словам
                        filter_config = telegram_config.get('filter_config')
                        keyword_filter = None
                        if filter_config:
                            try:
                                keyword_filter = SimpleKeywordFilter(filter_config)
                                print(f"   🔍 Простой фильтр создан: режим={filter_config.get('mode')}, keywords={len(filter_config.get('keywords', []))}")
                            except Exception as e:
                                print(f"   ⚠️ Ошибка создания фильтра: {e}")
                        
                        self.users[key] = {
                            'name': user_data.get('name', user_id),
                            'telegram_sender': telegram_sender,
                            'sources': telegram_config.get('sources', user_data.get('sources', [])),
                            'topics_mapping': topics_mapping,
                            'processors': processors,
                            'keyword_filter': keyword_filter,
                            'chat_id': telegram_config['chat_id']
                        }
                        # Устанавливаем время на текущий момент чтобы обрабатывать только новые статьи  
                        self.last_check_time[key] = datetime.now(pytz.timezone('Europe/Moscow'))
                        print(f"✅ Пользователь {user_id} / {config_id} настроен")
                        print(f"   📱 Chat ID: {telegram_config['chat_id']}")
                        print(f"   📡 Источников: {len(self.users[key]['sources'])}")
                        print(f"   🗂️ Топиков: {len(topics_mapping)}")
                    except Exception as e:
                        print(f"❌ Ошибка настройки Telegram для {user_id}/{config_id}: {e}")
            print(f"\n📊 Активных telegram-конфигов: {len(self.users)}")
            return len(self.users) > 0
        except Exception as e:
            print(f"❌ Ошибка загрузки пользователей: {e}")
            return False
    
    async def initialize_database(self):
        """Инициализация подключения к базе данных"""
        try:
            self.db = DatabaseManager()
            print("✅ Подключение к базе данных инициализировано")
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения к БД: {e}")
            return False
    
    def get_user_keywords(self, user_key):
        user_data = self.users.get(user_key, {})
        processors = user_data.get('processors', [])
        keywords = []
        for processor in processors:
            if processor.get('name') == 'keyword_filter':
                config = processor.get('config', {})
                keywords.extend(config.get('keywords', []))
        return keywords
    
    def should_send_article_to_user(self, article, user_key):
        user_data = self.users.get(user_key, {})
        
        # Проверка источника: если список источников задан, но идентификаторы не совпадают
        user_sources = user_data.get('sources', [])
        if user_sources:
            art_source = str(article['feed_id']).lower()
            if art_source not in user_sources:
                return False, []
        
        # ПРИОРИТЕТ 1: Фильтр для конкретного источника (новая система)
        source_filter = self.get_filter_for_source(user_key, article['feed_id'])
        if source_filter:
            try:
                should_send, filter_metadata = source_filter.filter_article(article)
                matched_keywords = filter_metadata.get('matched_keywords', [])
                if should_send:
                    self.logger.debug(f"🔍 Фильтр источника ПРОПУСТИЛ: {filter_metadata.get('filter_reason', 'unknown')}")
                    return True, matched_keywords
                else:
                    self.logger.debug(f"🚫 Фильтр источника ЗАБЛОКИРОВАЛ: {filter_metadata.get('filter_reason', 'unknown')}")
                    return False, []
            except Exception as e:
                self.logger.error(f"❌ Ошибка фильтрации источника: {e}")
                # При ошибке фильтра источника - проверяем общий фильтр
        
        # ПРИОРИТЕТ 2: Общий фильтр пользователя (обратная совместимость)
        keyword_filter = user_data.get('keyword_filter')
        if keyword_filter:
            try:
                should_send, filter_metadata = keyword_filter.filter_article(article)
                matched_keywords = filter_metadata.get('matched_keywords', [])
                if should_send:
                    self.logger.debug(f"🔍 Общий фильтр ПРОПУСТИЛ: {filter_metadata.get('filter_reason', 'unknown')}")
                    return True, matched_keywords
                else:
                    self.logger.debug(f"🚫 Общий фильтр ЗАБЛОКИРОВАЛ: {filter_metadata.get('filter_reason', 'unknown')}")
                    return False, []
            except Exception as e:
                self.logger.error(f"❌ Ошибка общей фильтрации: {e}")
                # При ошибке фильтра - пропускаем статью
                return True, []
        
        # СТАРАЯ ФИЛЬТРАЦИЯ: Поддержка legacy processors для совместимости
        processors = user_data.get('processors', [])
        for processor in processors:
            if processor.get('name') == 'keyword_filter':
                config = processor.get('config', {})
                keywords = config.get('keywords', [])
                mode = config.get('mode', 'include')
                min_matches = config.get('min_matches', 1)
                if keywords:
                    matched_keywords = self.check_keywords_in_article(article, keywords)
                    if mode == 'include':
                        if len(matched_keywords) >= min_matches:
                            return True, matched_keywords
                        else:
                            return False, []
                    elif mode == 'exclude':
                        if len(matched_keywords) >= min_matches:
                            return False, matched_keywords
        
        # Если фильтров нет - пропускаем статью
        return True, []
    
    def check_keywords_in_article(self, article, keywords):
        if not keywords:
            return []
        filter_config = {
            'mode': 'include',
            'keywords': keywords,
            'case_sensitive': False,
            'fields': ['title', 'description', 'content']
        }
        advanced_filter = AdvancedKeywordFilter(filter_config)
        should_send, metadata = advanced_filter.filter_article(article)
        return metadata.get('matched_keywords', []) if should_send else []
    
    def get_topic_id_for_source(self, user_key, source_id):
        user_data = self.users.get(user_key, {})
        topics_mapping = user_data.get('topics_mapping', {})
        
        # Поддержка разных форматов mapping
        if source_id in topics_mapping:
            topic = topics_mapping[source_id]
            if isinstance(topic, dict):
                return topic.get('topic_id')
            return topic
        
        # Fallback: ищем по частичному совпадению домена
        for mapped_source, topic_id in topics_mapping.items():
            if mapped_source in source_id or source_id in mapped_source:
                if isinstance(topic_id, dict):
                    return topic_id.get('topic_id')
                return topic_id
        
        return None
    
    def get_filter_for_source(self, user_key, source_id):
        """Получает filter_config для конкретного источника"""
        user_data = self.users.get(user_key, {})
        topics_mapping = user_data.get('topics_mapping', {})
        
        # Проверяем прямое совпадение
        if source_id in topics_mapping:
            topic = topics_mapping[source_id]
            if isinstance(topic, dict):
                filter_config = topic.get('filter_config')
                if filter_config:
                    return SimpleKeywordFilter(filter_config)
        
        # Fallback: ищем по частичному совпадению домена
        for mapped_source, topic_data in topics_mapping.items():
            if mapped_source in source_id or source_id in mapped_source:
                if isinstance(topic_data, dict):
                    filter_config = topic_data.get('filter_config')
                    if filter_config:
                        return SimpleKeywordFilter(filter_config)
        
        return None
    
    async def send_article_to_user(self, article, user_key, matched_keywords=None):
        user_data = self.users.get(user_key)
        if not user_data:
            return False
        telegram_sender = user_data['telegram_sender']
        topic_id = self.get_topic_id_for_source(user_key, article['feed_id'])
        
        # Проверяем есть ли настроенный топик для этого источника
        if topic_id is None:
            self.logger.debug(f"🚫 Пропускаю {article['feed_id']} для {user_key}: топик не настроен")
            return False  # Не отправляем если нет настроенного топика
        
        try:
            title = article.get('title', 'Без заголовка')
            description = article.get('description', '')
            link = article.get('link', '')
            categories = article.get('tags', []) if article.get('tags') else []
            success = telegram_sender.send_article(
                title=title,
                link=link,
                description=description,
                keywords=matched_keywords or [],
                categories=categories,
                source=article.get('feed_id', 'unknown'),
                topic_id=topic_id
            )
            if success:
                source_name = article.get('feed_id', 'unknown')
                topic_info = f" (топик {topic_id})" if topic_id else ""
                print(f"📤 {user_key}: {title[:40]}... → {source_name}{topic_info}")
                return True
            else:
                print(f"❌ Ошибка отправки {user_key}: {title[:40]}...")
                return False
        except Exception as e:
            print(f"❌ Ошибка отправки статьи пользователю {user_key}: {e}")
            return False
    
    async def check_articles_for_user(self, user_key):
        """Проверка новых статей для пользователя с настоящей асинхронностью"""
        try:
            user_data = self.users[user_key]
            last_check = self.last_check_time[user_key]
            
            self.logger.debug(f"Last check for {user_key}: {last_check}")
            
            # Конвертируем в UTC для запроса к БД
            utc_time = last_check.astimezone(pytz.UTC)
            self.logger.debug(f"Querying articles after {utc_time.strftime('%Y-%m-%d %H:%M:%S')} UTC (was {last_check.strftime('%Y-%m-%d %H:%M:%S')} Moscow)")
            
            # Получаем новые статьи, сортированные по времени публикации (ХРОНОЛОГИЧЕСКИЙ ПОРЯДОК!)
            query = """
                SELECT id, feed_id, title, link, description, tags, published_date, added_date
                FROM articles 
                WHERE added_date > ? 
                ORDER BY published_date ASC, added_date ASC
                LIMIT 500
            """
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, (utc_time.strftime('%Y-%m-%d %H:%M:%S'),))
            articles = cursor.fetchall()
            conn.close()
            
            self.logger.info(f"Found {len(articles)} potential new articles for {user_key}")
            
            if not articles:
                self.logger.info(f"Sent 0 articles for {user_key}")
                return 0
            
            # Фильтруем и подготавливаем статьи для отправки
            articles_to_send = []
            for article_row in articles:
                article = {
                    'id': article_row[0],
                    'feed_id': article_row[1],
                    'title': article_row[2],
                    'link': article_row[3],
                    'description': article_row[4],
                    'tags': json.loads(article_row[5]) if article_row[5] else [],
                    'published_date': article_row[6],
                    'added_date': article_row[7]
                }
                should_send, matched_keywords = self.should_send_article_to_user(article, user_key)
                if should_send:
                    articles_to_send.append((article, matched_keywords))
            
            # МАССОВАЯ АСИНХРОННАЯ ОТПРАВКА без блокировки
            if articles_to_send:
                sent_count = await self._send_articles_batch_async(articles_to_send, user_key)
            else:
                sent_count = 0
            
            # Обновляем время только ПОСЛЕ успешной отправки
            self.last_check_time[user_key] = datetime.now(pytz.timezone('Europe/Moscow'))
            self.logger.info(f"Sent {sent_count} articles for {user_key}")
            return sent_count
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки статей для {user_key}: {e}")
            return 0

    async def _send_articles_batch_async(self, articles_to_send, user_key):
        """Оптимальная отправка статей с максимальным использованием лимитов Telegram"""
        if not articles_to_send:
            return 0
            
        self.logger.info(f"📤 Начинаю отправку {len(articles_to_send)} статей (оптимально)")
        sent_count = 0
        
        # Создаем задачи для всех статей
        tasks = []
        for article, matched_keywords in articles_to_send:
            task = self.send_article_to_user(article, user_key, matched_keywords)
            tasks.append(task)
        
        # Отправляем с точным соблюдением лимита: 20 сообщений/минуту = 3 секунды на сообщение
        for i, task in enumerate(tasks):
            try:
                success = await task
                if success:
                    sent_count += 1
                    self.logger.info(f"✅ {i+1}/{len(tasks)}: статья отправлена")
                else:
                    self.logger.warning(f"❌ {i+1}/{len(tasks)}: ошибка отправки")
                
                # Точная задержка 3 секунды (кроме последнего сообщения)
                if i < len(tasks) - 1:
                    await asyncio.sleep(3.0)  # 20 сообщений/минуту
                    
            except Exception as e:
                self.logger.error(f"❌ {i+1}/{len(tasks)}: исключение {e}")

        total_time = len(articles_to_send) * 3
        self.logger.info(f"📊 Отправлено {sent_count}/{len(articles_to_send)} статей за ~{total_time//60}м {total_time%60}с")
        return sent_count
    
    async def notification_cycle(self):
        if not self.users:
            self.logger.warning("⚠️ Нет активных telegram-конфигов")
            return
        cycle_start = datetime.now()
        total_sent = 0
        
        # ПАРАЛЛЕЛЬНАЯ обработка всех пользователей одновременно
        tasks = []
        for user_key in self.users:
            task = self.check_articles_for_user(user_key)
            tasks.append(task)
        
        # Ждем завершения ВСЕХ пользователей параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, (user_key, result) in enumerate(zip(self.users.keys(), results)):
            try:
                if isinstance(result, Exception):
                    self.logger.error(f"❌ Ошибка для {user_key}: {result}")
                else:
                    sent_count = result
                    total_sent += sent_count
                    # Логируем только если есть новые статьи
                    if sent_count > 0:
                        user_name = self.users[user_key]['name']
                        self.logger.info(f"📬 {user_name}: отправлено {sent_count} статей")
            except Exception as e:
                self.logger.error(f"❌ Ошибка обработки результата для {user_key}: {e}")
        
        cycle_duration = (datetime.now() - cycle_start).total_seconds()
        if total_sent > 0:
            self.logger.info(f"🎯 Цикл завершен: {total_sent} статей за {cycle_duration:.1f}с")
        else:
            self.logger.debug(f"🔄 Цикл завершен: новых статей нет ({cycle_duration:.1f}с)")
    
    async def start_notifications(self, interval_minutes=1):  # Ускорено с 2 до 1 минуты
        """Запуск сервиса уведомлений с оптимальным интервалом"""
        self.running = True
        
        print(f"🔔 User Notification Service запущен")
        print(f"⏰ Интервал проверки: {interval_minutes} минут (ускоренный)")
        print(f"👥 Активных пользователей: {len(self.users)}")
        print(f"📱 Активных telegram-конфигов: {sum(len(user.get('telegram_configs', {})) for user in self.users.values() if isinstance(user, dict))}")
        print("=" * 60)
        
        try:
            while self.running:
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"\n🔔 [{timestamp}] Начинаю цикл уведомлений")
                
                await self.notification_cycle()
                
                # Ждем до следующего цикла (поддержка дробных минут)
                sleep_seconds = max(1, int(interval_minutes * 60))
                print(f"😴 Ожидание {interval_minutes} минут...")

                for i in range(sleep_seconds):
                    if not self.running:
                        break
                    await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n🛑 Получен сигнал остановки")
            await self.stop_notifications()
    
    async def _on_users_reload(self, new_users):
        """Callback для перезагрузки пользователей"""
        print("🔄 Перезагружаю пользователей User Notification Service...")
        
        # Сохраняем старые времена последней проверки
        old_last_check = self.last_check_time.copy()
        
        # Очищаем текущих пользователей
        self.users = {}
        self.last_check_time = {}
        
        # Загружаем новых пользователей используя существующую логику
        users_data = new_users if new_users else {}
        
        for user_id, user_data in users_data.items():
            # Пропускаем неактивных пользователей
            if not user_data.get('active'):
                continue
            
            telegram_configs = user_data.get('telegram_configs', {})
            for config_id, telegram_config in telegram_configs.items():
                if not telegram_config.get('enabled') or not telegram_config.get('bot_token'):
                    continue
                
                # Создаем TelegramSender для пользователя
                try:
                    telegram_sender = TelegramSender(
                        bot_token=telegram_config['bot_token'],
                        chat_id=telegram_config['chat_id']
                    )
                    
                    # Получаем topics_mapping из конфига
                    topics_mapping = telegram_config.get('topics_mapping', {})
                    
                    # Поддержка фильтрации по ключевым словам (для горячей перезагрузки)
                    filter_config = telegram_config.get('filter_config')
                    keyword_filter = None
                    if filter_config:
                        try:
                            keyword_filter = AdvancedKeywordFilter(filter_config)
                            print(f"   🔍 Фильтр перезагружен: режим={filter_config.get('mode')}, keywords={len(filter_config.get('keywords', []))}")
                        except Exception as e:
                            print(f"   ⚠️ Ошибка создания фильтра: {e}")
                    
                    key = f"{user_id}::{config_id}"
                    self.users[key] = {
                        'name': user_data.get('name', user_id),
                        'telegram_sender': telegram_sender,
                        'sources': telegram_config.get('sources', user_data.get('sources', [])),
                        'topics_mapping': topics_mapping,
                        'processors': telegram_config.get('processors', user_data.get('processors', [])),
                        'keyword_filter': keyword_filter,
                        'chat_id': telegram_config['chat_id']
                    }
                    
                    # Восстанавливаем время последней проверки или ставим текущее
                    if key in old_last_check:
                        self.last_check_time[key] = old_last_check[key]
                        print(f"✅ Пользователь {key} перезагружен (время сохранено)")
                    else:
                        # Устанавливаем время на текущий момент чтобы обрабатывать только новые статьи  
                        self.last_check_time[key] = datetime.now(pytz.timezone('Europe/Moscow'))
                        print(f"✅ Пользователь {key} добавлен (новый)")
                
                except Exception as e:
                    print(f"❌ Ошибка настройки Telegram для {user_id}::{config_id}: {e}")
        
        print(f"✅ Пользователи перезагружены: {len(self.users)} активных")
    
    async def _on_topics_reload(self, new_topics):
        """Callback для перезагрузки топиков mapping"""
        print(f"🔄 Перезагружаю topics mapping: {len(new_topics)} топиков")
        
        # Обновляем topics mapping для всех пользователей
        for user_key, user_data in self.users.items():
            user_data['topics_mapping'] = new_topics
        
        print("✅ Topics mapping обновлен для всех пользователей")
    
    async def stop_notifications(self):
        """Остановка сервиса уведомлений"""
        self.running = False
        print(f"✅ User Notification Service остановлен")

async def main():
    """Главная функция User Notification Service"""
    print("🔔 RSS Media Bus - User Notification Service v3.0")
    print("=" * 60)
    
    service = UserNotificationService()
    
    # Инициализируем БД
    if not await service.initialize_database():
        print("❌ Не удалось подключиться к базе данных")
        return
    
    # Загружаем пользователей
    if not await service.load_users():
        print("❌ Нет активных пользователей для уведомлений")
        return
    
    # Запускаем сервис уведомлений
    try:
        # 1 минута вместо 2 минут - более быстрые уведомления
        await service.start_notifications(interval_minutes=1)
    except KeyboardInterrupt:
        print("\n🛑 Сервис прерван пользователем")
    
    print("👋 User Notification Service завершен")

if __name__ == "__main__":
    asyncio.run(main()) 
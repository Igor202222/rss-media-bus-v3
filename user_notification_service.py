#!/usr/bin/env python3
"""
RSS Media Bus - User Notification Service v3.0
Читает новые статьи из БД и отправляет пользователям по их настройкам
"""

import asyncio
import yaml
import json
import time
import pytz
from datetime import datetime, timedelta
from pathlib import Path

# Импорты наших модулей
from core.database import DatabaseManager
from outputs.telegram_sender import TelegramSender

class UserNotificationService:
    def __init__(self):
        self.db = None
        self.users = {}
        self.running = False
        self.last_check_time = {}
    
    async def load_users(self):
        """Загрузка активных пользователей из config/users.yaml"""
        try:
            users_file = Path("config/users.yaml")
            
            if not users_file.exists():
                raise FileNotFoundError("Файл config/users.yaml не найден")
            
            with open(users_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Проверяем структуру файла (users в корне или в секции 'users')
            users_data = data.get('users', data)
            
            self.users = {}
            for user_id, user_data in users_data.items():
                # Пропускаем неактивных пользователей
                if not user_data.get('active'):
                    continue
                
                # Пропускаем пользователей без Telegram
                telegram_config = user_data.get('telegram', {})
                if not telegram_config.get('enabled') or not telegram_config.get('bot_token'):
                    continue
                
                # Создаем TelegramSender для пользователя
                try:
                    telegram_sender = TelegramSender(
                        bot_token=telegram_config['bot_token'],
                        chat_id=telegram_config['chat_id']
                    )
                    
                    # Загружаем mapping топиков для пользователя
                    topics_mapping = {}
                    try:
                        with open('config/topics_mapping.json', 'r', encoding='utf-8') as f:
                            topics_mapping = json.load(f)
                    except Exception as e:
                        print(f"⚠️ Ошибка загрузки topics_mapping для {user_id}: {e}")
                    
                    self.users[user_id] = {
                        'name': user_data.get('name', user_id),
                        'telegram_sender': telegram_sender,
                        'sources': user_data.get('sources', []),
                        'topics_mapping': topics_mapping,
                        'processors': user_data.get('processors', []),
                        'chat_id': telegram_config['chat_id']
                    }
                    
                    # Инициализируем время последней проверки как ТЕКУЩЕЕ время
                    # Отправляем только статьи, которые появятся ПОСЛЕ запуска сервиса
                    self.last_check_time[user_id] = datetime.now()
                    
                    print(f"✅ Пользователь {user_id} настроен")
                    print(f"   📱 Chat ID: {telegram_config['chat_id']}")
                    print(f"   📡 Источников: {len(user_data.get('sources', []))}")
                    print(f"   📋 Топиков: {len(topics_mapping)}")
                    
                except Exception as e:
                    print(f"❌ Ошибка настройки Telegram для {user_id}: {e}")
            
            print(f"\n📊 Активных пользователей с уведомлениями: {len(self.users)}")
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
    
    def get_user_keywords(self, user_id):
        """Получение ключевых слов пользователя из его процессоров"""
        user_data = self.users.get(user_id, {})
        processors = user_data.get('processors', [])
        
        keywords = []
        for processor in processors:
            if processor.get('name') == 'keyword_filter':
                config = processor.get('config', {})
                keywords.extend(config.get('keywords', []))
        
        return keywords
    
    def should_send_article_to_user(self, article, user_id):
        """Определяет нужно ли отправлять статью пользователю"""
        user_data = self.users.get(user_id, {})
        
        # Проверяем источники пользователя
        user_sources = user_data.get('sources', [])
        if user_sources and article['feed_id'] not in user_sources:
            return False, []
        
        # Проверяем фильтры пользователя
        processors = user_data.get('processors', [])
        
        # Ищем фильтры ключевых слов
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
        
        # Если нет фильтров или фильтры прошли - отправляем
        return True, []
    
    def check_keywords_in_article(self, article, keywords):
        """Проверка наличия ключевых слов в статье"""
        matched_keywords = []
        
        # Текст для поиска (заголовок + описание + контент)
        search_text = " ".join([
            article.get('title', ''),
            article.get('description', ''),
            article.get('content', '')
        ]).lower()
        
        for keyword in keywords:
            if keyword.lower() in search_text:
                matched_keywords.append(keyword)
        
        return matched_keywords
    
    def get_topic_id_for_source(self, user_id, source_id):
        """Получение ID топика для источника у конкретного пользователя"""
        user_data = self.users.get(user_id, {})
        topics_mapping = user_data.get('topics_mapping', {})
        
        if source_id in topics_mapping:
            return topics_mapping[source_id].get('topic_id')
        
        return None
    
    async def send_article_to_user(self, article, user_id, matched_keywords=None):
        """Отправка статьи конкретному пользователю"""
        user_data = self.users.get(user_id)
        if not user_data:
            return False
        
        telegram_sender = user_data['telegram_sender']
        
        # Определяем топик для источника
        topic_id = self.get_topic_id_for_source(user_id, article['feed_id'])
        
        try:
            # Подготавливаем данные для отправки
            title = article.get('title', 'Без заголовка')
            description = article.get('description', '')
            link = article.get('link', '')
            categories = article.get('tags', []) if article.get('tags') else []
            
            # Отправляем через TelegramSender
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
                print(f"📤 {user_id}: {title[:40]}... → {source_name}{topic_info}")
                return True
            else:
                print(f"❌ Ошибка отправки {user_id}: {title[:40]}...")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка отправки статьи пользователю {user_id}: {e}")
            return False
    
    async def check_new_articles_for_user(self, user_id):
        """Проверка и отправка новых статей для конкретного пользователя"""
        if user_id not in self.users:
            return 0
        
        last_check = self.last_check_time.get(user_id)
        
        try:
            # Получаем новые статьи из БД
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            query = """
            SELECT feed_id, title, description, content, link, tags, published_date
            FROM articles 
            WHERE added_date > ? 
            ORDER BY added_date DESC
            LIMIT 100
            """
            
            # Конвертируем локальное время в UTC для сравнения с БД
            moscow_tz = pytz.timezone('Europe/Moscow')
            
            if last_check.tzinfo is None:
                # Предполагаем московское время
                moscow_time = moscow_tz.localize(last_check)
            else:
                moscow_time = last_check
                
            utc_time = moscow_time.astimezone(pytz.UTC)
            utc_str = utc_time.strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(query, (utc_str,))
            articles = cursor.fetchall()
            conn.close()
            
            sent_count = 0
            for article_row in articles:
                # Преобразуем row в словарь
                article = {
                    'feed_id': article_row[0],
                    'title': article_row[1],
                    'description': article_row[2],
                    'content': article_row[3],
                    'link': article_row[4],
                    'tags': json.loads(article_row[5]) if article_row[5] else [],
                    'published_date': article_row[6]
                }
                
                # Проверяем нужно ли отправлять этому пользователю
                should_send, matched_keywords = self.should_send_article_to_user(article, user_id)
                
                if should_send:
                    success = await self.send_article_to_user(article, user_id, matched_keywords)
                    if success:
                        sent_count += 1
                
                # Небольшая пауза между отправками
                await asyncio.sleep(0.5)
            
            # Обновляем время последней проверки
            self.last_check_time[user_id] = datetime.now()
            
            return sent_count
            
        except Exception as e:
            print(f"❌ Ошибка проверки статей для {user_id}: {e}")
            return 0
    
    async def notification_cycle(self):
        """Один цикл проверки и отправки уведомлений всем пользователям"""
        if not self.users:
            print("⚠️ Нет активных пользователей")
            return
        
        cycle_start = datetime.now()
        total_sent = 0
        
        print(f"🔔 Проверяю новые статьи для {len(self.users)} пользователей...")
        
        for user_id in self.users:
            try:
                user_name = self.users[user_id]['name']
                print(f"👤 {user_name[:20]}...", end=" ")
                
                sent_count = await self.check_new_articles_for_user(user_id)
                total_sent += sent_count
                
                if sent_count > 0:
                    print(f"📤 {sent_count} статей")
                else:
                    print("📡 без новых")
                
                # Пауза между пользователями
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Ошибка для пользователя {user_id}: {e}")
        
        cycle_duration = (datetime.now() - cycle_start).total_seconds()
        
        print(f"\n📊 Цикл уведомлений завершен за {cycle_duration:.1f}с:")
        print(f"  👥 Пользователей: {len(self.users)}")
        print(f"  📤 Отправлено статей: {total_sent}")
    
    async def start_notifications(self, interval_minutes=2):
        """Запуск сервиса уведомлений"""
        self.running = True
        
        print(f"🔔 User Notification Service запущен")
        print(f"⏰ Интервал: {interval_minutes} минут")
        print(f"👥 Активных пользователей: {len(self.users)}")
        print(f"📱 Режим: уведомления в Telegram")
        print(f"🔄 Для остановки: Ctrl+C")
        print("=" * 50)
        
        try:
            while self.running:
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"\n🔔 [{timestamp}] Начинаю цикл уведомлений")
                
                await self.notification_cycle()
                
                # Ждем до следующего цикла
                sleep_seconds = interval_minutes * 60
                print(f"😴 Ожидание {interval_minutes} минут...")
                
                for i in range(sleep_seconds):
                    if not self.running:
                        break
                    await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n🛑 Получен сигнал остановки")
            await self.stop_notifications()
    
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
        await service.start_notifications(interval_minutes=2)
    except KeyboardInterrupt:
        print("\n🛑 Сервис прерван пользователем")
    
    print("👋 User Notification Service завершен")

if __name__ == "__main__":
    asyncio.run(main()) 
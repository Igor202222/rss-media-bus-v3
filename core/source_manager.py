import feedparser
import aiohttp
import asyncio
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import traceback

class AsyncRSSParser:
    def __init__(self, db_manager, telegram_sender=None, keywords=None, config=None):
        self.db = db_manager
        self.telegram = telegram_sender
        self.keywords = keywords or []
        self.config = config
        
        # Новая система: настройки по источникам
        self.source_modes = self._load_source_modes(config)
        
        # Старая система для обратной совместимости
        self.forward_all = self._determine_forward_mode(config)
        self.filter_by_keywords = not self.forward_all
        
        # Счетчики ошибок для каждого источника
        self.error_counts = {}
        self.last_error_time = {}
        
        mode_str = self._get_mode_description()
        print(f"🔍 AsyncRSSParser режим: {mode_str}")
        
    def _load_source_modes(self, config):
        """Загрузка настроек по источникам из конфига"""
        if not config or not hasattr(config, 'SOURCE_MODES'):
            return {}
        
        source_modes = getattr(config, 'SOURCE_MODES', {})
        if source_modes:
            print(f"🎯 Найдены настройки для {len(source_modes)} источников")
            for domain, settings in source_modes.items():
                if domain != 'default':
                    mode = settings.get('mode', 'filter')
                    topic = settings.get('topic_id', 'None')
                    print(f"  📡 {domain}: {mode}, топик {topic}")
        
        return source_modes
    
    def _get_mode_description(self):
        """Описание режима работы"""
        if self.source_modes:
            return f"Гибкие настройки по источникам ({len(self.source_modes)} правил)"
        elif self.forward_all:
            return "Все новости"
        else:
            return "Фильтрация по ключевым словам"
    
    def _determine_forward_mode(self, config):
        """Определение режима работы из конфигурации (для обратной совместимости)"""
        if not config:
            return len(self.keywords) == 0
        
        if hasattr(config, 'FORWARD_ALL_NEWS'):
            return config.FORWARD_ALL_NEWS
        
        if hasattr(config, 'FILTER_BY_KEYWORDS'):
            return not config.FILTER_BY_KEYWORDS
        
        return len(self.keywords) == 0
    
    def _get_source_settings(self, feed_url):
        """Получение настроек для конкретного источника"""
        if not self.source_modes:
            # Обратная совместимость - используем глобальные настройки
            return {
                'mode': 'forward_all' if self.forward_all else 'filter',
                'keywords': self.keywords,
                'topic_id': getattr(self.config, 'TELEGRAM_TOPIC_ID', None)
            }
        
        # Извлекаем домен из URL
        try:
            domain = urlparse(feed_url).netloc.lower()
            domain = domain.replace('www.', '')
        except:
            domain = feed_url
        
        # Ищем точное совпадение домена
        for source_domain, settings in self.source_modes.items():
            if source_domain == 'default':
                continue
            if source_domain in domain:
                # Создаем полные настройки для источника
                source_settings = {
                    'mode': settings.get('mode', 'filter'),
                    'keywords': settings.get('keywords', self.keywords),
                    'topic_id': settings.get('topic_id', None)
                }
                print(f"🎯 {domain}: режим '{source_settings['mode']}', топик {source_settings['topic_id']}")
                return source_settings
        
        # Используем настройки по умолчанию
        default_settings = self.source_modes.get('default', {})
        return {
            'mode': default_settings.get('mode', 'filter'),
            'keywords': default_settings.get('keywords', self.keywords),
            'topic_id': default_settings.get('topic_id', None)
        }
        
    async def parse_all_feeds_async(self, feeds):
        """Асинхронная обработка всех RSS источников"""
        if not feeds:
            print("⚠️ Нет активных источников")
            return 0
        
        print(f"📡 Начинаю асинхронную обработку {len(feeds)} источников")
        
        # Создаем сессию для HTTP запросов
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(
            limit=10, 
            limit_per_host=3,
            force_close=True,
            enable_cleanup_closed=True
        )
        
        headers = {
            'User-Agent': 'RSS Media Monitor/2.0 (Enhanced AsyncRSSParser)',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        }
        
        async with aiohttp.ClientSession(
            timeout=timeout, 
            connector=connector,
            headers=headers
        ) as session:
            
            # Создаем задачи для всех источников
            tasks = []
            for feed_info in feeds:
                feed_id, feed_url = feed_info[0], feed_info[1]
                
                # Пропускаем источники с частыми ошибками
                if self.should_skip_feed(feed_url):
                    continue
                
                task = self._parse_single_feed_async(session, feed_id, feed_url)
                tasks.append(task)
            
            if not tasks:
                print("⚠️ Нет доступных источников для обработки")
                return 0
            
            # Выполняем все задачи параллельно с ограничением
            semaphore = asyncio.Semaphore(5)
            
            async def limited_task(task):
                async with semaphore:
                    return await task
            
            limited_tasks = [limited_task(task) for task in tasks]
            results = await asyncio.gather(*limited_tasks, return_exceptions=True)
            
            # Обрабатываем результаты
            total_new_articles = 0
            successful_feeds = 0
            failed_feeds = 0
            
            for i, result in enumerate(results):
                if i < len(feeds):
                    feed_url = feeds[i][1]
                    if isinstance(result, Exception):
                        print(f"❌ Ошибка при обработке {feed_url}: {result}")
                        failed_feeds += 1
                        self._record_feed_error(feed_url)
                    else:
                        total_new_articles += result
                        successful_feeds += 1
                        self._reset_feed_errors(feed_url)
            
            print(f"📊 Обработано: {successful_feeds} успешно, {failed_feeds} с ошибками")
            print(f"📰 Всего новых статей: {total_new_articles}")
            
            return total_new_articles
    
    async def _parse_single_feed_async(self, session, feed_id, feed_url):
        """Асинхронная обработка одного RSS источника"""
        max_retries = 3
        retry_delay = 2
        
        # Получаем настройки для этого источника
        source_settings = self._get_source_settings(feed_url)
        
        for attempt in range(max_retries):
            try:
                print(f"📡 Попытка {attempt + 1}/{max_retries}: {feed_url}")
                
                # Скачиваем RSS
                async with session.get(feed_url) as response:
                    if response.status == 404:
                        print(f"❌ RSS не найден (404): {feed_url}")
                        return 0
                    elif response.status >= 400:
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status
                        )
                    
                    content = await response.text(encoding='utf-8', errors='ignore')
                    
                    if not content or len(content) < 100:
                        raise Exception("Получен пустой или слишком короткий ответ")
                
                # Парсим RSS в отдельном потоке
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor(max_workers=2) as executor:
                    feed_data = await loop.run_in_executor(
                        executor, self._safe_parse_feed, content
                    )
                
                if not feed_data or not feed_data.entries:
                    print(f"⚠️ RSS пустой или некорректный: {feed_url}")
                    return 0
                
                # Обновляем информацию об источнике
                feed_title = getattr(feed_data.feed, 'title', self._extract_domain_name(feed_url))
                self.db.update_feed_info(feed_id, title=feed_title)
                
                # Обрабатываем статьи с настройками источника
                new_articles_count = await self._process_articles_async(
                    feed_id, feed_url, feed_data.entries, source_settings
                )
                
                print(f"✅ {feed_url}: {new_articles_count} новых статей")
                return new_articles_count
                
            except asyncio.TimeoutError:
                print(f"⏰ Таймаут для {feed_url} (попытка {attempt + 1})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                
            except aiohttp.ClientError as e:
                print(f"🌐 Сетевая ошибка {feed_url}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                
            except Exception as e:
                print(f"❌ Ошибка парсинга {feed_url}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
        
        print(f"💥 Все попытки исчерпаны для {feed_url}")
        return 0
    
    def _safe_parse_feed(self, content):
        """Безопасный парсинг RSS с обработкой ошибок"""
        try:
            return feedparser.parse(content)
        except Exception as e:
            print(f"⚠️ Ошибка парсинга feedparser: {e}")
            return None
    
    async def _process_articles_async(self, feed_id, feed_url, entries, source_settings):
        """Асинхронная обработка статей из RSS с настройками источника"""
        new_articles_count = 0
        articles_to_send = []
        
        # Получаем максимальный возраст статей
        max_age_hours = getattr(self.config, 'MAX_ARTICLE_AGE_HOURS', 24)
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        
        # Обрабатываем статьи в обратном порядке (старые первыми)
        for entry in entries[:50]:
            try:
                article_data = self._extract_article_data(entry)
                if not article_data:
                    continue
                
                # Проверяем возраст статьи
                if article_data.get('published_date'):
                    if article_data['published_date'] < cutoff_time:
                        continue
                
                # Проверяем существование статьи
                if self.db.article_exists(article_data.get('link')):
                    continue
                
                # Определяем нужно ли отправлять статью с настройками источника
                should_send, matched_keywords = self._should_send_article(article_data, source_settings)
                
                # Сохраняем в базу данных
                article_id = self.db.add_article(
                    feed_id=feed_id,
                    title=article_data['title'],
                    link=article_data['link'],
                    description=article_data['description'],
                    content=article_data['content'],
                    author=article_data['author'],
                    published_date=article_data['published_date']
                )
                
                if article_id:
                    new_articles_count += 1
                    
                    # Добавляем к отправке если подходит
                    if should_send:
                        article_data['matched_keywords'] = matched_keywords
                        article_data['source_url'] = feed_url
                        article_data['topic_id'] = source_settings.get('topic_id')
                        articles_to_send.append(article_data)
                        
            except Exception as e:
                print(f"⚠️ Ошибка обработки статьи: {e}")
                continue
        
        # Отправляем статьи в Telegram если есть
        if articles_to_send and self.telegram:
            await self._send_articles_to_telegram(articles_to_send, feed_url)
        
        return new_articles_count
    
    def _should_send_article(self, article_data, source_settings):
        """Определяет нужно ли отправлять статью с настройками источника"""
        mode = source_settings.get('mode', 'filter')
        keywords = source_settings.get('keywords', [])
        
        if mode == 'forward_all':
            # Режим "все новости" для этого источника
            return True, ["ВСЕ НОВОСТИ"]
        
        elif mode == 'filter':
            # Режим фильтрации для этого источника
            if not keywords:
                return True, []
            
            matched_keywords = self._check_keywords(article_data, keywords)
            return len(matched_keywords) > 0, matched_keywords
        
        # Неизвестный режим - используем фильтрацию
        return False, []
    
    def _extract_article_data(self, entry):
        """Извлечение данных из RSS статьи"""
        try:
            # Заголовок
            title = entry.get('title', '').strip()
            if not title:
                return None
            
            # Ссылка
            link = entry.get('link', '').strip()
            
            # Описание
            description = entry.get('summary', '') or entry.get('description', '')
            if description:
                import re
                description = re.sub(r'<[^>]+>', '', description)
                description = description.strip()
            
            # Контент
            content = ''
            if hasattr(entry, 'content') and entry.content:
                content = entry.content[0].value if entry.content else ''
                if content:
                    import re
                    content = re.sub(r'<[^>]+>', '', content).strip()
            
            # Автор
            author = entry.get('author', '')
            
            # Дата публикации
            published_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                utc_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                published_date = utc_date
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                utc_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                published_date = utc_date
            else:
                published_date = datetime.now(timezone.utc)
            
            # Категории RSS
            categories = []
            if hasattr(entry, 'tags'):
                categories.extend([tag.term for tag in entry.tags if hasattr(tag, 'term')])
            if hasattr(entry, 'category'):
                categories.append(entry.category)
            
            return {
                'title': title,
                'link': link,
                'description': description,
                'content': content,
                'author': author,
                'published_date': published_date,
                'categories': categories
            }
            
        except Exception as e:
            print(f"⚠️ Ошибка извлечения данных статьи: {e}")
            return None
    
    def _check_keywords(self, article_data, keywords=None):
        """Проверка статьи на соответствие ключевым словам"""
        if keywords is None:
            keywords = self.keywords
        
        if not keywords:
            return []
        
        matched_keywords = []
        
        # Подготавливаем текст для поиска
        search_texts = [
            article_data.get('title', '').lower(),
            article_data.get('description', '').lower(),
            article_data.get('content', '').lower(),
            article_data.get('author', '').lower(),
        ]
        
        # Добавляем категории RSS
        categories_text = ' '.join(article_data.get('categories', [])).lower()
        search_texts.append(categories_text)
        
        # Объединяем весь текст
        full_text = ' '.join(search_texts)
        
        # Проверяем каждое ключевое слово
        for keyword in keywords:
            keyword_lower = keyword.lower().strip()
            if keyword_lower and keyword_lower in full_text:
                matched_keywords.append(keyword)
        
        return matched_keywords
    
    async def _send_articles_to_telegram(self, articles, source_url):
        """Отправка статей в Telegram"""
        source_name = self._extract_domain_name(source_url)
        
        for article in articles:
            try:
                # Используем topic_id из настроек источника
                topic_id = article.get('topic_id')
                
                # Отправляем через обновленный метод TelegramSender
                success = self.telegram.send_article(
                    title=article['title'],
                    description=article.get('description', ''),
                    link=article.get('link', ''),
                    source=source_name,
                    keywords=article.get('matched_keywords', []),
                    categories=article.get('categories', []),
                    topic_id=topic_id
                )
                
                if success:
                    keywords_str = ', '.join(article.get('matched_keywords', [])[:2])
                    topic_str = f" → топик {topic_id}" if topic_id else ""
                    print(f"📱 Отправлено: {article['title'][:40]}... [{keywords_str}]{topic_str}")
                else:
                    print(f"❌ Не удалось отправить: {article['title'][:40]}...")
                
                # Небольшая задержка между сообщениями
                await asyncio.sleep(1)
                
            except Exception as e:
                print(f"❌ Ошибка отправки в Telegram: {e}")
    
    def _extract_domain_name(self, url):
        """Извлекает доменное имя из URL для названия источника"""
        try:
            if "tass.ru" in url:
                return "ТАСС"
            elif "lenta.ru" in url:
                return "Lenta.ru"
            elif "ria.ru" in url:
                return "РИА Новости"
            elif "interfax.ru" in url:
                return "Интерфакс"
            elif "kommersant.ru" in url:
                return "Коммерсант"
            elif "rbc.ru" in url:
                return "РБК"
            else:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                return domain.replace('www.', '')
        except:
            return "RSS источник"
    
    def _record_feed_error(self, feed_url):
        """Записывает ошибку для источника"""
        self.error_counts[feed_url] = self.error_counts.get(feed_url, 0) + 1
        self.last_error_time[feed_url] = time.time()
    
    def _reset_feed_errors(self, feed_url):
        """Сбрасывает счетчик ошибок для источника"""
        if feed_url in self.error_counts:
            del self.error_counts[feed_url]
        if feed_url in self.last_error_time:
            del self.last_error_time[feed_url]
    
    def get_error_count(self, feed_url):
        """Получить количество ошибок для источника"""
        return self.error_counts.get(feed_url, 0)
    
    def should_skip_feed(self, feed_url, max_errors=5):
        """Проверить, стоит ли пропустить источник из-за ошибок"""
        error_count = self.get_error_count(feed_url)
        if error_count >= max_errors:
            last_error = self.last_error_time.get(feed_url, 0)
            delay_minutes = min(60, 2 ** error_count)
            
            if time.time() - last_error < delay_minutes * 60:
                print(f"⏸️ Пропускаю {feed_url} на {delay_minutes} минут (ошибок: {error_count})")
                return True
        
        return False
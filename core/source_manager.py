import feedparser
import aiohttp
import asyncio
import sqlite3
import time
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import traceback
from .error_manager import ErrorManager

class AsyncRSSParser:
    def __init__(self, db_manager, config=None):
        self.db = db_manager
        self.config = config
        
        # Новая система управления ошибками
        self.error_manager = ErrorManager(db_manager)
        
        print(f"🧐 AsyncRSSParser: только парсинг и сохранение в БД")

    async def parse_all_feeds_async(self, feeds):
        if not feeds:
            print("⚠️ Нет активных источников")
            return 0
        print(f"📡 Начинаю асинхронную обработку {len(feeds)} источников")
        timeout = aiohttp.ClientTimeout(total=30)
        connector = aiohttp.TCPConnector(
            limit=10, 
            limit_per_host=3,
            force_close=True,
            enable_cleanup_closed=True
        )
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive'
        }
        async with aiohttp.ClientSession(
            timeout=timeout, 
            connector=connector,
            headers=headers
        ) as session:
            tasks = []
            for i, feed_info in enumerate(feeds):
                # Поддержка разных форматов: старый (id, url), новый (id, url, name), с прокси (id, url, name, proxy_required, proxy_settings)
                if len(feed_info) >= 5:
                    feed_id, feed_url, feed_name, proxy_required, proxy_settings = feed_info
                elif len(feed_info) >= 3:
                    feed_id, feed_url, feed_name = feed_info[0], feed_info[1], feed_info[2]
                    proxy_required, proxy_settings = False, {}
                else:
                    feed_id, feed_url = feed_info[0], feed_info[1]
                    feed_name = self._extract_domain_name(feed_url)
                    proxy_required, proxy_settings = False, {}
                
                should_skip, reason = self.error_manager.should_skip_feed(feed_url)
                if should_skip:
                    print(f"⏸️ {feed_name}: {reason}")
                    continue
                task = self._parse_single_feed_async(session, feed_id, feed_url, feed_name, proxy_required, proxy_settings)
                tasks.append(task)
            if not tasks:
                print("⚠️ Нет доступных источников для обработки")
                return 0
            semaphore = asyncio.Semaphore(5)
            async def limited_task(task):
                async with semaphore:
                    return await task
            limited_tasks = [limited_task(task) for task in tasks]
            results = await asyncio.gather(*limited_tasks, return_exceptions=True)
            total_new_articles = 0
            successful_feeds = 0
            failed_feeds = 0
            # Сопоставляем результаты с задачами
            task_index = 0
            for i, feed_info in enumerate(feeds):
                feed_name = feed_info[2] if len(feed_info) >= 3 else self._extract_domain_name(feed_info[1])
                
                should_skip, _ = self.error_manager.should_skip_feed(feed_info[1])
                if should_skip:
                    continue
                    
                if task_index < len(results):
                    result = results[task_index]
                    task_index += 1
                    
                    if isinstance(result, Exception):
                        print(f"❌ {feed_name}: {str(result)[:50]}")
                        failed_feeds += 1
                        self.error_manager.record_error(
                            feed_info[1], feed_name, "exception", 
                            error_message=str(result)[:100]
                        )
                    else:
                        total_new_articles += result
                        successful_feeds += 1
                        self.error_manager.reset_errors(feed_info[1])
                        if result > 0:
                            print(f"✅ {feed_name}: {result} новых")
                        else:
                            print(f"📡 {feed_name}: без новых")
            print(f"📊 Обработано: {successful_feeds} успешно, {failed_feeds} с ошибками")
            print(f"📰 Всего новых статей: {total_new_articles}")
            return total_new_articles

    async def _parse_single_feed_async(self, session, feed_id, feed_url, feed_name=None, proxy_required=False, proxy_settings=None):
        if not feed_name:
            feed_name = self._extract_domain_name(feed_url)
        
        if proxy_settings is None:
            proxy_settings = {}
            
        max_retries = 3
        retry_delay = 2
        
        # Определяем нужно ли использовать прокси
        current_session = session
        proxy_session = None
        
        if proxy_required and proxy_settings.get('url'):
            print(f"🌐 {feed_name}: используем прокси ({proxy_settings.get('region', 'unknown')})")
            # Создаем отдельную сессию с прокси
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(
                limit=5,
                limit_per_host=2,
                force_close=True,
                enable_cleanup_closed=True
            )
            headers = {
                'User-Agent': 'RSS Media Monitor/2.0 (Proxy)',
                'Accept': 'application/rss+xml, application/xml, text/xml, */*',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
            proxy_session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers=headers
            )
            current_session = proxy_session
        
        try:
            for attempt in range(max_retries):
                try:
                    if attempt > 0:
                        print(f"📡 {feed_name} попытка {attempt + 1}/{max_retries}")
                    
                    # Используем прокси если настроен
                    request_kwargs = {}
                    if proxy_required and proxy_settings.get('url'):
                        request_kwargs['proxy'] = proxy_settings['url']
                    
                    async with current_session.get(feed_url, **request_kwargs) as response:
                        if response.status == 404:
                            print(f"❌ {feed_name}: RSS не найден (404)")
                            self.error_manager.record_error(
                                feed_url, feed_name, "not_found", 404, "RSS feed не найден"
                            )
                            return 0
                        elif response.status >= 400:
                            # Специальная обработка 403 ошибок
                            if response.status == 403:
                                alternative = self.error_manager.should_try_alternative_method(feed_url, 403)
                                print(f"🚫 {feed_name}: 403 Forbidden (рекомендация: {alternative})")
                                self.error_manager.record_error(
                                    feed_url, feed_name, "forbidden", 403, 
                                    f"Доступ запрещен, попробуйте: {alternative}"
                                )
                            else:
                                self.error_manager.record_error(
                                    feed_url, feed_name, "http_error", response.status, 
                                    f"HTTP {response.status}"
                                )
                            
                            raise aiohttp.ClientResponseError(
                                request_info=response.request_info,
                                history=response.history,
                                status=response.status
                            )
                        content = await response.text(encoding='utf-8', errors='ignore')
                        if not content or len(content) < 100:
                            raise Exception("Получен пустой или слишком короткий ответ")
                    
                    loop = asyncio.get_event_loop()
                    with ThreadPoolExecutor(max_workers=2) as executor:
                        feed_data = await loop.run_in_executor(
                            executor, self._safe_parse_feed, content
                        )
                    if not feed_data or not feed_data.entries:
                        print(f"⚠️ {feed_name}: RSS пустой")
                        return 0
                    feed_title = getattr(feed_data.feed, 'title', self._extract_domain_name(feed_url))
                    # Обновляем информацию о ленте по URL, чтобы таблица feeds содержала запись
                    self.db.update_feed_info(feed_url=feed_url, title=feed_title)
                    new_articles_count = await self._process_articles_async(
                        feed_id, feed_url, feed_data.entries
                    )
                    return new_articles_count
                except asyncio.TimeoutError:
                    print(f"⏰ {feed_name}: таймаут (попытка {attempt + 1})")
                    if attempt == max_retries - 1:  # Последняя попытка
                        self.error_manager.record_error(
                            feed_url, feed_name, "timeout", 
                            error_message="Превышено время ожидания ответа"
                        )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                except aiohttp.ClientError as e:
                    print(f"🌐 {feed_name}: сетевая ошибка")
                    if attempt == max_retries - 1:  # Последняя попытка
                        self.error_manager.record_error(
                            feed_url, feed_name, "network_error", 
                            error_message=str(e)[:100]
                        )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
                except Exception as e:
                    print(f"❌ {feed_name}: ошибка парсинга")
                    if attempt == max_retries - 1:  # Последняя попытка
                        self.error_manager.record_error(
                            feed_url, feed_name, "parsing_error", 
                            error_message=str(e)[:100]
                        )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2
        finally:
            # Закрываем прокси сессию если была создана
            if proxy_session:
                await proxy_session.close()
        print(f"💥 {feed_name}: все попытки исчерпаны")
        return 0

    def _safe_parse_feed(self, content):
        try:
            return feedparser.parse(content)
        except Exception as e:
            print(f"⚠️ Ошибка парсинга feedparser: {e}")
            return None

    async def _process_articles_async(self, feed_id, feed_url, entries):
        new_articles_count = 0
        max_age_hours = getattr(self.config, 'MAX_ARTICLE_AGE_HOURS', 24) if self.config else 24
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        for entry in entries[:50]:
            try:
                article_data = self._extract_article_data(entry)
                if not article_data:
                    continue
                if article_data.get('published_date'):
                    if article_data['published_date'] < cutoff_time:
                        continue
                if self.db.article_exists(article_data.get('link')):
                    continue
                article_id = self.db.add_article(
                    feed_id=feed_id,
                    title=article_data['title'],
                    link=article_data['link'],
                    description=article_data['description'],
                    content=article_data['content'],
                    author=article_data['author'],
                    published_date=article_data['published_date'],
                    guid=article_data.get('guid'),
                    category=article_data.get('category'),
                    tags=article_data.get('tags'),
                    full_text=article_data.get('full_text'),
                    media_attachments=article_data.get('media_attachments'),
                    modification_date=article_data.get('modification_date'),
                    news_id=article_data.get('news_id'),
                    content_type=article_data.get('content_type'),
                    newsline=article_data.get('newsline')
                )
                if article_id:
                    new_articles_count += 1
            except Exception as e:
                print(f"⚠️ Ошибка обработки статьи: {e}")
                continue
        return new_articles_count

    def _extract_domain_name(self, url):
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

    # Старые методы обработки ошибок удалены - теперь используется ErrorManager

    def _extract_article_data(self, entry):
        try:
            import re
            title = entry.get('title', '').strip()
            if not title:
                return None
            link = entry.get('link', '').strip()
            guid = entry.get('guid', '') or entry.get('id', '')
            description = entry.get('summary', '') or entry.get('description', '')
            if description:
                description = re.sub(r'<[^>]+>', '', description)
                description = description.strip()
            content = ''
            if hasattr(entry, 'content') and entry.content:
                content = entry.content[0].value if entry.content else ''
                if content:
                    content = re.sub(r'<[^>]+>', '', content).strip()
            full_text = ''
            if hasattr(entry, 'rbc_news_full-text'):
                full_text = entry['rbc_news_full-text']
            elif hasattr(entry, 'full_text'):
                full_text = entry.full_text
            if full_text:
                full_text = re.sub(r'<[^>]+>', '', full_text).strip()
            author = entry.get('author', '')
            published_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                utc_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                published_date = utc_date
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                utc_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
                published_date = utc_date
            else:
                published_date = datetime.now(timezone.utc)
            modification_date = None
            if hasattr(entry, 'rbc_news_newsmodifdate'):
                try:
                    mod_date_str = entry['rbc_news_newsmodifdate']
                    import email.utils
                    mod_timestamp = email.utils.parsedate_tz(mod_date_str)
                    if mod_timestamp:
                        modification_date = datetime(*mod_timestamp[:6], tzinfo=timezone.utc)
                except:
                    pass
            category = entry.get('category', '')
            tags = []
            if hasattr(entry, 'tags'):
                tags.extend([tag.term for tag in entry.tags if hasattr(tag, 'term')])
            if hasattr(entry, 'rbc_news_tag'):
                if isinstance(entry['rbc_news_tag'], list):
                    tags.extend(entry['rbc_news_tag'])
                else:
                    tags.append(entry['rbc_news_tag'])
            media_attachments = []
            if hasattr(entry, 'enclosures'):
                for enclosure in entry.enclosures:
                    media_attachments.append({
                        'type': 'enclosure',
                        'url': getattr(enclosure, 'href', ''),
                        'mime_type': getattr(enclosure, 'type', ''),
                        'length': getattr(enclosure, 'length', 0)
                    })
            if hasattr(entry, 'rbc_news_image'):
                images = entry['rbc_news_image']
                if not isinstance(images, list):
                    images = [images]
                for img in images:
                    if isinstance(img, dict):
                        media_attachments.append({
                            'type': 'image',
                            'url': img.get('rbc_news_url', ''),
                            'mime_type': img.get('rbc_news_type', 'image/jpeg'),
                            'source': img.get('rbc_news_source', ''),
                            'copyright': img.get('rbc_news_copyright', '')
                        })
            if hasattr(entry, 'rbc_news_video'):
                video = entry['rbc_news_video']
                if isinstance(video, dict):
                    media_attachments.append({
                        'type': 'video',
                        'url': video.get('url', ''),
                        'mime_type': video.get('type', 'video/mp4'),
                        'copyright': video.get('copyright', '')
                    })
            news_id = ''
            content_type = 'article'
            newsline = ''
            if hasattr(entry, 'rbc_news_news_id'):
                news_id = entry['rbc_news_news_id']
            if hasattr(entry, 'rbc_news_type'):
                content_type = entry['rbc_news_type']
            if hasattr(entry, 'rbc_news_newsline'):
                newsline = entry['rbc_news_newsline']
            return {
                'title': title,
                'link': link,
                'guid': guid,
                'description': description,
                'content': content,
                'full_text': full_text,
                'author': author,
                'published_date': published_date,
                'modification_date': modification_date,
                'category': category,
                'tags': tags,
                'media_attachments': media_attachments,
                'news_id': news_id,
                'content_type': content_type,
                'newsline': newsline,
                'categories': tags
            }
        except Exception as e:
            print(f"⚠️ Ошибка извлечения данных статьи: {e}")
            traceback.print_exc()
            return None
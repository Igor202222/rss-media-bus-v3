import sqlite3
import os
from datetime import datetime
from config import DATABASE_PATH

class DatabaseManager:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            title TEXT,
            description TEXT,
            active BOOLEAN DEFAULT 1,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feed_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            link TEXT UNIQUE,
            description TEXT,
            content TEXT,
            author TEXT,
            published_date TIMESTAMP,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            guid TEXT,
            category TEXT,
            tags TEXT,
            full_text TEXT,
            media_attachments TEXT,
            modification_date TIMESTAMP,
            news_id TEXT,
            content_type TEXT,
            newsline TEXT,
            FOREIGN KEY (feed_id) REFERENCES feeds (id)
        )''')
        
        # Попытка добавить новые поля к существующей таблице (миграция)
        self._migrate_articles_table()
        
        conn.commit()
        conn.close()
        print("✅ База данных инициализирована")
    
    def _migrate_articles_table(self):
        """Миграция существующей таблицы articles для добавления новых полей"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Список новых полей для добавления
        new_fields = [
            ('guid', 'TEXT'),
            ('category', 'TEXT'), 
            ('tags', 'TEXT'),
            ('full_text', 'TEXT'),
            ('media_attachments', 'TEXT'),
            ('modification_date', 'TIMESTAMP'),
            ('news_id', 'TEXT'),
            ('content_type', 'TEXT'),
            ('newsline', 'TEXT')
        ]
        
        # Проверяем существующие колонки
        cursor.execute("PRAGMA table_info(articles)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        # Добавляем недостающие колонки
        for field_name, field_type in new_fields:
            if field_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE articles ADD COLUMN {field_name} {field_type}")
                    print(f"✅ Добавлен столбец: {field_name}")
                except Exception as e:
                    print(f"⚠️ Ошибка добавления столбца {field_name}: {e}")
        
        conn.commit()
        conn.close()
    
    def add_feed(self, url, title=None, description=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO feeds (url, title, description) VALUES (?, ?, ?)', 
                         (url, title, description))
            feed_id = cursor.lastrowid
            conn.commit()
            print(f"✅ Добавлен источник: {title or url}")
            return feed_id
        except sqlite3.IntegrityError:
            print(f"⚠️  Источник уже существует: {url}")
            return None
        finally:
            conn.close()
    
    def get_feed_id_by_url(self, url):
        """Получение feed_id по URL (для совместимости с MockDBManager)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM feeds WHERE url = ?', (url,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return result[0]
        else:
            # Автоматически создаем источник если его нет
            return self.add_feed(url, f"Auto-created: {url}")
    
    def get_all_feeds(self, active_only=True):
        conn = self.get_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM feeds"
        if active_only:
            query += " WHERE active = 1"
        cursor.execute(query)
        feeds = cursor.fetchall()
        conn.close()
        return feeds
    
    def search_articles(self, keywords, limit=20):
        conn = self.get_connection()
        cursor = conn.cursor()
        search_terms = []
        params = []
        for keyword in keywords:
            term = f"%{keyword.lower()}%"
            search_terms.append('(LOWER(a.title) LIKE ? OR LOWER(a.description) LIKE ? OR LOWER(a.content) LIKE ?)')
            params.extend([term, term, term])
        
        query = f'''SELECT a.title, a.link, a.description, a.published_date, 
                   a.author, f.title as feed_title, f.url as feed_url
            FROM articles a JOIN feeds f ON a.feed_id = f.id
            WHERE {' AND '.join(search_terms)}
            ORDER BY a.published_date DESC LIMIT ?'''
        
        params.append(limit)
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        return results
    
    def add_article(self, feed_id, title, link, description, content, author, published_date, 
                   guid=None, category=None, tags=None, full_text=None, media_attachments=None, 
                   modification_date=None, news_id=None, content_type=None, newsline=None):
        """Добавление статьи с расширенными полями"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Конвертируем tags и media_attachments в JSON строки
            import json
            tags_json = json.dumps(tags, ensure_ascii=False) if tags else None
            media_json = json.dumps(media_attachments, ensure_ascii=False) if media_attachments else None
            
            cursor.execute('''
                INSERT INTO articles 
                (feed_id, title, link, description, content, author, published_date,
                 guid, category, tags, full_text, media_attachments, modification_date,
                 news_id, content_type, newsline)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (feed_id, title, link, description, content, author, published_date,
                  guid, category, tags_json, full_text, media_json, modification_date,
                  news_id, content_type, newsline))
            
            conn.commit()
            article_id = cursor.lastrowid
            print(f"💾 Сохранена статья: {title[:50]}...")
            return article_id
            
        except sqlite3.IntegrityError:
            # Статья уже существует
            return None
        finally:
            conn.close()

    def save_article(self, article_data):
        """Сохранение статьи из словаря (для совместимости с MockDBManager)"""
        return self.add_article(
            feed_id=article_data.get('feed_id', 1),
            title=article_data.get('title', ''),
            link=article_data.get('link', ''),
            description=article_data.get('description', ''),
            content=article_data.get('content', ''),
            author=article_data.get('author', ''),
            published_date=article_data.get('published_date'),
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

    def update_feed_info(self, feed_url=None, feed_id=None, status=None, last_check=None, articles_count=0, error_msg=None, title=None, **kwargs):
        """Обновление информации о фиде - совместимость с MockDBManager и новый интерфейс"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Определяем feed_id
        if feed_url and not feed_id:
            feed_id = self.get_feed_id_by_url(feed_url)
        
        if not feed_id:
            print(f"⚠️ Не удалось определить feed_id для {feed_url}")
            conn.close()
            return
        
        updates = []
        params = []
        
        if title:
            updates.append("title = ?")
            params.append(title)
        
        updates.append("last_updated = ?")
        params.append(datetime.now())
        params.append(feed_id)
        
        query = f"UPDATE feeds SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
        conn.close()
    
    def get_feed_stats(self):
        """Статистика по источникам"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT f.title, f.url, f.active,
                   COUNT(a.id) as articles_count,
                   MAX(a.published_date) as last_article_date,
                   f.last_updated
            FROM feeds f
            LEFT JOIN articles a ON f.id = a.feed_id
            GROUP BY f.id
            ORDER BY articles_count DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def get_articles_by_feed(self, feed_id, limit=100):
        """Получение статей источника"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT title, link, description, published_date, author
            FROM articles 
            WHERE feed_id = ?
            ORDER BY published_date DESC
            LIMIT ?
        ''', (feed_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        return results
    
    def article_exists(self, link):
        """Проверка существования статьи по ссылке"""
        if not link:
            return False
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM articles WHERE link = ?', (link,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def is_article_new(self, url):
        """Проверка новизны статьи (для совместимости с MockDBManager)"""
        return not self.article_exists(url)
    
    def cleanup_old_articles(self, days):
        """Удаление старых статей"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM articles 
            WHERE added_date < datetime('now', '-{} days')
        '''.format(days))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted
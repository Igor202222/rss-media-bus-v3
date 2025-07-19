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
            FOREIGN KEY (feed_id) REFERENCES feeds (id)
        )''')
        
        conn.commit()
        conn.close()
        print("✅ База данных инициализирована")
    
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
    
    def add_article(self, feed_id, title, link, description, content, author, published_date):
        """Добавление статьи"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO articles 
                (feed_id, title, link, description, content, author, published_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (feed_id, title, link, description, content, author, published_date))
            
            conn.commit()
            return cursor.lastrowid
            
        except sqlite3.IntegrityError:
            # Статья уже существует
            return None
        finally:
            conn.close()
    
    def update_feed_info(self, feed_id, title=None, articles_count=None):
        """Обновление информации о фиде"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
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
        
        stats = cursor.fetchall()
        conn.close()
        return stats

    def mark_feed_as_parsed(self, feed_id):
        """Помечаем, что источник прошел первый парсинг"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Сначала добавляем колонку если её нет
        try:
            cursor.execute('ALTER TABLE feeds ADD COLUMN first_parse_done BOOLEAN DEFAULT 0')
        except sqlite3.OperationalError:
            pass  # Колонка уже существует
        
        cursor.execute('UPDATE feeds SET first_parse_done = 1 WHERE id = ?', (feed_id,))
        conn.commit()
        conn.close()
    
    def is_feed_first_parse(self, feed_id):
        """Проверяем, первый ли парсинг для источника"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Сначала добавляем колонку если её нет
        try:
            cursor.execute('ALTER TABLE feeds ADD COLUMN first_parse_done BOOLEAN DEFAULT 0')
        except sqlite3.OperationalError:
            pass  # Колонка уже существует
        
        cursor.execute('SELECT first_parse_done FROM feeds WHERE id = ?', (feed_id,))
        result = cursor.fetchone()
        conn.close()
        return result and result[0] == 0
    
    def get_total_articles_count(self):
        """Получаем общее количество статей"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM articles')
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    
    def cleanup_old_articles(self, days):
        """Удаление старых статей"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM articles 
            WHERE added_date < datetime('now', '-' || ? || ' days')
        ''', (days,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted_count
    def get_feed_by_url(self, url):
        """Получение информации о фиде по URL"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, url, title FROM feeds WHERE url = ?', (url,))
        feed = cursor.fetchone()
        conn.close()
        return feed
    
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
#!/usr/bin/env python3
"""
Просмотр базы данных RSS статей
Создает HTML файл для удобного просмотра в браузере
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

def export_database_to_html():
    """Экспорт базы данных в HTML для просмотра"""
    
    # Подключаемся к базе
    conn = sqlite3.connect('rss_media_bus.db')
    cursor = conn.cursor()
    
    # Получаем статистику
    cursor.execute("SELECT COUNT(*) FROM articles")
    total_articles = cursor.fetchone()[0]
    
    # Статистика по источникам
    cursor.execute("""
        SELECT feed_id, COUNT(*) as count 
        FROM articles 
        GROUP BY feed_id 
        ORDER BY count DESC
    """)
    source_stats = cursor.fetchall()
    
    # Последние статьи
    cursor.execute("""
        SELECT title, feed_id, link, description, 
               datetime(added_date) as date,
               datetime(published_date) as pub_date
        FROM articles 
        ORDER BY added_date DESC 
        LIMIT 100
    """)
    recent_articles = cursor.fetchall()
    
    # Создаем HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>RSS Media Bus - База данных статей</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background: #f5f5f5;
                line-height: 1.6;
            }}
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 2.5em;
                font-weight: 300;
            }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                padding: 30px;
                background: #f8f9fa;
            }}
            .stat-card {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                text-align: center;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .stat-number {{
                font-size: 2em;
                font-weight: bold;
                color: #667eea;
                margin-bottom: 5px;
            }}
            .stat-label {{
                color: #666;
                text-transform: uppercase;
                font-size: 0.8em;
                letter-spacing: 1px;
            }}
            .articles {{
                padding: 30px;
            }}
            .article {{
                border-bottom: 1px solid #eee;
                padding: 20px 0;
                transition: background 0.2s;
            }}
            .article:hover {{
                background: #f8f9fa;
                margin: 0 -20px;
                padding: 20px;
                border-radius: 5px;
            }}
            .article:last-child {{
                border-bottom: none;
            }}
            .article-title {{
                font-size: 1.2em;
                font-weight: 600;
                margin-bottom: 10px;
                color: #333;
            }}
            .article-title a {{
                color: #333;
                text-decoration: none;
            }}
            .article-title a:hover {{
                color: #667eea;
            }}
            .article-meta {{
                display: flex;
                gap: 15px;
                margin-bottom: 10px;
                font-size: 0.9em;
                color: #666;
            }}
            .source-tag {{
                background: #667eea;
                color: white;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 0.8em;
            }}
            .date {{
                color: #999;
            }}
            .description {{
                color: #666;
                line-height: 1.5;
            }}
            .search {{
                padding: 20px 30px;
                background: #f8f9fa;
                border-bottom: 1px solid #eee;
            }}
            .search input {{
                width: 100%;
                padding: 12px;
                border: 1px solid #ddd;
                border-radius: 6px;
                font-size: 1em;
            }}
            .filter-buttons {{
                margin-top: 15px;
                display: flex;
                gap: 10px;
                flex-wrap: wrap;
            }}
            .filter-btn {{
                background: #e9ecef;
                border: none;
                padding: 8px 16px;
                border-radius: 20px;
                cursor: pointer;
                transition: background 0.2s;
                font-size: 0.9em;
            }}
            .filter-btn:hover, .filter-btn.active {{
                background: #667eea;
                color: white;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📡 RSS Media Bus</h1>
                <p>База данных статей</p>
                <p style="opacity: 0.8;">Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
            </div>
            
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number">{total_articles}</div>
                    <div class="stat-label">Всего статей</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len(source_stats)}</div>
                    <div class="stat-label">Источников</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len([s for s in source_stats if s[0].endswith('.ru')])}</div>
                    <div class="stat-label">Доменных источников</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len([a for a in recent_articles if a[4] and '2025-07-19' in a[4]])}</div>
                    <div class="stat-label">Сегодня</div>
                </div>
            </div>
            
            <div class="search">
                <input type="text" id="searchInput" placeholder="🔍 Поиск по заголовкам и описаниям...">
                <div class="filter-buttons">
                    <button class="filter-btn active" onclick="filterBySource('all')">Все источники</button>"""
    
    # Добавляем кнопки фильтров по источникам
    for source, count in source_stats[:6]:  # Топ 6 источников
        source_name = source.replace('.ru', '').replace('_main', '').upper()
        html_content += f"""
                    <button class="filter-btn" onclick="filterBySource('{source}')">{source_name} ({count})</button>"""
    
    html_content += """
                </div>
            </div>
            
            <div class="articles" id="articlesContainer">"""
    
    # Добавляем статьи
    for article in recent_articles:
        title, feed_id, link, description, added_date, pub_date = article
        
        # Очищаем заголовок и описание
        title = title.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;') if title else 'Без заголовка'
        description = description.replace('<', '&lt;').replace('>', '&gt;') if description else ''
        
        # Сокращаем описание
        if description and len(description) > 300:
            description = description[:300] + '...'
        
        # Определяем отображаемое имя источника
        source_display = {
            'tass.ru': 'ТАСС',
            'ria.ru': 'РИА Новости', 
            'rbc.ru': 'РБК',
            'source': 'Смешанные источники'
        }.get(feed_id, feed_id)
        
        html_content += f"""
                <div class="article" data-source="{feed_id}">
                    <div class="article-title">
                        {f'<a href="{link}" target="_blank">{title}</a>' if link else title}
                    </div>
                    <div class="article-meta">
                        <span class="source-tag">{source_display}</span>
                        <span class="date">📅 {added_date or 'Не указана'}</span>
                        {f'<span class="date">📰 {pub_date}</span>' if pub_date else ''}
                    </div>
                    {f'<div class="description">{description}</div>' if description else ''}
                </div>"""
    
    html_content += """
            </div>
        </div>
        
        <script>
            // Поиск по статьям
            document.getElementById('searchInput').addEventListener('input', function(e) {
                const searchTerm = e.target.value.toLowerCase();
                const articles = document.querySelectorAll('.article');
                
                articles.forEach(article => {
                    const title = article.querySelector('.article-title').textContent.toLowerCase();
                    const description = article.querySelector('.description');
                    const descText = description ? description.textContent.toLowerCase() : '';
                    
                    if (title.includes(searchTerm) || descText.includes(searchTerm)) {
                        article.style.display = 'block';
                    } else {
                        article.style.display = 'none';
                    }
                });
            });
            
            // Фильтр по источникам
            function filterBySource(source) {
                const articles = document.querySelectorAll('.article');
                const buttons = document.querySelectorAll('.filter-btn');
                
                // Обновляем активную кнопку
                buttons.forEach(btn => btn.classList.remove('active'));
                event.target.classList.add('active');
                
                articles.forEach(article => {
                    if (source === 'all' || article.getAttribute('data-source') === source) {
                        article.style.display = 'block';
                    } else {
                        article.style.display = 'none';
                    }
                });
            }
        </script>
    </body>
    </html>"""
    
    # Сохраняем HTML файл
    with open('rss_database_view.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    conn.close()
    print("✅ HTML файл создан: rss_database_view.html")
    print("🌐 Откройте файл в браузере для просмотра базы данных")
    
    return total_articles, len(source_stats)

def export_database_to_json():
    """Экспорт базы данных в JSON"""
    conn = sqlite3.connect('rss_media_bus.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT title, feed_id, link, description, 
               datetime(added_date) as added_date,
               datetime(published_date) as published_date
        FROM articles 
        ORDER BY added_date DESC
    """)
    
    articles = []
    for row in cursor.fetchall():
        articles.append({
            'title': row[0],
            'source': row[1], 
            'link': row[2],
            'description': row[3],
            'added_date': row[4],
            'published_date': row[5]
        })
    
    with open('rss_database.json', 'w', encoding='utf-8') as f:
        json.dump({
            'total_articles': len(articles),
            'exported_at': datetime.now().isoformat(),
            'articles': articles
        }, f, ensure_ascii=False, indent=2)
    
    conn.close()
    print("✅ JSON файл создан: rss_database.json")
    return len(articles)

if __name__ == "__main__":
    print("📊 Экспорт базы данных RSS статей...")
    
    # Создаем HTML версию
    total_articles, total_sources = export_database_to_html()
    
    # Создаем JSON версию  
    json_articles = export_database_to_json()
    
    print(f"\n📈 Статистика:")
    print(f"├── Всего статей: {total_articles}")
    print(f"├── Источников: {total_sources}")
    print(f"└── Экспортировано в JSON: {json_articles}")
    
    print(f"\n📁 Созданные файлы:")
    print(f"├── rss_database_view.html (откройте в браузере)")
    print(f"└── rss_database.json (данные в JSON формате)") 
#!/usr/bin/env python3
"""
Долгосрочный мониторинг RSS источников
Ведет историю работы каждого источника и создает отчеты для анализа
"""

import json
import sqlite3
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from urllib.parse import urlparse

class LongTermMonitor:
    def __init__(self, instance_path='.'):
        self.instance_path = instance_path
        self.db_file = os.path.join(instance_path, 'source_monitoring.db')
        self.log_file = os.path.join(instance_path, 'monitor.log')
        self.feeds_file = os.path.join(instance_path, 'feeds.txt')
        self.report_file = os.path.join(instance_path, 'source_health_report.json')
        
        self.init_database()
        
    def init_database(self):
        """Создает базу данных для долгосрочного мониторинга"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Таблица для записи каждой попытки обращения к источнику
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS source_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL,  -- 'success', 'error', '404', 'timeout', etc.
                articles_found INTEGER DEFAULT 0,
                error_message TEXT,
                response_time REAL,
                attempt_number INTEGER DEFAULT 1
            )
        ''')
        
        # Таблица для ежедневной статистики по источникам
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url TEXT NOT NULL,
                date DATE NOT NULL,
                total_attempts INTEGER DEFAULT 0,
                successful_attempts INTEGER DEFAULT 0,
                error_attempts INTEGER DEFAULT 0,
                total_articles INTEGER DEFAULT 0,
                avg_response_time REAL,
                main_error_type TEXT,
                reliability_score REAL,  -- процент успешных попыток
                UNIQUE(source_url, date)
            )
        ''')
        
        # Таблица для источников и их конфигурации
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS source_config (
                source_url TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                first_seen DATE DEFAULT CURRENT_DATE,
                last_seen DATE DEFAULT CURRENT_DATE,
                notes TEXT  -- для записи ручных заметок
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def parse_current_logs(self, hours_back=24):
        """Парсит логи за указанное количество часов и записывает в БД"""
        print(f"📊 Анализ логов за последние {hours_back} часов...")
        
        if not os.path.exists(self.log_file):
            print("❌ Файл логов не найден")
            return
            
        # Читаем логи
        with open(self.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Анализируем строки
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        parsed_count = 0
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        for line in lines[-10000:]:  # Последние 10к строк
            # Парсим успешные запросы
            success_match = re.search(r'✅ (https?://[^\s:]+).*?(\d+) новых статей', line)
            if success_match:
                url, articles = success_match.groups()
                
                cursor.execute('''
                    INSERT INTO source_attempts 
                    (source_url, status, articles_found, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (url, 'success', int(articles), datetime.now()))
                parsed_count += 1
                
            # Парсим ошибки 404
            error_404_match = re.search(r'❌.*RSS.*404.*?(https?://[^\s]+)', line)
            if error_404_match:
                url = error_404_match.group(1)
                
                cursor.execute('''
                    INSERT INTO source_attempts 
                    (source_url, status, error_message, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (url, '404', 'RSS не найден (404)', datetime.now()))
                parsed_count += 1
                
            # Парсим таймауты
            timeout_match = re.search(r'⏰ Таймаут для (https?://[^\s]+)', line)
            if timeout_match:
                url = timeout_match.group(1)
                
                cursor.execute('''
                    INSERT INTO source_attempts 
                    (source_url, status, error_message, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (url, 'timeout', 'Превышен лимит времени', datetime.now()))
                parsed_count += 1
                
            # Парсим сетевые ошибки
            network_match = re.search(r'🌐 Сетевая ошибка (https?://[^\s]+)', line)
            if network_match:
                url = network_match.group(1)
                
                cursor.execute('''
                    INSERT INTO source_attempts 
                    (source_url, status, error_message, timestamp)
                    VALUES (?, ?, ?, ?)
                ''', (url, 'network_error', 'Сетевая ошибка', datetime.now()))
                parsed_count += 1
                
        conn.commit()
        conn.close()
        
        print(f"✅ Обработано {parsed_count} записей")
        
    def update_daily_stats(self):
        """Обновляет ежедневную статистику"""
        print("📈 Обновление ежедневной статистики...")
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Получаем статистику за сегодня
        today = datetime.now().date()
        
        cursor.execute('''
            SELECT 
                source_url,
                COUNT(*) as total_attempts,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN status != 'success' THEN 1 ELSE 0 END) as errors,
                SUM(articles_found) as total_articles,
                AVG(response_time) as avg_time
            FROM source_attempts 
            WHERE DATE(timestamp) = ?
            GROUP BY source_url
        ''', (today,))
        
        stats = cursor.fetchall()
        
        for stat in stats:
            url, total, successful, errors, articles, avg_time = stat
            
            reliability = (successful / total * 100) if total > 0 else 0
            
            # Определяем основной тип ошибки
            cursor.execute('''
                SELECT status, COUNT(*) as count
                FROM source_attempts 
                WHERE source_url = ? AND DATE(timestamp) = ? AND status != 'success'
                GROUP BY status
                ORDER BY count DESC
                LIMIT 1
            ''', (url, today))
            
            main_error_result = cursor.fetchone()
            main_error = main_error_result[0] if main_error_result else None
            
            # Вставляем или обновляем ежедневную статистику
            cursor.execute('''
                INSERT OR REPLACE INTO daily_stats 
                (source_url, date, total_attempts, successful_attempts, 
                 error_attempts, total_articles, avg_response_time, 
                 main_error_type, reliability_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (url, today, total, successful, errors, articles or 0, 
                  avg_time, main_error, reliability))
                  
        conn.commit()
        conn.close()
        
    def load_source_config(self):
        """Загружает конфигурацию источников из feeds.txt"""
        print("📋 Обновление конфигурации источников...")
        
        if not os.path.exists(self.feeds_file):
            return
            
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        with open(self.feeds_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('http'):
                    # Активный источник
                    domain = urlparse(line).netloc
                    cursor.execute('''
                        INSERT OR IGNORE INTO source_config (source_url, domain, is_active)
                        VALUES (?, ?, 1)
                    ''', (line, domain))
                    
                elif line.startswith('#') and 'http' in line:
                    # Отключенный источник
                    url_match = re.search(r'https?://[^\s]+', line)
                    if url_match:
                        url = url_match.group()
                        domain = urlparse(url).netloc
                        cursor.execute('''
                            INSERT OR IGNORE INTO source_config (source_url, domain, is_active)
                            VALUES (?, ?, 0)
                        ''', (url, domain))
                        
        conn.commit()
        conn.close()
        
    def generate_report(self, days_back=7):
        """Генерирует подробный отчет за указанный период"""
        print(f"📊 Генерация отчета за {days_back} дней...")
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Получаем общую статистику
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days_back)
        
        # Статистика по источникам за период
        cursor.execute('''
            SELECT 
                sc.source_url,
                sc.domain,
                sc.is_active,
                COUNT(ds.date) as days_with_data,
                AVG(ds.reliability_score) as avg_reliability,
                SUM(ds.successful_attempts) as total_success,
                SUM(ds.error_attempts) as total_errors,
                SUM(ds.total_articles) as total_articles,
                GROUP_CONCAT(DISTINCT ds.main_error_type) as error_types
            FROM source_config sc
            LEFT JOIN daily_stats ds ON sc.source_url = ds.source_url 
                AND ds.date BETWEEN ? AND ?
            GROUP BY sc.source_url
            ORDER BY avg_reliability DESC NULLS LAST
        ''', (start_date, end_date))
        
        sources_data = cursor.fetchall()
        
        # Анализируем каждый источник
        report = {
            'generated_at': datetime.now().isoformat(),
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days_back
            },
            'summary': {},
            'sources': {}
        }
        
        all_sources = []
        problematic_sources = []
        excellent_sources = []
        
        for row in sources_data:
            url, domain, is_active, days_data, avg_rel, success, errors, articles, error_types = row
            
            reliability = avg_rel if avg_rel is not None else 0
            total_attempts = (success or 0) + (errors or 0)
            
            # Классификация источника
            if reliability >= 90:
                status = "🟢 Отличный"
                category = "excellent"
                excellent_sources.append(url)
            elif reliability >= 70:
                status = "🟡 Хороший"
                category = "good"
            elif reliability >= 40:
                status = "🟠 Проблемный"
                category = "problematic"
                problematic_sources.append(url)
            else:
                status = "🔴 Критический"
                category = "critical"
                problematic_sources.append(url)
                
            # Рекомендации
            recommendations = []
            if not is_active:
                recommendations.append("⏸️ Источник отключен - возможно стоит переактивировать")
            elif reliability < 50:
                if '404' in (error_types or ''):
                    recommendations.append("🔧 Проверить актуальность URL - возможно RSS переехал")
                if 'timeout' in (error_types or ''):
                    recommendations.append("⚡ Увеличить timeout или добавить retry логику")
                if 'network_error' in (error_types or ''):
                    recommendations.append("🌐 Проблемы с сетью - возможно нужен прокси")
                    
            if not recommendations and reliability < 90:
                recommendations.append("🔍 Требует мониторинга")
            elif not recommendations:
                recommendations.append("✅ Работает стабильно")
                
            source_info = {
                'domain': domain,
                'is_active': bool(is_active),
                'status': status,
                'category': category,
                'reliability_score': round(reliability, 1),
                'days_monitored': days_data or 0,
                'total_attempts': total_attempts,
                'successful_attempts': success or 0,
                'error_attempts': errors or 0,
                'articles_found': articles or 0,
                'main_errors': error_types.split(',') if error_types else [],
                'recommendations': recommendations
            }
            
            report['sources'][url] = source_info
            all_sources.append(url)
            
        # Общая сводка
        report['summary'] = {
            'total_sources': len(all_sources),
            'excellent_sources': len(excellent_sources),
            'problematic_sources': len(problematic_sources),
            'avg_reliability': round(sum(s['reliability_score'] for s in report['sources'].values()) / len(all_sources), 1) if all_sources else 0
        }
        
        conn.close()
        
        # Сохраняем отчет
        with open(self.report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        return report
        
    def print_summary_report(self, days_back=7):
        """Выводит краткий отчет в консоль"""
        report = self.generate_report(days_back)
        
        print(f"\n📊 ОТЧЕТ ПО ИСТОЧНИКАМ за {days_back} дней")
        print("=" * 60)
        print(f"📅 Период: {report['period']['start_date']} → {report['period']['end_date']}")
        print(f"📡 Всего источников: {report['summary']['total_sources']}")
        print(f"🟢 Отличных: {report['summary']['excellent_sources']}")
        print(f"🔴 Проблемных: {report['summary']['problematic_sources']}")
        print(f"📈 Средняя надежность: {report['summary']['avg_reliability']}%")
        
        # Топ проблемных источников
        problematic = [(url, data) for url, data in report['sources'].items() 
                      if data['category'] in ['problematic', 'critical']]
        problematic.sort(key=lambda x: x[1]['reliability_score'])
        
        if problematic:
            print(f"\n⚠️ ТРЕБУЮТ ВНИМАНИЯ ({len(problematic)} источников):")
            print("-" * 60)
            for url, data in problematic[:10]:  # Топ-10 проблемных
                domain = data['domain'][:35]
                reliability = data['reliability_score']
                status = data['status']
                articles = data['articles_found']
                
                print(f"{status:<12} {domain:<35} {reliability:>5.1f}% ({articles} статей)")
                
                # Показываем рекомендации
                for rec in data['recommendations'][:2]:  # Первые 2 рекомендации
                    print(f"             → {rec}")
                print()
                
        print(f"\n💾 Полный отчет сохранен в: {self.report_file}")
        
    def run_full_analysis(self, hours_back=24, days_report=7):
        """Запускает полный анализ"""
        print("🚀 Запуск полного анализа источников...")
        
        self.parse_current_logs(hours_back)
        self.update_daily_stats()
        self.load_source_config()
        self.print_summary_report(days_report)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Долгосрочный мониторинг RSS источников')
    parser.add_argument('--path', default='.', help='Путь к экземпляру')
    parser.add_argument('--hours', type=int, default=24, help='Часов для анализа логов')
    parser.add_argument('--days', type=int, default=7, help='Дней для отчета')
    parser.add_argument('--report-only', action='store_true', help='Только показать отчет')
    
    args = parser.parse_args()
    
    monitor = LongTermMonitor(args.path)
    
    if args.report_only:
        monitor.print_summary_report(args.days)
    else:
        monitor.run_full_analysis(args.hours, args.days)

if __name__ == "__main__":
    main()
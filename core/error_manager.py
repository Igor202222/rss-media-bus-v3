#!/usr/bin/env python3
"""
RSS Media Bus - Централизованное управление ошибками источников
Специальная обработка 403 ошибок, логирование и статистика
"""

import time
import json
import logging
import aiohttp
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

class ErrorManager:
    def __init__(self, database_manager=None):
        self.db = database_manager
        self.error_counts = {}
        self.last_error_time = {}
        self.error_details = {}  # Детальная информация об ошибках
        
        # Настройка логирования ошибок
        self.error_log_file = Path("rss_errors.log")
        self.setup_error_logging()
        
        print("🛡️ Error Manager инициализирован")
    
    def setup_error_logging(self):
        """Настройка специального логгера для ошибок RSS"""
        self.error_logger = logging.getLogger('rss_errors')
        self.error_logger.setLevel(logging.INFO)
        
        # Файловый хандлер для ошибок
        file_handler = logging.FileHandler(self.error_log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Формат логов
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        if not self.error_logger.handlers:
            self.error_logger.addHandler(file_handler)
    
    def record_error(self, feed_url: str, feed_name: str, error_type: str, 
                    status_code: Optional[int] = None, error_message: str = ""):
        """Записать ошибку с детальной информацией"""
        
        # Увеличиваем счетчик
        self.error_counts[feed_url] = self.error_counts.get(feed_url, 0) + 1
        self.last_error_time[feed_url] = time.time()
        
        # Сохраняем детали
        if feed_url not in self.error_details:
            self.error_details[feed_url] = []
        
        error_detail = {
            'timestamp': datetime.now().isoformat(),
            'feed_name': feed_name,
            'error_type': error_type,
            'status_code': status_code,
            'error_message': error_message,
            'error_count': self.error_counts[feed_url]
        }
        
        self.error_details[feed_url].append(error_detail)
        
        # Ограничиваем историю последними 10 ошибками
        if len(self.error_details[feed_url]) > 10:
            self.error_details[feed_url] = self.error_details[feed_url][-10:]
        
        # Логируем
        log_msg = f"{feed_name} | {error_type}"
        if status_code:
            log_msg += f" | HTTP {status_code}"
        if error_message:
            log_msg += f" | {error_message}"
        log_msg += f" | Ошибок: {self.error_counts[feed_url]}"
        
        self.error_logger.error(log_msg)
        
        # Сохраняем в БД если доступна
        if self.db:
            self._save_error_to_db(feed_url, error_detail)
    
    def reset_errors(self, feed_url: str):
        """Сбросить ошибки при успешном запросе"""
        if feed_url in self.error_counts:
            count = self.error_counts[feed_url]
            del self.error_counts[feed_url]
            
            if count > 0:
                self.error_logger.info(f"{feed_url} | Восстановлен после {count} ошибок")
        
        if feed_url in self.last_error_time:
            del self.last_error_time[feed_url]
    
    def should_skip_feed(self, feed_url: str, max_errors: int = 5) -> Tuple[bool, str]:
        """
        Определить нужно ли пропустить источник
        Возвращает (should_skip, reason)
        """
        error_count = self.error_counts.get(feed_url, 0)
        
        if error_count >= max_errors:
            last_error = self.last_error_time.get(feed_url, 0)
            delay_minutes = min(60, 2 ** error_count)
            
            if time.time() - last_error < delay_minutes * 60:
                reason = f"Пропуск на {delay_minutes} мин (ошибок: {error_count})"
                return True, reason
        
        return False, ""
    
    def should_try_alternative_method(self, feed_url: str, status_code: int) -> str:
        """
        Определить альтернативный метод при специфических ошибках
        Возвращает рекомендацию: 'proxy', 'user_agent', 'both', 'none'
        """
        if status_code == 403:
            error_count = self.error_counts.get(feed_url, 0)
            
            # Первые 2 ошибки - пробуем User-Agent
            if error_count <= 2:
                return 'user_agent'
            # 3-4 ошибки - пробуем прокси  
            elif error_count <= 4:
                return 'proxy'
            # 5+ ошибок - пробуем и то и другое
            else:
                return 'both'
        
        elif status_code in [429, 503]:  # Rate limiting, Service unavailable
            return 'proxy'
        
        return 'none'
    
    def get_error_statistics(self) -> Dict:
        """Получить статистику ошибок"""
        stats = {
            'total_feeds_with_errors': len(self.error_counts),
            'total_errors': sum(self.error_counts.values()),
            'feeds': {}
        }
        
        for feed_url, count in self.error_counts.items():
            last_error = self.last_error_time.get(feed_url, 0)
            last_error_time = datetime.fromtimestamp(last_error) if last_error else None
            
            details = self.error_details.get(feed_url, [])
            latest_detail = details[-1] if details else {}
            
            stats['feeds'][feed_url] = {
                'error_count': count,
                'last_error_time': last_error_time.isoformat() if last_error_time else None,
                'last_error_type': latest_detail.get('error_type', 'unknown'),
                'last_status_code': latest_detail.get('status_code'),
                'feed_name': latest_detail.get('feed_name', 'Unknown'),
                'recent_errors': details[-3:] if len(details) >= 3 else details
            }
        
        return stats
    
    def _save_error_to_db(self, feed_url: str, error_detail: dict):
        """Сохранить ошибку в базу данных (если нужно)"""
        # TODO: Можно добавить сохранение в БД для персистентности
        pass
    
    def export_error_report(self, filepath: str = None) -> str:
        """Экспортировать отчет об ошибках в JSON"""
        if not filepath:
            filepath = f"error_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        stats = self.get_error_statistics()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2, default=str)
        
        return filepath 
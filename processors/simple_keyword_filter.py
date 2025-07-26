#!/usr/bin/env python3
"""
Простой фильтр ключевых слов для RSS Media Bus
Базовая фильтрация по вхождению подстроки
"""

import logging
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)

class SimpleKeywordFilter:
    """Простой фильтр по ключевым словам - точное вхождение подстроки"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Простая конфигурация:
        {
            "mode": "include|exclude|all",
            "keywords": ["слово1", "слово2"],
            "case_sensitive": false,
            "fields": ["title", "description"]
        }
        """
        self.mode = config.get('mode', 'all')
        self.keywords = config.get('keywords', [])
        self.case_sensitive = config.get('case_sensitive', False)
        self.fields = config.get('fields', ['title', 'description'])
        
        # Подготавливаем ключевые слова для поиска
        if not self.case_sensitive:
            self.keywords = [kw.lower() for kw in self.keywords]
        
        logger.info(f"🔍 SimpleKeywordFilter: режим={self.mode}, ключевых слов={len(self.keywords)}")
    
    def filter_article(self, article: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Фильтрует статью по простому правилу: есть ли ключевые слова в тексте
        
        Returns:
            should_send: bool - отправлять ли статью  
            metadata: dict - информация о совпадениях
        """
        
        # Режим "все новости" - без фильтрации
        if self.mode == 'all' or not self.keywords:
            return True, {
                'filter_mode': self.mode,
                'matched_keywords': [],
                'filter_reason': 'Все новости разрешены'
            }
        
        # Извлекаем текст из статьи
        text = self._extract_text(article)
        if not self.case_sensitive:
            text = text.lower()
        
        # Ищем совпадения ключевых слов
        matched_keywords = []
        for keyword in self.keywords:
            if keyword in text:  # Простое вхождение подстроки
                matched_keywords.append(keyword)
        
        # Метаданные для отладки
        metadata = {
            'filter_mode': self.mode,
            'matched_keywords': matched_keywords,
            'total_matches': len(matched_keywords)
        }
        
        # Применяем логику фильтрации
        if self.mode == 'include':
            # Включающий режим: пропускаем ТОЛЬКО статьи с ключевыми словами
            should_send = len(matched_keywords) > 0
            if should_send:
                metadata['filter_reason'] = f"Найдены слова: {', '.join(matched_keywords)}"
            else:
                metadata['filter_reason'] = "Ключевые слова не найдены"
                
        elif self.mode == 'exclude':
            # Исключающий режим: пропускаем статьи БЕЗ ключевых слов
            should_send = len(matched_keywords) == 0
            if should_send:
                metadata['filter_reason'] = "Исключающие слова не найдены"
            else:
                metadata['filter_reason'] = f"Исключено по словам: {', '.join(matched_keywords)}"
        
        else:
            # Неизвестный режим - по умолчанию пропускаем
            should_send = True
            metadata['filter_reason'] = f"Неизвестный режим: {self.mode}"
        
        return should_send, metadata
    
    def _extract_text(self, article: Dict[str, Any]) -> str:
        """Извлекает текст из указанных полей статьи"""
        text_parts = []
        
        for field in self.fields:
            if field in article and article[field]:
                text_parts.append(str(article[field]))
        
        return ' '.join(text_parts)

# Тестирование
if __name__ == "__main__":
    print("🧪 Тестирование SimpleKeywordFilter")
    
    # Тестовые статьи
    test_articles = [
        {
            'title': 'Подтверждено: новый закон принят',
            'description': 'Парламент подписал важный документ'
        },
        {
            'title': 'Экономические новости',
            'description': 'Из под полы вышла информация о росте'
        },
        {
            'title': 'Спортивные результаты',
            'description': 'Футбольная команда выиграла матч'
        }
    ]
    
    # Тест включающего фильтра
    include_config = {
        'mode': 'include',
        'keywords': ['под'],
        'case_sensitive': False,
        'fields': ['title', 'description']
    }
    
    include_filter = SimpleKeywordFilter(include_config)
    
    print("\n📊 Тест включающего фильтра (ключевое слово: 'под'):")
    for i, article in enumerate(test_articles, 1):
        should_send, metadata = include_filter.filter_article(article)
        status = "✅ ОТПРАВИТЬ" if should_send else "❌ ЗАБЛОКИРОВАТЬ"
        print(f"   {i}. '{article['title']}' → {status}")
        print(f"      Найдено: {metadata['matched_keywords']}")
        print(f"      Причина: {metadata['filter_reason']}")
    
    # Тест исключающего фильтра
    exclude_config = {
        'mode': 'exclude', 
        'keywords': ['спорт', 'футбол'],
        'case_sensitive': False
    }
    
    exclude_filter = SimpleKeywordFilter(exclude_config)
    
    print("\n📊 Тест исключающего фильтра (исключаем: 'спорт', 'футбол'):")
    for i, article in enumerate(test_articles, 1):
        should_send, metadata = exclude_filter.filter_article(article)
        status = "✅ ОТПРАВИТЬ" if should_send else "❌ ЗАБЛОКИРОВАТЬ"
        print(f"   {i}. '{article['title']}' → {status}")
        print(f"      Найдено: {metadata['matched_keywords']}")
        print(f"      Причина: {metadata['filter_reason']}") 
#!/usr/bin/env python3
"""
Advanced Keyword Filter для RSS Media Bus v3.1+
Продвинутая фильтрация статей по ключевым словам с множественными режимами
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class FilterMode(Enum):
    """Режимы фильтрации"""
    ALL = "all"                    # Все новости (без фильтрации)
    INCLUDE = "include"            # Включить статьи с ключевыми словами
    EXCLUDE = "exclude"            # Исключить статьи с ключевыми словами
    PRIORITY = "priority"          # Приоритетные + обычные (с пометками)
    SMART = "smart"                # Умная фильтрация (ML подобная)

class KeywordMatcher:
    """Продвинутый матчер ключевых слов"""
    
    def __init__(self, keywords: List[str], case_sensitive: bool = False):
        self.keywords = keywords
        self.case_sensitive = case_sensitive
        
        # Компилируем регексы для производительности
        self.compiled_patterns = []
        for keyword in keywords:
            # Поддержка wildcards: * и ?
            if '*' in keyword or '?' in keyword:
                regex_pattern = keyword.replace('*', '.*').replace('?', '.')
                flags = 0 if case_sensitive else re.IGNORECASE
                self.compiled_patterns.append(re.compile(regex_pattern, flags))
            else:
                # Простое совпадение слов (границы слов)
                escaped = re.escape(keyword)
                pattern = r'\b' + escaped + r'\b'
                flags = 0 if case_sensitive else re.IGNORECASE
                self.compiled_patterns.append(re.compile(pattern, flags))
    
    def find_matches(self, text: str) -> List[Tuple[str, int]]:
        """Находит совпадения и возвращает (keyword, count) для каждого"""
        matches = []
        text_to_search = text if self.case_sensitive else text.lower()
        
        for i, pattern in enumerate(self.compiled_patterns):
            keyword = self.keywords[i]
            found_matches = pattern.findall(text_to_search)
            if found_matches:
                matches.append((keyword, len(found_matches)))
        
        return matches
    
    def get_match_score(self, text: str) -> int:
        """Возвращает общий счет совпадений"""
        matches = self.find_matches(text)
        return sum(count for _, count in matches)

class AdvancedKeywordFilter:
    """Продвинутый фильтр по ключевым словам"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        config format:
        {
            "mode": "include|exclude|priority|smart|all",
            "keywords": ["keyword1", "keyword2"],
            "min_matches": 1,
            "case_sensitive": false,
            "fields": ["title", "description", "content"],
            "priority_keywords": ["urgent", "breaking"],
            "exclude_keywords": ["spam", "advertisement"],
            "smart_categories": ["politics", "economy"],
            "boost_multiplier": 2.0
        }
        """
        self.mode = FilterMode(config.get('mode', 'all'))
        self.keywords = config.get('keywords', [])
        self.min_matches = config.get('min_matches', 1)
        self.case_sensitive = config.get('case_sensitive', False)
        self.fields = config.get('fields', ['title', 'description'])
        
        # Продвинутые настройки
        self.priority_keywords = config.get('priority_keywords', [])
        self.exclude_keywords = config.get('exclude_keywords', [])
        self.smart_categories = config.get('smart_categories', [])
        self.boost_multiplier = config.get('boost_multiplier', 2.0)
        
        # Создаем матчеры
        self.main_matcher = KeywordMatcher(self.keywords, self.case_sensitive) if self.keywords else None
        self.priority_matcher = KeywordMatcher(self.priority_keywords, self.case_sensitive) if self.priority_keywords else None
        self.exclude_matcher = KeywordMatcher(self.exclude_keywords, self.case_sensitive) if self.exclude_keywords else None
        
        logger.info(f"🔍 AdvancedKeywordFilter создан: режим={self.mode.value}, keywords={len(self.keywords)}")
    
    def filter_article(self, article: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Фильтрует статью и возвращает (should_send, metadata)
        
        Returns:
            should_send: bool - отправлять ли статью
            metadata: dict - метаданные фильтрации (совпадения, приоритет и т.д.)
        """
        
        # Извлекаем текст для анализа
        article_text = self._extract_text(article)
        
        # Базовые метаданные
        metadata = {
            'filter_mode': self.mode.value,
            'matched_keywords': [],
            'priority_keywords': [],
            'excluded_keywords': [],
            'match_score': 0,
            'is_priority': False,
            'filter_reason': ''
        }
        
        # Проверяем исключающие ключевые слова
        if self.exclude_matcher:
            exclude_matches = self.exclude_matcher.find_matches(article_text)
            if exclude_matches:
                metadata['excluded_keywords'] = [kw for kw, _ in exclude_matches]
                metadata['filter_reason'] = f"Исключено по ключевым словам: {', '.join(metadata['excluded_keywords'])}"
                return False, metadata
        
        # Основная логика фильтрации
        if self.mode == FilterMode.ALL:
            metadata['filter_reason'] = "Режим: все новости"
            return True, metadata
        
        elif self.mode == FilterMode.INCLUDE:
            return self._filter_include_mode(article_text, metadata)
        
        elif self.mode == FilterMode.EXCLUDE:
            return self._filter_exclude_mode(article_text, metadata)
        
        elif self.mode == FilterMode.PRIORITY:
            return self._filter_priority_mode(article_text, metadata)
        
        elif self.mode == FilterMode.SMART:
            return self._filter_smart_mode(article, article_text, metadata)
        
        else:
            metadata['filter_reason'] = "Неизвестный режим фильтрации"
            return True, metadata
    
    def _extract_text(self, article: Dict[str, Any]) -> str:
        """Извлекает текст из указанных полей статьи"""
        text_parts = []
        
        for field in self.fields:
            if field in article and article[field]:
                text_parts.append(str(article[field]))
        
        return ' '.join(text_parts)
    
    def _filter_include_mode(self, text: str, metadata: Dict) -> Tuple[bool, Dict]:
        """Режим включения: статья проходит если есть ключевые слова"""
        if not self.main_matcher:
            metadata['filter_reason'] = "Нет ключевых слов для включения"
            return True, metadata
        
        matches = self.main_matcher.find_matches(text)
        total_matches = sum(count for _, count in matches)
        
        metadata['matched_keywords'] = [kw for kw, _ in matches]
        metadata['match_score'] = total_matches
        
        if total_matches >= self.min_matches:
            metadata['filter_reason'] = f"Найдено {total_matches} совпадений: {', '.join(metadata['matched_keywords'])}"
            return True, metadata
        else:
            metadata['filter_reason'] = f"Недостаточно совпадений: {total_matches} < {self.min_matches}"
            return False, metadata
    
    def _filter_exclude_mode(self, text: str, metadata: Dict) -> Tuple[bool, Dict]:
        """Режим исключения: статья НЕ проходит если есть ключевые слова"""
        if not self.main_matcher:
            metadata['filter_reason'] = "Нет ключевых слов для исключения"
            return True, metadata
        
        matches = self.main_matcher.find_matches(text)
        total_matches = sum(count for _, count in matches)
        
        metadata['matched_keywords'] = [kw for kw, _ in matches]
        metadata['match_score'] = total_matches
        
        if total_matches >= self.min_matches:
            metadata['filter_reason'] = f"Исключено по {total_matches} совпадениям: {', '.join(metadata['matched_keywords'])}"
            return False, metadata
        else:
            metadata['filter_reason'] = f"Нет исключающих совпадений"
            return True, metadata
    
    def _filter_priority_mode(self, text: str, metadata: Dict) -> Tuple[bool, Dict]:
        """Режим приоритета: приоритетные статьи + обычные с пометками"""
        # Проверяем приоритетные ключевые слова
        priority_matches = []
        if self.priority_matcher:
            priority_matches = self.priority_matcher.find_matches(text)
            metadata['priority_keywords'] = [kw for kw, _ in priority_matches]
            metadata['is_priority'] = len(priority_matches) > 0
        
        # Проверяем обычные ключевые слова
        regular_matches = []
        if self.main_matcher:
            regular_matches = self.main_matcher.find_matches(text)
            metadata['matched_keywords'] = [kw for kw, _ in regular_matches]
        
        total_priority = sum(count for _, count in priority_matches)
        total_regular = sum(count for _, count in regular_matches)
        
        # Boost для приоритетных
        metadata['match_score'] = total_regular + (total_priority * self.boost_multiplier)
        
        # Пропускаем если есть приоритетные ИЛИ достаточно обычных
        if total_priority > 0:
            metadata['filter_reason'] = f"Приоритетные совпадения: {', '.join(metadata['priority_keywords'])}"
            return True, metadata
        elif total_regular >= self.min_matches:
            metadata['filter_reason'] = f"Обычные совпадения: {', '.join(metadata['matched_keywords'])}"
            return True, metadata
        else:
            metadata['filter_reason'] = f"Недостаточно совпадений: {total_regular} обычных, {total_priority} приоритетных"
            return False, metadata
    
    def _filter_smart_mode(self, article: Dict, text: str, metadata: Dict) -> Tuple[bool, Dict]:
        """Умная фильтрация с учетом категорий, источников и контекста"""
        score = 0
        reasons = []
        
        # 1. Обычные ключевые слова
        if self.main_matcher:
            matches = self.main_matcher.find_matches(text)
            keyword_score = sum(count for _, count in matches)
            score += keyword_score
            if matches:
                reasons.append(f"keywords: {keyword_score}")
                metadata['matched_keywords'] = [kw for kw, _ in matches]
        
        # 2. Приоритетные ключевые слова
        if self.priority_matcher:
            priority_matches = self.priority_matcher.find_matches(text)
            priority_score = sum(count for _, count in priority_matches) * self.boost_multiplier
            score += priority_score
            if priority_matches:
                reasons.append(f"priority: {priority_score}")
                metadata['priority_keywords'] = [kw for kw, _ in priority_matches]
                metadata['is_priority'] = True
        
        # 3. Категории статьи
        article_category = article.get('category', '').lower()
        if article_category in [cat.lower() for cat in self.smart_categories]:
            score += 5
            reasons.append(f"category: {article_category}")
        
        # 4. Источник статьи (некоторые источники могут быть приоритетными)
        source_id = article.get('feed_id', '')
        if source_id in ['tass.ru', 'ria.ru', 'reuters.com']:  # Приоритетные источники
            score += 2
            reasons.append(f"priority_source: {source_id}")
        
        # 5. Время публикации (свежие новости важнее)
        pub_date = article.get('published_date')
        if pub_date:
            hours_old = (datetime.now() - pub_date).total_seconds() / 3600
            if hours_old < 1:  # Менее часа
                score += 3
                reasons.append("fresh")
            elif hours_old < 6:  # Менее 6 часов
                score += 1
                reasons.append("recent")
        
        metadata['match_score'] = score
        metadata['filter_reason'] = f"Smart score: {score} ({', '.join(reasons)})"
        
        # Умный порог зависит от наличия приоритетных совпадений
        threshold = 3 if metadata.get('is_priority') else max(self.min_matches, 5)
        
        return score >= threshold, metadata

class FilterProcessor:
    """Процессор для интеграции с User Notification Service"""
    
    def __init__(self, filter_configs: Dict[str, Dict[str, Any]]):
        """
        filter_configs: Dict[config_id, filter_config]
        Создает отдельные фильтры для каждой telegram_config
        """
        self.filters = {}
        
        for config_id, filter_config in filter_configs.items():
            if filter_config:  # Если есть настройки фильтрации
                self.filters[config_id] = AdvancedKeywordFilter(filter_config)
                logger.info(f"✅ Фильтр создан для конфигурации {config_id}")
            else:
                # Нет фильтра = пропускаем все
                self.filters[config_id] = None
                logger.info(f"📤 Конфигурация {config_id} без фильтрации (все статьи)")
    
    def should_send_to_config(self, article: Dict[str, Any], config_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Проверяет нужно ли отправлять статью в конкретную конфигурацию"""
        if config_id not in self.filters:
            # Неизвестная конфигурация - по умолчанию отправляем
            return True, {'filter_reason': 'No filter configured'}
        
        filter_instance = self.filters[config_id]
        if filter_instance is None:
            # Нет фильтра для этой конфигурации - отправляем все
            return True, {'filter_reason': 'All articles mode'}
        
        # Применяем фильтр
        return filter_instance.filter_article(article)

# Утилиты для создания конфигураций
def create_simple_keyword_filter(keywords: List[str], mode: str = "include") -> Dict[str, Any]:
    """Создает простую конфигурацию фильтра"""
    return {
        "mode": mode,
        "keywords": keywords,
        "min_matches": 1,
        "case_sensitive": False,
        "fields": ["title", "description"]
    }

def create_priority_filter(normal_keywords: List[str], priority_keywords: List[str]) -> Dict[str, Any]:
    """Создает конфигурацию приоритетного фильтра"""
    return {
        "mode": "priority",
        "keywords": normal_keywords,
        "priority_keywords": priority_keywords,
        "min_matches": 1,
        "case_sensitive": False,
        "fields": ["title", "description", "content"],
        "boost_multiplier": 3.0
    }

def create_smart_filter(categories: List[str], keywords: List[str] = None) -> Dict[str, Any]:
    """Создает конфигурацию умного фильтра"""
    return {
        "mode": "smart",
        "keywords": keywords or [],
        "smart_categories": categories,
        "min_matches": 2,
        "case_sensitive": False,
        "fields": ["title", "description", "content"],
        "boost_multiplier": 2.5
    }

# Тестирование
if __name__ == "__main__":
    print("🧪 Тестирование AdvancedKeywordFilter")
    
    # Тестовая статья
    test_article = {
        'title': 'Срочно: Новый закон о цифровой экономике принят',
        'description': 'Парламент принял важный закон о развитии цифровых технологий и блокчейн',
        'content': 'Подробности законопроекта включают регулирование криптовалют и NFT',
        'category': 'politics',
        'feed_id': 'tass.ru',
        'published_date': datetime.now()
    }
    
    # Тест простого фильтра
    simple_config = create_simple_keyword_filter(['срочно', 'важный', 'закон'], 'include')
    simple_filter = AdvancedKeywordFilter(simple_config)
    
    should_send, metadata = simple_filter.filter_article(test_article)
    print(f"📊 Простой фильтр: {should_send}")
    print(f"   Причина: {metadata['filter_reason']}")
    print(f"   Совпадения: {metadata['matched_keywords']}")
    
    # Тест приоритетного фильтра
    priority_config = create_priority_filter(['закон', 'экономика'], ['срочно', 'важный'])
    priority_filter = AdvancedKeywordFilter(priority_config)
    
    should_send, metadata = priority_filter.filter_article(test_article)
    print(f"📊 Приоритетный фильтр: {should_send}")
    print(f"   Причина: {metadata['filter_reason']}")
    print(f"   Приоритетные: {metadata['priority_keywords']}")
    print(f"   Обычные: {metadata['matched_keywords']}")
    
    # Тест умного фильтра
    smart_config = create_smart_filter(['politics', 'economy'], ['цифровой', 'технологии'])
    smart_filter = AdvancedKeywordFilter(smart_config)
    
    should_send, metadata = smart_filter.filter_article(test_article)
    print(f"📊 Умный фильтр: {should_send}")
    print(f"   Причина: {metadata['filter_reason']}")
    print(f"   Счет: {metadata['match_score']}")
    print(f"   Приоритет: {metadata['is_priority']}") 
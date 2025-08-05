# core/translator.py
import aiohttp
import asyncio
import json
import logging
from typing import Optional, Dict, Any
import re

class AutoTranslator:
    """Автоматический переводчик для RSS статей"""
    
    def __init__(self, config: Dict[str, Any]):
        self.enabled = config.get('enabled', False)
        self.provider = config.get('provider', 'yandex')
        self.source_lang = config.get('source_lang', 'auto')
        self.target_lang = config.get('target_lang', 'ru')
        self.fields_to_translate = config.get('fields', ['title', 'description'])
        
        self.session = None
        # ВАЖНО: Logger инициализируем ДО вызова _load_api_key
        self.logger = logging.getLogger(__name__)
        
        # Семафор для ограничения одновременных запросов (избегаем перегрузки API)
        self.semaphore = asyncio.Semaphore(1)  # Только 1 запрос одновременно
        
        # Теперь можем загружать API ключ (logger уже есть)
        self.api_key = self._load_api_key(config.get('api_key'))
        
        # Счетчики для статистики
        self.translated_count = 0
        self.skipped_count = 0
        self.error_count = 0
    
    def _load_api_key(self, config_api_key: Optional[str]) -> Optional[str]:
        """Загружает API ключ из config/api_keys.yaml или из конфига"""
        # Если ключ указан в конфиге напрямую - используем его
        if config_api_key:
            return config_api_key
        
        # Иначе читаем из файла api_keys.yaml
        try:
            import yaml
            from pathlib import Path
            
            api_keys_file = Path("config/api_keys.yaml")
            if api_keys_file.exists():
                with open(api_keys_file, 'r') as f:
                    api_config = yaml.safe_load(f)
                
                provider_config = api_config.get('translation_apis', {}).get(self.provider, {})
                if provider_config.get('enabled'):
                    api_key = provider_config.get('api_key')
                    if api_key:
                        self.logger.info(f"API ключ для {self.provider} загружен из config/api_keys.yaml")
                        return api_key
            
            self.logger.warning(f"API ключ для {self.provider} не найден в config/api_keys.yaml")
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки API ключа: {e}")
            return None
    
    async def __aenter__(self):
        if self.enabled:
            # Добавляем aggressive timeout чтобы избежать зависаний
            timeout = aiohttp.ClientTimeout(total=5, connect=2)  # 5 сек общий, 2 сек на подключение
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def translate_article(self, article: Dict[str, Any]) -> Dict[str, Any]:
        """Переводит указанные поля статьи"""
        if not self.enabled:
            return article
        
        # Определяем нужно ли переводить
        if not self._needs_translation(article):
            self.skipped_count += 1
            self.logger.debug(f"Skipping translation for Russian source: {article.get('feed_id')}")
            return article
        
        translated_article = article.copy()
        translated_fields = []
        
        for field in self.fields_to_translate:
            if field in article and article[field]:
                try:
                    original_text = article[field]
                    translated_text = await self._translate_text(original_text)
                    
                    if translated_text and translated_text != original_text:
                        # Сохраняем оригинал и перевод
                        translated_article[f'{field}_original'] = original_text
                        translated_article[field] = translated_text
                        translated_fields.append(field)
                        
                except Exception as e:
                    self.error_count += 1
                    self.logger.error(f"Translation error for field {field}: {e}")
                    # Продолжаем с оригинальным текстом
        
        if translated_fields:
            self.translated_count += 1
            self.logger.info(f"Translated article '{article.get('title', 'N/A')[:50]}...' fields: {translated_fields}")
        
        return translated_article
    
    def _needs_translation(self, article: Dict[str, Any]) -> bool:
        """Определяет нужно ли переводить статью"""
        feed_id = article.get('feed_id', '')
        
        # Русские источники не переводим (проверяем по feed_id)
        russian_sources = ['habr', 'vc.ru', 'tass.ru', 'ria.ru', 'rbc.ru', 'lenta.ru']
        if any(source in feed_id.lower() for source in russian_sources):
            self.logger.debug(f"Skipping Russian source: {feed_id}")
            return False
        
        # Если источник НЕ русский - проверяем содержит ли текст кириллицу
        title = article.get('title', '')
        description = article.get('description', '')
        combined_text = f"{title} {description}"
        
        if self._has_cyrillic(combined_text):
            self.logger.debug(f"Skipping article with Cyrillic text: {title[:30]}...")
            return False
        
        # Если источник не русский И нет кириллицы - переводим
        self.logger.debug(f"Will translate: {feed_id} - {title[:30]}...")
        return True
    
    def _has_cyrillic(self, text: str) -> bool:
        """Проверяет есть ли в тексте кириллица"""
        if not text:
            return False
        cyrillic_chars = len(re.findall(r'[а-яё]', text.lower()))
        return cyrillic_chars > len(text) * 0.1  # Если больше 10% кириллицы
    
    async def _translate_text(self, text: str) -> Optional[str]:
        """Переводит текст через выбранный API"""
        if not text or len(text.strip()) < 3:
            return text
            
        if self.provider == 'yandex':
            return await self._translate_yandex(text)
        elif self.provider == 'google':
            return await self._translate_google(text)
        else:
            self.logger.error(f"Unknown translation provider: {self.provider}")
            return text
    
    async def _translate_yandex(self, text: str) -> Optional[str]:
        """Yandex Translate API"""
        if not self.api_key:
            self.logger.error("Yandex API key not provided")
            return text
            
        url = "https://translate.api.cloud.yandex.net/translate/v2/translate"
        
        headers = {
            'Authorization': f'Api-Key {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'texts': [text],
            'targetLanguageCode': self.target_lang,
            'sourceLanguageCode': self.source_lang if self.source_lang != 'auto' else 'en'
        }
        
        async with self.semaphore:  # Ограничиваем одновременные запросы
            try:
                async with self.session.post(url, headers=headers, json=data, timeout=10) as response:
                    if response.status == 200:
                        result = await response.json()
                        translated = result['translations'][0]['text']
                        self.logger.debug(f"Yandex translation: '{text[:30]}...' -> '{translated[:30]}...'")
                        return translated
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Yandex Translate API error {response.status}: {error_text}")
                        return text
            except asyncio.TimeoutError:
                self.logger.error("Yandex Translate timeout")
                return text
            except Exception as e:
                self.logger.error(f"Yandex Translate request error: {e}")
                return text
    
    async def _translate_google(self, text: str) -> Optional[str]:
        """Google Translate API"""
        if not self.api_key:
            self.logger.error("Google API key not provided")
            return text
            
        url = "https://translation.googleapis.com/language/translate/v2"
        
        params = {
            'key': self.api_key,
            'q': text,
            'target': self.target_lang,
            'source': self.source_lang,
            'format': 'text'
        }
        
        try:
            async with self.session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    translated = data['data']['translations'][0]['translatedText']
                    self.logger.debug(f"Google translation: '{text[:30]}...' -> '{translated[:30]}...'")
                    return translated
                else:
                    error_text = await response.text()
                    self.logger.error(f"Google Translate API error {response.status}: {error_text}")
                    return text
        except asyncio.TimeoutError:
            self.logger.error("Google Translate timeout")
            return text
        except Exception as e:
            self.logger.error(f"Google Translate request error: {e}")
            return text
    
    def get_stats(self) -> Dict[str, int]:
        """Возвращает статистику переводов"""
        return {
            'translated': self.translated_count,
            'skipped': self.skipped_count,
            'errors': self.error_count
        }
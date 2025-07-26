import requests
import json
import time
import re
import html
from config import REQUEST_TIMEOUT

class TelegramSender:
    def __init__(self, bot_token, chat_id, topic_id=None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.topic_id = topic_id  # ID топика для отправки сообщений
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def test_connection(self):
        """Тест соединения с Telegram API"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                bot_info = response.json()
                print(f"✅ Подключение к боту: {bot_info['result']['first_name']}")
                
                # Проверяем поддержку топиков если указан topic_id
                if self.topic_id:
                    print(f"📱 Настроен топик: {self.topic_id}")
                
                return True
            else:
                print(f"❌ Ошибка API: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка соединения: {e}")
            return False
    
    def send_message(self, text, topic_id=None, parse_mode=None):
        """
        Отправка сообщения в Telegram с оптимальной обработкой rate limiting
        
        Args:
            text: Текст сообщения
            topic_id: ID топика (переопределяет self.topic_id)
            parse_mode: Режим парсинга ('HTML', 'Markdown' или None)
        """
        max_retries = 2  # Уменьшаем количество попыток
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                url = f"{self.base_url}/sendMessage"
                
                data = {
                    "chat_id": self.chat_id,
                    "text": text,
                    "disable_web_page_preview": True
                }
                
                # Режим парсинга
                if parse_mode:
                    data["parse_mode"] = parse_mode
                
                # Определяем ID топика (приоритет у параметра)
                target_topic_id = topic_id if topic_id is not None else self.topic_id
                
                if target_topic_id:
                    data["message_thread_id"] = target_topic_id
                    print(f"📱 Отправка в топик {target_topic_id}")
                
                response = requests.post(url, json=data, timeout=REQUEST_TIMEOUT)
                
                if response.status_code == 200:
                    return True
                elif response.status_code == 429:
                    # Rate limiting - получаем точное время ожидания от Telegram
                    error_info = response.json()
                    retry_after = error_info.get('parameters', {}).get('retry_after', 10)
                    
                    print(f"⏳ Rate limit #{retry_count + 1}. Ожидание {retry_after} секунд...")
                    time.sleep(retry_after)  # Ждем точно столько, сколько говорит Telegram
                    
                    retry_count += 1
                    continue
                else:
                    error_info = response.json()
                    error_description = error_info.get('description', 'Неизвестная ошибка')
                    
                    # Специальная обработка ошибок топиков
                    if 'message thread not found' in error_description.lower():
                        print(f"❌ Топик {target_topic_id} не найден, отправляю в общий чат")
                        # Повторяем без топика
                        data.pop('message_thread_id', None)
                        response = requests.post(url, json=data, timeout=REQUEST_TIMEOUT)
                        return response.status_code == 200
                    
                    print(f"❌ Ошибка отправки: {error_description}")
                    return False
                    
            except Exception as e:
                print(f"❌ Ошибка отправки сообщения (попытка {retry_count + 1}): {e}")
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(2)  # Короткая задержка при сетевых ошибках
                    
        print(f"❌ Не удалось отправить сообщение после {max_retries} попыток")
        return False
    
    def send_article(self, title, link, description, keywords, categories, source, topic_id=None, article_data=None):
        """Отправка статьи в упрощенном формате: заголовок + полное описание + теги"""
        try:
            message_parts = []
            
            # 1. ЗАГОЛОВОК (жирным)
            message_parts.append(f"<b>{title}</b>")
            message_parts.append("")  # Пустая строка
            
            # 2. ПОЛНОЕ ОПИСАНИЕ из RSS (без сокращений)
            if description:
                # Очищаем HTML теги и декодируем HTML-сущности
                clean_description = re.sub(r'<[^>]+>', '', description)
                
                # Декодируем HTML-сущности (&mdash; → —, &laquo; → «, etc)
                clean_description = html.unescape(clean_description)
                
                # Дополнительная очистка
                clean_description = clean_description.replace('[continued]', '')
                clean_description = clean_description.strip()
                
                if clean_description:
                    message_parts.append(clean_description)
                    message_parts.append("")  # Пустая строка
            
            # 3. ТЕГИ (все категории)
            if categories:
                tags_str = " ".join([f"#{cat.replace(' ', '_').replace('&', 'and')}" for cat in categories])
                message_parts.append(f"🏷️ {tags_str}")
            else:
                message_parts.append("🏷️ #без_категории")
            
            # 4. ССЫЛКА на материал
            if link:
                message_parts.append("")  # Пустая строка
                message_parts.append(f"🔗 {link}")
            
            # Собираем финальное сообщение
            message = "\n".join(message_parts)
            
            return self.send_message(message, topic_id=topic_id, parse_mode='HTML')
            
        except Exception as e:
            print(f"❌ Ошибка формирования сообщения: {e}")
            return False    
    
    def send_test_message(self, topic_id=None):
        """Отправка тестового сообщения"""
        test_message = """🧪 <b>Тест RSS мониторинга</b>

✅ Система мониторинга СМИ запущена
🔍 Универсальная архитектура v2.0
📊 AsyncRSSParser активен
📱 Отправка в Telegram работает

<i>Сообщение отправлено автоматически</i>"""
        
        return self.send_message(test_message, topic_id=topic_id, parse_mode='HTML')
    
    def send_status_update(self, feeds_count, new_articles, keywords_count, monitor_name=None, topic_id=None):
        """Отправка статуса обновления"""
        monitor_name = monitor_name or "RSS Monitor"
        
        message = f"""📊 <b>Статус обновления</b>

🎯 Система: {monitor_name}
📡 Источников проверено: {feeds_count}
📝 Новых статей найдено: {new_articles}
🔍 Ключевых слов: {keywords_count}

⏰ {time.strftime('%d.%m.%Y %H:%M')}"""
        
        return self.send_message(message, topic_id=topic_id, parse_mode='HTML')
    
    def send_error_alert(self, error_message, component="RSS Monitor", topic_id=None):
        """Отправка алерта об ошибке"""
        alert_message = f"""🚨 <b>Алерт мониторинга</b>

❌ Компонент: {component}
📝 Ошибка: {error_message}

⏰ {time.strftime('%d.%m.%Y %H:%M')}

<i>Требуется проверка системы</i>"""
        
        return self.send_message(alert_message, topic_id=topic_id, parse_mode='HTML')
    
    def get_topic_info(self, topic_id):
        """Получение информации о топике (для диагностики)"""
        try:
            # Это API метод недоступен в обычных ботах, но можем попробовать
            url = f"{self.base_url}/getForumTopics"
            data = {"chat_id": self.chat_id}
            
            response = requests.post(url, json=data, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    topics = result.get('result', {}).get('topics', [])
                    for topic in topics:
                        if topic.get('message_thread_id') == topic_id:
                            return topic
            
            return None
            
        except Exception as e:
            print(f"⚠️ Не удалось получить информацию о топике: {e}")
            return None
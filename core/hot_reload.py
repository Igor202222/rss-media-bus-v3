#!/usr/bin/env python3
"""
Hot Reload система для RSS Media Bus v3.1
Поддержка перезагрузки sources.yaml и users.yaml без остановки процессов
"""

import signal
import yaml
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Callable, Optional

logger = logging.getLogger(__name__)

class HotReloadManager:
    """Менеджер горячей перезагрузки конфигурации"""
    
    def __init__(self, process_name: str = "unknown"):
        self.process_name = process_name
        self.config_dir = Path("config")
        
        # Коллбеки для перезагрузки
        self.reload_callbacks: Dict[str, List[Callable]] = {
            'sources': [],
            'users': [],
            'topics': []
        }
        
        # Последние времена загрузки файлов
        self.last_modified = {}
        
        # Флаги состояния
        self.reload_in_progress = False
        
        logger.info(f"🔄 HotReloadManager инициализирован для процесса: {process_name}")
    
    def register_callback(self, config_type: str, callback: Callable):
        """Регистрация callback'а для типа конфигурации"""
        if config_type in self.reload_callbacks:
            self.reload_callbacks[config_type].append(callback)
            logger.info(f"📋 Зарегистрирован callback для {config_type} в {self.process_name}")
        else:
            logger.warning(f"⚠️ Неизвестный тип конфигурации: {config_type}")
    
    def setup_signal_handlers(self):
        """Настройка обработчиков сигналов"""
        # USR1 - перезагрузка источников (sources.yaml)
        signal.signal(signal.SIGUSR1, self._handle_sources_reload)
        
        # USR2 - перезагрузка пользователей (users.yaml)
        signal.signal(signal.SIGUSR2, self._handle_users_reload)
        
        logger.info(f"🔔 Обработчики сигналов настроены для {self.process_name}")
        logger.info(f"   USR1 - перезагрузка sources.yaml")
        logger.info(f"   USR2 - перезагрузка users.yaml")
    
    def _handle_sources_reload(self, signum, frame):
        """Обработчик сигнала USR1 - перезагрузка источников"""
        logger.info(f"🔄 Получен сигнал USR1 - перезагрузка sources.yaml")
        asyncio.create_task(self._reload_sources())
    
    def _handle_users_reload(self, signum, frame):
        """Обработчик сигнала USR2 - перезагрузка пользователей"""
        logger.info(f"🔄 Получен сигнал USR2 - перезагрузка users.yaml")
        asyncio.create_task(self._reload_users())
    
    async def _reload_sources(self):
        """Асинхронная перезагрузка источников"""
        if self.reload_in_progress:
            logger.warning("⚠️ Перезагрузка уже в процессе, пропускаем")
            return
        
        try:
            self.reload_in_progress = True
            logger.info("🔄 Начинаем перезагрузку sources.yaml...")
            
            # Загружаем новую конфигурацию
            sources_file = self.config_dir / "sources.yaml"
            with open(sources_file, 'r', encoding='utf-8') as f:
                sources_config = yaml.safe_load(f)
                sources = sources_config.get('sources', {})
            
            logger.info(f"📡 Загружено источников: {len(sources)}")
            
            # Вызываем все зарегистрированные callbacks
            for callback in self.reload_callbacks['sources']:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(sources)
                    else:
                        callback(sources)
                    logger.info("✅ Callback выполнен успешно")
                except Exception as e:
                    logger.error(f"❌ Ошибка в callback: {e}")
            
            # Обновляем время модификации
            self.last_modified['sources'] = datetime.now()
            logger.info("✅ Перезагрузка sources.yaml завершена успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка перезагрузки sources.yaml: {e}")
        finally:
            self.reload_in_progress = False
    
    async def _reload_users(self):
        """Асинхронная перезагрузка пользователей"""
        if self.reload_in_progress:
            logger.warning("⚠️ Перезагрузка уже в процессе, пропускаем")
            return
        
        try:
            self.reload_in_progress = True
            logger.info("🔄 Начинаем перезагрузку users.yaml...")
            
            # Загружаем новую конфигурацию пользователей
            users_file = self.config_dir / "users.yaml"
            with open(users_file, 'r', encoding='utf-8') as f:
                users_config = yaml.safe_load(f)
                users = users_config if users_config else {}
            
            logger.info(f"👥 Загружено пользователей: {len(users)}")
            
            # Вызываем callbacks для пользователей
            for callback in self.reload_callbacks['users']:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(users)
                    else:
                        callback(users)
                    logger.info("✅ Users callback выполнен успешно")
                except Exception as e:
                    logger.error(f"❌ Ошибка в users callback: {e}")
            
            # Обновляем время модификации
            self.last_modified['users'] = datetime.now()
            logger.info("✅ Перезагрузка users.yaml и topics завершена успешно")
            
        except Exception as e:
            logger.error(f"❌ Ошибка перезагрузки users.yaml: {e}")
        finally:
            self.reload_in_progress = False
    
    def load_initial_config(self, config_type: str) -> Any:
        """Загрузка начальной конфигурации"""
        try:
            if config_type == 'sources':
                sources_file = self.config_dir / "sources.yaml"
                with open(sources_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    return config.get('sources', {})
            
            elif config_type == 'users':
                users_file = self.config_dir / "users.yaml"
                with open(users_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            
            elif config_type == 'topics':
                topics_file = self.config_dir / "topics_mapping.json"
                with open(topics_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            else:
                logger.error(f"❌ Неизвестный тип конфигурации: {config_type}")
                return {}
                
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки {config_type}: {e}")
            return {}
    
    def get_reload_status(self) -> Dict[str, Any]:
        """Получение статуса перезагрузки"""
        return {
            'process_name': self.process_name,
            'reload_in_progress': self.reload_in_progress,
            'last_modified': self.last_modified,
            'registered_callbacks': {
                config_type: len(callbacks) 
                for config_type, callbacks in self.reload_callbacks.items()
            }
        }


# Утилиты для отправки сигналов
def send_reload_signal(signal_type: str, process_name: Optional[str] = None):
    """Отправка сигнала перезагрузки процессу"""
    import subprocess
    import os
    
    # Определяем тип сигнала
    if signal_type == 'sources':
        sig = 'USR1'
        config_name = 'sources.yaml'
    elif signal_type == 'users':
        sig = 'USR2'
        config_name = 'users.yaml'
    else:
        print(f"❌ Неизвестный тип сигнала: {signal_type}")
        return False
    
    try:
        if process_name:
            # Отправляем сигнал конкретному процессу
            result = subprocess.run([
                'pgrep', '-f', process_name
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid.strip():
                        os.kill(int(pid), getattr(signal, f'SIG{sig}'))
                        print(f"✅ Сигнал {sig} отправлен процессу {process_name} (PID: {pid})")
                return True
            else:
                print(f"❌ Процесс {process_name} не найден")
                return False
        else:
            # Отправляем сигнал всем процессам RSS Bus
            rss_processes = ['rss_bus_core.py', 'user_notification_service.py']
            sent_count = 0
            
            for process in rss_processes:
                result = subprocess.run([
                    'pgrep', '-f', process
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid.strip():
                            os.kill(int(pid), getattr(signal, f'SIG{sig}'))
                            print(f"✅ Сигнал {sig} отправлен {process} (PID: {pid})")
                            sent_count += 1
            
            if sent_count > 0:
                print(f"📡 Сигнал перезагрузки {config_name} отправлен {sent_count} процессам")
                return True
            else:
                print("❌ Не найдено активных процессов RSS Bus")
                return False
                
    except Exception as e:
        print(f"❌ Ошибка отправки сигнала: {e}")
        return False


# Команда для CLI использования
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2 or sys.argv[1] not in ['sources', 'users']:
        print("Использование:")
        print(f"  python3 core/hot_reload.py sources  # Перезагрузка sources.yaml")
        print(f"  python3 core/hot_reload.py users    # Перезагрузка users.yaml")
        sys.exit(1)
    
    signal_type = sys.argv[1]
    success = send_reload_signal(signal_type)
    
    if success:
        print(f"🔄 Запрошена перезагрузка {signal_type}.yaml")
        print("📋 Проверьте логи процессов для подтверждения")
    else:
        print(f"❌ Не удалось отправить сигнал перезагрузки")
        sys.exit(1) 
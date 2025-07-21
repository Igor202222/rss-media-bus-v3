#!/usr/bin/env python3
"""
RSS Media Bus v3.0 - Основная конфигурация системы
"""

import os
from pathlib import Path

# ============= ПУТИ И ФАЙЛЫ =============

# Базовая директория проекта
BASE_DIR = Path(__file__).parent

# База данных SQLite
DATABASE_PATH = BASE_DIR / "rss_media_bus.db"

# Конфигурационные файлы
CONFIG_DIR = BASE_DIR / "config"
SOURCES_CONFIG = CONFIG_DIR / "sources.yaml"
USERS_CONFIG = CONFIG_DIR / "users.yaml"

# Логи
LOGS_DIR = BASE_DIR / "logs"
RSS_LOG_FILE = BASE_DIR / "rss_monitor.log"

# ============= RSS МОНИТОРИНГ =============

# Интервал между циклами мониторинга (секунды)
MONITORING_INTERVAL = 300  # 5 минут

# Максимальное время ожидания для HTTP запросов (секунды)
HTTP_TIMEOUT = 30
REQUEST_TIMEOUT = HTTP_TIMEOUT  # Алиас для совместимости

# Максимальное количество попыток при ошибке
MAX_RETRY_ATTEMPTS = 3

# ============= БАЗА ДАННЫХ =============

# Время хранения старых статей (дни)
ARTICLE_RETENTION_DAYS = 90

# Максимальное количество статей в базе
MAX_ARTICLES_COUNT = 100000

# ============= СОЗДАНИЕ ДИРЕКТОРИЙ =============

def ensure_directories():
    """Создание необходимых директорий"""
    LOGS_DIR.mkdir(exist_ok=True)
    CONFIG_DIR.mkdir(exist_ok=True)
    print(f"✅ Директории созданы: {LOGS_DIR}, {CONFIG_DIR}")

if __name__ == "__main__":
    ensure_directories()
    print(f"📊 DATABASE_PATH: {DATABASE_PATH}")
    print(f"📁 CONFIG_DIR: {CONFIG_DIR}") 
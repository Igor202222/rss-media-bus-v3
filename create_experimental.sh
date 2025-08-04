#!/bin/bash

echo "🧪 СОЗДАНИЕ ЭКСПЕРИМЕНТАЛЬНОЙ КОПИИ RSS MEDIA BUS"
echo "================================================="

# Определяем пути
PRODUCTION_DIR="/opt/rss_media_bus"
EXPERIMENTAL_DIR="/opt/rss_media_bus_experimental"

# Проверяем что мы в правильной директории
cd $PRODUCTION_DIR || exit 1

echo "📦 Создаю полную копию проекта..."
cp -r $PRODUCTION_DIR $EXPERIMENTAL_DIR

cd $EXPERIMENTAL_DIR

echo "🧹 Очищаю экспериментальную копию..."

# 1. Удаляем production базу данных (ВАЖНО!)
if [ -f "rss_media_bus.db" ]; then
    echo "   💾 Удаляю production БД (создастся новая пустая)"
    rm rss_media_bus.db
fi

# 2. Очищаем логи
echo "   📝 Очищаю все логи"
rm -f *.log
find . -name "*.log.gz" -delete 2>/dev/null || true

# 3. Очищаем Python cache
echo "   🗑️ Удаляю cache файлы"
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# 4. Создаем МИНИМАЛЬНЫЕ конфигурационные файлы для экспериментов
echo "⚙️ Создаю экспериментальные конфиги..."

# Бэкапим оригинальные конфиги
mv config/sources.yaml config/sources_production.yaml.backup
mv config/users.yaml config/users_production.yaml.backup

# Создаем минимальный sources.yaml для экспериментов (только 2 тестовых источника)
cat > config/sources.yaml << 'EOD'
# Экспериментальные RSS источники
# ВАЖНО: Это НЕ production конфиг! Только для тестов.

sources:
  # Тестовые источники для экспериментов
  test_habr:
    url: "https://habr.com/ru/rss/hub/programming/"
    name: "Хабр - Программирование (ТЕСТ)"
    active: true
    group: "tech_test"
  
  test_vc:
    url: "https://vc.ru/rss"
    name: "VC.ru Новости (ТЕСТ)" 
    active: true
    group: "tech_test"

# ============================================
# ДОБАВЛЯЙТЕ НОВЫЕ ИСТОЧНИКИ ЗДЕСЬ ДЛЯ ТЕСТИРОВАНИЯ
# После успешного тестирования переносите в production
# ============================================

  # Новые источники для тестирования:
  # new_source_example:
  #   url: "https://example.com/rss"
  #   name: "Новый источник (ТЕСТ)"
  #   active: false  # Включить после настройки
  #   group: "new_test"
EOD

# Создаем ТЕСТОВЫЙ users.yaml
cat > config/users.yaml << 'EOD'
# Экспериментальные пользователи
# ВАЖНО: Используйте ТОЛЬКО тестовых ботов и тестовые чаты!

users:
  test_user:
    name: "Тестовый пользователь"
    active: true
    telegram_configs:
      test_bot:
        enabled: true
        # ⚠️ ВАЖНО: Замените на токен ТЕСТОВОГО бота!
        # Создайте нового бота через @BotFather специально для экспериментов
        bot_token: "YOUR_TEST_BOT_TOKEN_HERE"  
        
        # ⚠️ ВАЖНО: Замените на ID ТЕСТОВОГО чата!
        # Создайте новую группу специально для экспериментов
        chat_id: -1001234567890  
        
        # Маппинг источников к топикам (настройте после создания группы)
        topics_mapping:
          test_habr: 1      # ID топика для Хабра
          test_vc: 2        # ID топика для VC.ru
        
        # Источники для обработки (только тестовые)
        sources: ["test_habr", "test_vc"]

# ============================================
# ИНСТРУКЦИЯ ПО НАСТРОЙКЕ:
# 1. Создайте тестового бота через @BotFather
# 2. Создайте тестовую группу в Telegram  
# 3. Добавьте бота в группу как админа
# 4. Создайте топики в группе
# 5. Замените токен и chat_id выше
# 6. Запустите: ./start_system.sh
# ============================================
EOD

# 5. Обновляем config.py для экспериментальной БД
echo "📝 Обновляю config.py для экспериментальной БД..."
sed -i 's/rss_media_bus\.db/rss_media_bus_experimental.db/g' config.py

# 6. Создаем подробный README для экспериментов
cat > EXPERIMENTAL_README.md << 'EOD'
# 🧪 RSS Media Bus - Экспериментальная копия

Это **изолированная копия** проекта для безопасного тестирования новых функций.

## ⚠️ КРИТИЧЕСКИ ВАЖНО

1. **Отдельная БД**: `rss_media_bus_experimental.db` (не влияет на production)
2. **Тестовые конфиги**: все настройки изолированы от production
3. **Отдельный бот**: используйте ТОЛЬКО тестового Telegram бота
4. **Отдельный чат**: создайте новую тестовую группу

## 🚀 Быстрый старт

### 1. Настройка Telegram бота
```
1. Напишите @BotFather в Telegram
2. /newbot → укажите имя "RSS Test Bot" 
3. Получите токен
4. Создайте новую группу для тестов
5. Добавьте бота в группу как администратора
```

### 2. Настройка конфигурации
```bash
# Отредактируйте конфиг
nano config/users.yaml

# Замените:
# - YOUR_TEST_BOT_TOKEN_HERE на токен тестового бота
# - -1001234567890 на ID тестовой группы
```

### 3. Запуск системы
```bash
cd /opt/rss_media_bus_experimental
./start_system.sh
```

## 📝 Тестирование новых источников

### Добавление нового источника:
1. Отредактируйте `config/sources.yaml`
2. Добавьте новый источник с `active: true`
3. Настройте топик в `config/users.yaml`
4. Перезапустите: `./start_system.sh`

### Пример добавления источника:
```yaml
# В config/sources.yaml
new_tech_blog:
  url: "https://techblog.example.com/feed"
  name: "Tech Blog (ТЕСТ)"
  active: true
  group: "new_sources"

# В config/users.yaml в topics_mapping:
new_tech_blog: 3  # ID топика в тестовой группе
```

## 🔍 Мониторинг тестов

```bash
# Проверка процессов
ps aux | grep -E "(rss_bus_core|user_notification)"

# Просмотр логов
tail -f rss_core.log
tail -f user_service.log

# Проверка БД
sqlite3 rss_media_bus_experimental.db "SELECT COUNT(*) FROM articles;"
```

## 🔙 Возврат к production

Production система НЕ затронута. Для возврата:
```bash
cd /opt/rss_media_bus
./start_system.sh
```

## 📊 После успешных тестов

1. Скопируйте протестированные источники в production `config/sources.yaml`
2. Настройте топики в production `config/users.yaml`
3. Перезапустите production систему

## ⚡ Полезные команды

```bash
# Остановка экспериментов
pkill -f "rss_bus_core.py|user_notification_service.py"

# Очистка экспериментальной БД
rm rss_media_bus_experimental.db

# Просмотр архивных конфигов production
cat config/sources_production.yaml.backup
```
EOD

echo ""
echo "✅ ЭКСПЕРИМЕНТАЛЬНАЯ КОПИЯ СОЗДАНА!"
echo ""
echo "📁 Расположение: $EXPERIMENTAL_DIR"
echo ""
echo "🔧 ОБЯЗАТЕЛЬНЫЕ СЛЕДУЮЩИЕ ШАГИ:"
echo ""
echo "1. 🤖 Создайте тестового Telegram бота:"
echo "   - Напишите @BotFather"
echo "   - /newbot → 'RSS Test Bot'"
echo "   - Сохраните токен"
echo ""
echo "2. 👥 Создайте тестовую группу:"
echo "   - Новая группа в Telegram"
echo "   - Добавьте бота как админа"
echo "   - Создайте 2 топика: 'Хабр' и 'VC.ru'"
echo ""
echo "3. ⚙️ Настройте конфигурацию:"
echo "   nano $EXPERIMENTAL_DIR/config/users.yaml"
echo "   # Замените YOUR_TEST_BOT_TOKEN_HERE и chat_id"
echo ""
echo "4. 🚀 Запустите тесты:"
echo "   cd $EXPERIMENTAL_DIR"
echo "   ./start_system.sh"
echo ""
echo "📖 Подробные инструкции: $EXPERIMENTAL_DIR/EXPERIMENTAL_README.md"
echo ""
echo "⚠️ ВАЖНО: Не используйте production токены и чаты!"
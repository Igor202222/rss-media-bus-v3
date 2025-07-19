# 🔄 Управление процессами RSS Media Bus v3.0

## 📊 **Активные процессы**

### **📡 RSS мониторинг:**
```bash
# Проверка статуса:
ps aux | grep rss_monitoring | grep -v grep

# Запуск в фоне:
nohup python3 rss_monitoring.py > rss_monitor.log 2>&1 &

# Остановка:
kill $(pgrep -f rss_monitoring.py)

# Перезапуск:
pkill -f rss_monitoring.py && sleep 2 && nohup python3 rss_monitoring.py > rss_monitor.log 2>&1 &
```

### **🤖 Пользовательский бот:**
```bash
# Проверка статуса:
ps aux | grep telegram_user_bot | grep -v grep

# Запуск в фоне:
cd user_bot && nohup python3 telegram_user_bot.py > bot.log 2>&1 &

# Остановка:
kill $(pgrep -f telegram_user_bot.py)
```

## 📊 **Мониторинг логов**

### **⚠️ ВАЖНО: Логи исключены из индексации**

Файлы логов добавлены в `.gitignore` чтобы **не засорять контекст в будущих сессиях**:

```bash
# Исключенные файлы:
*.log
rss_monitor.log
user_bot/bot.log
__pycache__/
*.pyc
*.db
```

### **📝 Просмотр логов (когда нужно):**

#### **RSS мониторинг:**
```bash
# Последние записи:
tail -20 rss_monitor.log

# Следить в реальном времени:
tail -f rss_monitor.log

# Поиск ошибок:
grep -i "error\|❌" rss_monitor.log

# Статистика обработки:
grep "📊\|✅\|новых статей" rss_monitor.log | tail -10
```

#### **Пользовательский бот:**
```bash
# Логи пользовательского бота:
tail -20 user_bot/bot.log

# Регистрации пользователей:
grep "🎉\|зарегистрирован" user_bot/bot.log

# Ошибки бота:
grep -i "error\|exception" user_bot/bot.log
```

### **🧹 Очистка логов (если нужно):**
```bash
# Очистить логи RSS:
> rss_monitor.log

# Очистить логи бота:
> user_bot/bot.log

# Архивировать старые логи:
mv rss_monitor.log rss_monitor_$(date +%Y%m%d).log.backup
touch rss_monitor.log
```

## 🔄 **Типичные операции**

### **🚀 Полный перезапуск системы:**
```bash
# 1. Остановка всех процессов:
pkill -f "rss_monitoring.py|telegram_user_bot.py"

# 2. Ожидание завершения:
sleep 5

# 3. Запуск RSS мониторинга:
nohup python3 rss_monitoring.py > rss_monitor.log 2>&1 &

# 4. Запуск пользовательского бота:
cd user_bot && nohup python3 telegram_user_bot.py > bot.log 2>&1 &

# 5. Проверка статуса:
ps aux | grep -E "rss_monitoring|telegram_user_bot" | grep -v grep
```

### **📊 Проверка работоспособности:**
```bash
# Процессы запущены:
ps aux | grep -E "rss_monitoring|telegram_user_bot" | grep -v grep

# Логи обновляются:
ls -lt *.log user_bot/*.log

# Debug логи в Telegram:
# Проверьте топик "📡 RSS МОНИТОРИНГ" в чате (-1002756550488)

# Размер логов не слишком большой:
du -h *.log user_bot/*.log
```

### **⚡ Быстрая диагностика проблем:**
```bash
# RSS не парсит статьи:
tail -50 rss_monitor.log | grep -E "❌|error|timeout"

# Пользовательский бот не отвечает:
tail -30 user_bot/bot.log | grep -E "error|exception|failed"

# Проблемы с Telegram API:
grep -i "telegram\|api\|bot" *.log user_bot/*.log | tail -10

# Проблемы с базой данных:
grep -i "database\|db\|sqlite" rss_monitor.log | tail -5
```

## 📈 **Мониторинг производительности**

### **📊 Статистика RSS мониторинга:**
```bash
# Количество обработанных статей сегодня:
grep "новых статей" rss_monitor.log | grep $(date +%Y-%m-%d) | wc -l

# Источники с ошибками:
grep "❌.*:" rss_monitor.log | cut -d: -f2 | sort | uniq -c | sort -nr

# Время выполнения циклов:
grep "Время цикла" rss_monitor.log | tail -10
```

### **👥 Статистика пользователей:**
```bash
# Новые регистрации сегодня:
grep "зарегистрирован" user_bot/bot.log | grep $(date +%Y-%m-%d) | wc -l

# Активность пользователей:
grep "/start\|/status\|/sources" user_bot/bot.log | tail -20
```

---

**⚠️ Примечание:** Логи намеренно исключены из документации проекта для предотвращения засорения контекста. При необходимости анализа используйте команды выше.

*Последнее обновление: Июль 2025* 
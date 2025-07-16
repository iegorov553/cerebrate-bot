# ⚠️ Warning Management System

Систематический подход к обработке warnings для предотвращения 27% всех проблем разработки.

## 🎯 Цель системы

Превратить warnings из игнорируемых сообщений в важные сигналы о проблемах конфигурации и архитектуры.

## 📋 Этапы обработки warnings

### 1. Pre-Development Baseline (Перед началом работы)

```bash
# Создание baseline warnings
python3 -c "import bot; print('Import check OK')" 2>&1 | grep -i warning > baseline_warnings.txt

# Проверка тестов на baseline warnings
python3 -m pytest tests/ -v 2>&1 | grep -i warning > test_baseline_warnings.txt

# Проверка handlers
python3 -c "
from bot.handlers.callbacks.admin_callbacks import AdminCallbackHandler
from bot.handlers.admin_conversations import create_broadcast_conversation
print('Handler check OK')
" 2>&1 | grep -i warning > handler_baseline_warnings.txt
```

### 2. During Development (Во время разработки)

#### Обязательные действия при каждом warning:
- [ ] **Прочитать** полный текст warning
- [ ] **Понять** причину warning
- [ ] **Исправить** warning сразу, не откладывая
- [ ] **Проверить** что warning исчез

#### Систематизация warnings по типам:

```python
# 1. PTBUserWarning (python-telegram-bot)
# Обычно указывает на неправильную конфигурацию

# 2. DeprecationWarning
# Указывает на устаревшие API

# 3. RuntimeWarning
# Указывает на проблемы с async/await

# 4. UserWarning
# Указывает на неправильное использование библиотек
```

### 3. Post-Development Verification (После изменений)

```bash
# Проверка что новых warnings нет
python3 -c "import bot; print('Import check OK')" 2>&1 | grep -i warning > new_warnings.txt
diff baseline_warnings.txt new_warnings.txt

# Проверка тестов на новые warnings
python3 -m pytest tests/ -v 2>&1 | grep -i warning > new_test_warnings.txt
diff test_baseline_warnings.txt new_test_warnings.txt
```

## 🔧 Обработка специфических warnings

### 1. PTBUserWarning для ConversationHandler

```python
# ❌ Проблема: per_message=True с MessageHandler
PTBUserWarning: If 'per_message=True', all entry points, state handlers, and fallbacks must be 'CallbackQueryHandler'

# ✅ Решение: Изменить конфигурацию
return ConversationHandler(
    # ...
    per_message=False,  # Позволяет MessageHandler в states
    # ...
)
```

### 2. DeprecationWarning для Sentry

```python
# ❌ Проблема: Устаревший API
DeprecationWarning: sentry_sdk.configure_scope is deprecated

# ✅ Решение: Использовать новый API
# Старый способ
with sentry_sdk.configure_scope() as scope:
    scope.set_user({"id": user_id})

# Новый способ
sentry_sdk.set_user({"id": user_id})
```

### 3. RuntimeWarning для async/await

```python
# ❌ Проблема: Не awaited coroutine
RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited

# ✅ Решение: Добавить await
result = await async_function()
```

### 4. UserWarning для библиотек

```python
# ❌ Проблема: Неправильное использование
UserWarning: Some library usage warning

# ✅ Решение: Читать документацию библиотеки
# Исправить использование согласно best practices
```

## 📊 Мониторинг warnings

### Автоматизированная проверка

```bash
#!/bin/bash
# Скрипт для проверки warnings в CI/CD

# Запуск тестов с записью warnings
python3 -m pytest tests/ -v 2>&1 | grep -i warning > current_warnings.txt

# Сравнение с baseline
if ! diff -q baseline_warnings.txt current_warnings.txt > /dev/null; then
    echo "❌ Новые warnings обнаружены:"
    diff baseline_warnings.txt current_warnings.txt
    exit 1
else
    echo "✅ Новых warnings нет"
fi
```

### Ручная проверка

```bash
# Проверка импортов
python3 -c "
import sys
import warnings
warnings.filterwarnings('error')
try:
    import bot
    print('✅ Импорт без warnings')
except Warning as w:
    print(f'❌ Warning при импорте: {w}')
"

# Проверка конкретного handler
python3 -c "
import warnings
warnings.filterwarnings('error')
try:
    from bot.handlers.admin_conversations import create_broadcast_conversation
    conv = create_broadcast_conversation()
    print('✅ ConversationHandler без warnings')
except Warning as w:
    print(f'❌ Warning в ConversationHandler: {w}')
"
```

## 🎯 Специализированные проверки

### Для ConversationHandler

```python
# Проверка конфигурации
def validate_conversation_handler(handler):
    """Проверка ConversationHandler на потенциальные warnings"""
    warnings = []
    
    # Проверка per_message с MessageHandler
    if handler.per_message:
        for state_handlers in handler.states.values():
            for h in state_handlers:
                if isinstance(h, MessageHandler):
                    warnings.append("per_message=True with MessageHandler")
    
    # Проверка timeout
    if handler.conversation_timeout and handler.conversation_timeout > 600:
        warnings.append("Very long conversation timeout")
    
    return warnings
```

### Для Database Operations

```python
# Проверка database warnings
def check_database_warnings():
    """Проверка database операций на warnings"""
    import warnings
    
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        
        # Тестовая операция
        from bot.database.client import DatabaseClient
        client = DatabaseClient("test_url")
        
        # Проверка warnings
        if w:
            print(f"❌ Database warnings: {[str(warning.message) for warning in w]}")
        else:
            print("✅ Database без warnings")
```

## 📈 Метрики успешности

### Индикаторы качественного warning management:
- Нет новых warnings после изменений
- Все warnings понятны и задокументированы
- Быстрое устранение warnings (в течение 1 commit)
- Proactive предотвращение warnings

### Индикаторы проблем:
- Накопление warnings без исправления
- Непонимание причин warnings
- Повторяющиеся warnings одного типа
- Игнорирование warnings в output

## 🔄 Continuous Improvement

### После каждого warning:
- [ ] Добавить проверку в automated tests
- [ ] Обновить документацию с решением
- [ ] Создать template для подобных случаев
- [ ] Улучшить baseline проверки

### Еженедельный review:
- [ ] Анализ всех warnings за неделю
- [ ] Выявление patterns в warnings
- [ ] Обновление automated checks
- [ ] Тренировка team на новых patterns

## 🚫 Частые ошибки

### 1. Игнорирование warnings
```bash
# ❌ Неправильно - перенаправить stderr
python3 command > output.txt 2>&1

# ✅ Правильно - читать stderr
python3 command 2>&1 | tee output.txt
```

### 2. Откладывание исправления warnings
```bash
# ❌ Неправильно - "исправлю потом"
git add .
git commit -m "feature implementation"  # warnings не исправлены

# ✅ Правильно - исправить сразу
# исправить warning
git add .
git commit -m "feature implementation + fix warning"
```

### 3. Неполное понимание warnings
```python
# ❌ Неправильно - подавить warning
import warnings
warnings.filterwarnings("ignore")

# ✅ Правильно - понять и исправить
# читать документацию
# понять причину
# исправить код
```

## 📚 Полезные ресурсы

### Документация warnings:
- [Python warnings](https://docs.python.org/3/library/warnings.html)
- [python-telegram-bot warnings](https://github.com/python-telegram-bot/python-telegram-bot/wiki/Frequently-Asked-Questions)
- [Sentry SDK migration guide](https://docs.sentry.io/platforms/python/migration/)

### Инструменты:
- `python -W error` - превратить warnings в errors
- `python -W ignore::DeprecationWarning` - игнорировать конкретный тип
- `pytest -v --tb=short` - короткий traceback для warnings

---

**Статус**: Обязательно к применению  
**Последнее обновление**: 2025-07-16 16:45  
**Применимость**: Все этапы разработки без исключений
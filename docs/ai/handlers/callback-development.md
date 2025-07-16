# 🔄 Callback Development Guide

Руководство по разработке и поддержке callback handlers в проекте.

## 🏗️ Архитектура Callback Handlers

### Базовый класс BaseCallbackHandler
```python
class BaseCallbackHandler:
    async def can_handle(self, callback_data: str) -> bool:
        """Проверка может ли handler обработать данный callback"""
        
    async def handle_callback(self, query: CallbackQuery, callback_data: str, translator: Translator, user_data: dict) -> None:
        """Обработка callback query"""
```

### Существующие Handlers
- **NavigationCallbackHandler**: menu_*, back_*, language_*
- **QuestionsCallbackHandler**: questions_*
- **FriendsCallbackHandler**: friends_*
- **AdminCallbackHandler**: admin_*
- **FeedbackCallbackHandler**: feedback_*

## 🔄 Handler Development Workflow

### 1. Audit Phase (ОБЯЗАТЕЛЬНО)
```bash
# Поиск всех callback_data в keyboards
grep -r "callback_data" bot/keyboards/keyboard_generators.py

# Проверка существующих handlers
grep -r "can_handle" bot/handlers/callbacks/

# Проверка ConversationHandler patterns
grep -r "ConversationHandler" bot/handlers/
find . -name "*conversation*" -type f

# Изучение UI flow в реальном использовании
grep -r "pattern" bot/ --include="*.py" -A 5 -B 5
```

### 2. Configuration Phase
```python
# Понимание handler priorities
# group=-1: высший приоритет (ConversationHandler)
# group=0: обычные callback handlers  
# group=1: message handlers (самый низкий)

# Проверка per_message конфигурации
# per_message=True: только CallbackQueryHandler
# per_message=False: позволяет MessageHandler в states

# Анализ взаимодействия handlers
application.add_handler(handler, group=0)  # Правильная группа
```

### 3. Implementation Phase
```python
# ✅ Inline логика для простых операций (2-5 строк)
elif data == "simple_toggle":
    success = await self.user_ops.toggle_setting(user_id, "key")
    await self._handle_menu_refresh(query, translator)
    
# ✅ Отдельные методы только для сложных случаев (>10 строк)
elif data == "complex_operation":
    await self._handle_complex_operation(query, translator)

# ✅ Обязательная проверка на file size limits
# Если файл >400 строк → только inline логика
```

### 4. Testing Phase
```python
# Технические тесты
def test_handler_can_handle():
    assert handler.can_handle("expected_pattern")
    
# Полный user journey
def test_complete_user_flow():
    # Проверка всего пути пользователя
    
# Проверка на дублирование обработки
def test_no_duplicate_handling():
    # Убеждаемся что сообщения не обрабатываются дважды
```

## 📝 Принципы разработки

### 1. Inline Logic для простых операций
```python
# ✅ ПРАВИЛЬНО - простые операции inline
elif data == "simple_toggle":
    success = await self.user_ops.toggle_setting(user_id, "key")
    await self._handle_menu_refresh(query, translator)
    
# ❌ НЕПРАВИЛЬНО - избыточное выделение в метод
elif data == "simple_toggle":
    await self._handle_simple_toggle(query, translator)
```

### 2. Отдельные методы для сложной логики
```python
# ✅ ПРАВИЛЬНО - сложная логика в отдельном методе
elif data == "complex_operation":
    await self._handle_complex_operation(query, translator)
    
async def _handle_complex_operation(self, query, translator):
    # Много логики (>10 строк)
```

### 3. Предпочтение существующих handlers
```python
# ❌ НЕ создавать новые handlers
class NewUnnecessaryHandler(BaseCallbackHandler):
    
# ✅ Использовать существующие handlers
# questions_* → QuestionsCallbackHandler
# friends_* → FriendsCallbackHandler
```

## ⚠️ Warning Management для Handlers

### Систематическая обработка warnings:
```python
# 1. Pre-Development: записать baseline warnings
python3 -c "from bot.handlers.callbacks.your_handler import YourHandler; print('Baseline OK')"

# 2. During Development: читать ВСЕ warnings
# PTBUserWarning для ConversationHandler конфигурации
# DeprecationWarning для устаревших API
# RuntimeWarning для async/await проблем

# 3. Post-Development: убеждаться что новых warnings нет
python3 -m pytest tests/test_handlers_integration.py -v
```

### Частые warnings и их решения:
```python
# ❌ PTBUserWarning: per_message=True with MessageHandler
return ConversationHandler(
    per_message=True,  # Конфликт!
    states={WAITING: [MessageHandler(...)]}
)

# ✅ Исправление
return ConversationHandler(
    per_message=False,  # Позволяет MessageHandler
    states={WAITING: [MessageHandler(...)]}
)
```

## 📊 Мониторинг и отладка

### Логирование
```python
self.logger.info("Action executed", user_id=user.id, action=data)
```

### Метрики
- Количество обработанных callbacks
- Время выполнения операций
- Количество ошибок

### Отладка
```python
# Включение debug логирования
logger.setLevel(logging.DEBUG)
```

## 🚫 Частые ошибки

### 1. Дублирующие handlers
```python
# ❌ Создание handler для уже обработанного callback
callback_data = "admin_broadcast"  # Уже в ConversationHandler!
```

### 2. Неправильный приоритет
```python
# ❌ Неправильная группа handlers
application.add_handler(handler, group=0)  # Конфликт с другими

# ✅ Правильная группа
application.add_handler(handler, group=1)  # Низкий приоритет
```

### 3. Отсутствие error handling
```python
# ❌ Без обработки ошибок
result = await operation()

# ✅ С обработкой ошибок
try:
    result = await operation()
except Exception as e:
    logger.error("Operation failed", error=str(e))
    await query.answer("Произошла ошибка")
```

---

**Статус**: Актуально  
**Последнее обновление**: 2025-07-16 16:35  
**Применимость**: Все callback handlers в проекте
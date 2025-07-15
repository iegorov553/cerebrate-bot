# 🎨 Общие паттерны Callback Handlers

Стандартные подходы и паттерны для работы с callback handlers без дублирования кода.

## 🗺️ Навигация
- ← [handlers-map.md](handlers-map.md) - Карта всех handlers
- → [questions-specifics.md](questions-specifics.md) - Специфика Questions handler
- ↗ [../workflows/adding-callbacks.md](../workflows/adding-callbacks.md) - Процесс добавления

## 🏗️ Базовая архитектура Handler

### BaseCallbackHandler Pattern
```python
from bot.handlers.base.base_handler import BaseCallbackHandler

class YourCallbackHandler(BaseCallbackHandler):
    def can_handle(self, data: str) -> bool:
        """Определяет может ли handler обработать callback."""
        return data.startswith("your_prefix_")
    
    async def handle_callback(
        self, 
        query: CallbackQuery, 
        data: str, 
        translator: Translator, 
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Основная логика обработки callback."""
        # Роутинг по типам action
        if data.startswith("your_prefix_simple_action"):
            # Простая inline логика (2-5 строк)
            pass
        elif data.startswith("your_prefix_complex:"):
            await self._handle_complex_action(query, data, translator)
        else:
            self.logger.warning("Unknown action", action=data)
```

### Регистрация в Router
```python
# В main.py или соответствующем файле
callback_router.register_handler(YourCallbackHandler(db_client, config, cache))
```

## 🔄 Паттерны обработки Callbacks

### 1. Simple Toggle Pattern (РЕКОМЕНДУЕТСЯ)
```python
elif data == "questions_toggle_notifications":
    # ✅ ХОРОШО: Inline логика для простых операций
    from bot.database.user_operations import UserOperations
    user_ops = UserOperations(self.db_client, self.user_cache)
    user_data = await user_ops.get_user_settings(query.from_user.id)
    current_enabled = user_data.get("enabled", True) if user_data else True
    await user_ops.update_user_settings(query.from_user.id, {"enabled": not current_enabled})
    await self.user_cache.invalidate(f"user_settings_{query.from_user.id}")
    await self._handle_questions_menu(query, translator)
```

### 2. ID-based Action Pattern
```python
elif data.startswith("questions_toggle:"):
    # Извлечение ID из callback_data
    try:
        question_id = int(data.split(":")[1])
        success = await question_manager.question_ops.toggle_question_status(question_id)
        
        if success:
            await self._handle_questions_menu(query, translator)
            self.logger.info("Question toggled", user_id=user.id, question_id=question_id)
        else:
            await query.edit_message_text(translator.translate("errors.general"))
            
    except (ValueError, IndexError) as e:
        self.logger.error("Invalid question ID", user_id=user.id, data=data, error=str(e))
        await query.edit_message_text(translator.translate("errors.general"))
```

### 3. Complex Action Pattern (с отдельным методом)
```python
elif data.startswith("questions_create:"):
    await self._handle_create_question(query, data, question_manager, translator)

async def _handle_create_question(self, query, data, question_manager, translator):
    """Handle question creation with validation."""
    user = query.from_user
    try:
        # Сложная логика создания вопроса
        # ... много строк кода ...
        
        self.logger.info("Question created", user_id=user.id)
    except Exception as e:
        self.logger.error("Question creation failed", user_id=user.id, error=str(e))
        await query.edit_message_text(translator.translate("errors.general"))
```

## 💾 Database Operations Patterns

### Standard User Settings Pattern
```python
# Типичная операция с пользовательскими настройками
from bot.database.user_operations import UserOperations

async def update_user_setting(self, user_id: int, key: str, value: any):
    user_ops = UserOperations(self.db_client, self.user_cache)
    
    # 1. Update в базе
    success = await user_ops.update_user_settings(user_id, {key: value})
    
    # 2. ОБЯЗАТЕЛЬНО: Invalidate cache
    if success:
        await self.user_cache.invalidate(f"user_settings_{user_id}")
        return True
    return False
```

### Question Operations Pattern
```python
# Работа с вопросами через QuestionManager
from bot.questions.question_manager import QuestionManager

async def work_with_questions(self, user_id: int):
    question_manager = QuestionManager(self.db_client, self.config, self.user_cache)
    
    # Получить summary
    summary = await question_manager.get_user_questions_summary(user_id)
    
    # Работа с конкретным вопросом
    question_details = await question_manager.question_ops.get_question_details(question_id)
    
    # Toggle статуса
    success = await question_manager.question_ops.toggle_question_status(question_id)
```

## 🎨 UI Generation Patterns

### Inline Keyboard Generation
```python
from bot.keyboards.keyboard_generators import KeyboardGenerator

# Простая кнопка
keyboard = KeyboardGenerator.single_button_keyboard(
    translator.translate("button.back"), 
    "menu_questions"
)

# Множественные кнопки с ID
buttons = []
for item in items:
    text = f"{item.name} {'✅' if item.active else '❌'}"
    callback_data = f"questions_toggle:{item.id}"
    buttons.append(InlineKeyboardButton(text, callback_data=callback_data))

keyboard = InlineKeyboardMarkup([buttons])
```

### Dynamic Content Generation
```python
# Генерация контента на основе данных пользователя
async def generate_menu_content(self, user_id: int, translator: Translator):
    # Получить данные
    user_data = await self.get_user_data(user_id)
    
    # Сформировать текст
    text = translator.translate("menu.title")
    if user_data:
        text += f"\n{translator.translate('user.status', status=user_data.get('status'))}"
    
    # Сформировать клавиатуру
    keyboard = self.generate_menu_keyboard(user_data, translator)
    
    return text, keyboard
```

## 🚨 Error Handling Patterns

### Standard Error Handler
```python
async def safe_operation(self, query: CallbackQuery, translator: Translator):
    user = query.from_user
    try:
        # Основная логика
        result = await self.risky_operation()
        
        # Успешный результат
        await query.edit_message_text(translator.translate("success.message"))
        self.logger.info("Operation completed", user_id=user.id)
        
    except SpecificError as e:
        # Специфическая ошибка
        self.logger.warning("Known error occurred", user_id=user.id, error=str(e))
        await query.edit_message_text(translator.translate("errors.specific"))
        
    except Exception as e:
        # Общая ошибка
        self.logger.error("Unexpected error", user_id=user.id, error=str(e))
        await query.edit_message_text(translator.translate("errors.general"))
```

### Rate Limit Error Pattern
```python
from bot.utils.exceptions import RateLimitExceeded

try:
    # Операция которая может превысить лимит
    await self.rate_limited_operation()
    
except RateLimitExceeded as e:
    # Специальная обработка rate limit
    await query.edit_message_text(translator.translate("errors.rate_limit"))
    self.logger.warning("Rate limit exceeded", user_id=user.id, action=action)
```

## ⚡ Performance Patterns

### Cache-First Pattern
```python
async def get_user_data_cached(self, user_id: int):
    # 1. Проверить cache
    cache_key = f"user_data_{user_id}"
    cached_data = await self.user_cache.get(cache_key)
    
    if cached_data:
        return cached_data
    
    # 2. Fetch from database
    user_ops = UserOperations(self.db_client, self.user_cache)
    data = await user_ops.get_user_settings(user_id)
    
    # 3. Cache result
    await self.user_cache.set(cache_key, data, ttl=300)  # 5 minutes
    
    return data
```

### Batch Operations Pattern
```python
async def bulk_update_questions(self, question_updates: List[Dict]):
    """Bulk update для множественных операций."""
    success_count = 0
    
    for update in question_updates:
        try:
            await self.update_single_question(update)
            success_count += 1
        except Exception as e:
            self.logger.error("Bulk update item failed", update=update, error=str(e))
            
    self.logger.info("Bulk update completed", success=success_count, total=len(question_updates))
    return success_count
```

## 🔄 Navigation Patterns

### Menu Navigation Pattern
```python
async def handle_menu_navigation(self, query: CallbackQuery, menu_type: str, translator: Translator):
    """Стандартная навигация между меню."""
    
    menu_handlers = {
        "main": self._handle_main_menu,
        "questions": self._handle_questions_menu,
        "friends": self._handle_friends_menu,
        "settings": self._handle_questions_menu,  # Settings → Questions redirect!
    }
    
    handler = menu_handlers.get(menu_type)
    if handler:
        await handler(query, translator)
    else:
        self.logger.warning("Unknown menu type", menu_type=menu_type)
        await self._handle_main_menu(query, translator)  # Fallback
```

### Back Button Pattern
```python
# Стандартные back кнопки
BACK_PATTERNS = {
    "back_to_main": "menu_main",
    "back_to_questions": "menu_questions", 
    "back_to_friends": "menu_friends",
}

async def handle_back_navigation(self, query: CallbackQuery, back_action: str, translator: Translator):
    target_menu = BACK_PATTERNS.get(back_action, "menu_main")
    await self.handle_menu_navigation(query, target_menu.replace("menu_", ""), translator)
```

## 🧪 Testing Patterns

### Handler Testing Template
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_your_handler():
    # Setup
    handler = YourCallbackHandler(mock_db, mock_config, mock_cache)
    query = MagicMock()
    query.from_user.id = 12345
    
    # Mock dependencies
    handler.user_cache = AsyncMock()
    
    # Execute
    await handler.handle_callback(query, "your_prefix_action", mock_translator, mock_context)
    
    # Assert
    query.edit_message_text.assert_called_once()
    handler.user_cache.invalidate.assert_called_with("user_settings_12345")
```

## 📏 Code Quality Patterns

### Метод Size Guidelines
```python
# ✅ ХОРОШО: Короткий метод
async def simple_toggle(self, user_id: int, setting: str):
    user_ops = UserOperations(self.db_client, self.user_cache)
    current = await user_ops.get_setting(user_id, setting)
    await user_ops.update_setting(user_id, setting, not current)
    await self.user_cache.invalidate(f"user_settings_{user_id}")

# ❌ ПЛОХО: Слишком длинный метод (>50 строк)
async def complex_operation_with_many_steps(self, ...):
    # ... 60+ строк кода ...
    # Нужно разбить на smaller методы!
```

### Logging Consistency Pattern
```python
# Стандартные логи для handlers
self.logger.debug("Action started", user_id=user.id, action=action)
self.logger.info("Action completed", user_id=user.id, result=result)
self.logger.warning("Action failed", user_id=user.id, reason=reason)
self.logger.error("Unexpected error", user_id=user.id, error=str(e))
```

## 🚫 Anti-Patterns (ЧТО НЕ ДЕЛАТЬ)

### ❌ НЕПРАВИЛЬНО: Отдельный метод для простого toggle
```python
# НЕ ДЕЛАЙ ТАК!
elif data == "questions_toggle_notifications":
    await self._handle_toggle_notifications(query, translator)  # ❌ Лишний метод

async def _handle_toggle_notifications(self, query, translator):  # ❌ 20+ строк для toggle
    # ... много кода для простой операции ...
```

### ❌ НЕПРАВИЛЬНО: Создание Settings Handler
```python
# НЕ СОЗДАВАЙ!
class SettingsCallbackHandler(BaseCallbackHandler):  # ❌ Settings handler удален!
    def can_handle(self, data: str) -> bool:
        return data.startswith("settings_")  # ❌ Используй questions_*
```

### ❌ НЕПРАВИЛЬНО: Забыть Cache Invalidation
```python
# НЕ ЗАБЫВАЙ cache invalidation!
await user_ops.update_user_settings(user_id, {"key": value})
# ❌ ЗАБЫЛ: await self.user_cache.invalidate(f"user_settings_{user_id}")
```

### ❌ НЕПРАВИЛЬНО: Дублирование логики
```python
# НЕ ДУБЛИРУЙ код между handlers!
# Если логика повторяется → вынести в service layer
```

## 🎯 Decision Tree для Handler Operations

```
Нужно добавить новый callback?
├─ Простая операция (toggle, redirect)?
│  └─ ✅ Inline логика в существующий handler (2-5 строк)
├─ Существующий handler >400 строк?
│  ├─ ✅ Только inline логику добавлять
│  └─ 📋 Планировать рефакторинг в big-tasks/
├─ Сложная операция (>10 строк)?
│  ├─ Логика уже существует?
│  │  └─ ✅ Переиспользовать существующий метод
│  └─ ✅ Новый метод в существующий handler
└─ Совершенно новый домен?
   └─ ⚠️ Новый handler (ОЧЕНЬ редко!)
```

---

**Последнее обновление**: 2025-07-15 21:20  
**Применимость**: Все callback handlers в проекте  
**Следующее обновление**: При изменении общих паттернов
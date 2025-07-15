# 🎯 QuestionsCallbackHandler - Детальное руководство

Полная документация по самому важному handler в системе - обрабатывает ВСЕ настройки и вопросы пользователей.

## 🗺️ Навигация
- ← [handlers-map.md](handlers-map.md) - Карта всех handlers
- ← [patterns.md](patterns.md) - Общие паттерны
- → [friends-specifics.md](friends-specifics.md) - Детали Friends handler

## ⚡ КРИТИЧЕСКИ ВАЖНО

### Settings Handler УДАЛЕН!
- **Было**: Отдельный SettingsCallbackHandler для настроек
- **Сейчас**: ВСЕ настройки обрабатываются здесь!
- **Паттерн**: `questions_*` callbacks для настроек
- **НЕ создавать**: `settings_*` callbacks (handler не существует!)

### Основная информация
- **Location**: `bot/handlers/callbacks/questions_callbacks.py`
- **Pattern**: `questions_*` 
- **Lines**: ~642 (HIGH priority для рефакторинга)
- **Responsibility**: Вопросы + Настройки пользователей

## 🎯 Поддерживаемые Callbacks

### Settings Operations (ОСНОВНЫЕ)
```python
"questions_toggle_notifications"  # Toggle уведомлений (inline логика)
"questions_show_all"              # Показать все настройки пользователя
```

### Question CRUD Operations
```python
"questions_create:{type}"         # Создание нового вопроса
"questions_edit:{question_id}"    # Редактирование вопроса
"questions_delete:{question_id}"  # Удаление вопроса
"questions_edit_schedule:{id}"    # Редактирование расписания (placeholder)
```

### Question Status Management
```python
"questions_toggle:{question_id}"  # Toggle активности вопроса
"questions_test:{question_id}"    # Отправка тестового вопроса
```

### Template System
```python
"questions_templates_cat:{category}"     # Категории шаблонов
"questions_use_template:{template_id}"   # Использование шаблона
"questions_create_from_template:{id}"    # Создание из шаблона
```

### Navigation
```python
"menu_questions"  # Главное меню вопросов
"questions"       # Alias для menu_questions  
"questions_noop"  # No-operation callback
```

## 🏗️ Архитектура Handler

### can_handle() Logic
```python
def can_handle(self, data: str) -> bool:
    questions_callbacks = {"menu_questions", "questions", "questions_noop"}
    return data in questions_callbacks or data.startswith("questions_")
```

### Routing в handle_callback()
```python
async def handle_callback(self, query, data, translator, context):
    if data in ["menu_questions", "questions"]:
        await self._handle_questions_menu(query, translator)
    elif data == "questions_noop":
        pass  # No-operation
    elif data.startswith("questions_"):
        await self._handle_questions_action(query, data, translator)
```

### Routing в _handle_questions_action()
```python
async def _handle_questions_action(self, query, data, translator):
    # Settings operations (INLINE LOGIC)
    if data == "questions_toggle_notifications":
        # 5 строк inline логики - НЕ отдельный метод!
        
    elif data == "questions_show_all":
        await self._handle_show_all_settings(query, question_manager, translator)
        
    # Question operations (SEPARATE METHODS)
    elif data.startswith("questions_toggle:"):
        await self._handle_toggle_question(query, data, question_manager, translator)
        
    elif data.startswith("questions_test:"):
        await self._handle_test_question(query, data, question_manager, translator)
        
    # ... etc
```

## 💡 Ключевые методы

### _handle_questions_menu() - Главное меню
```python
async def _handle_questions_menu(self, query: CallbackQuery, translator: Translator):
    """Генерирует главное меню вопросов с настройками."""
    
    # 1. Получить данные пользователя
    user_data = await user_ops.get_user_settings(user.id)
    questions_summary = await question_manager.get_user_questions_summary(user.id)
    
    # 2. Сгенерировать клавиатуру с настройками
    keyboard = KeyboardGenerator.questions_menu_keyboard(
        questions_summary, 
        user_data, 
        translator
    )
    
    # 3. Обновить сообщение
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
```

### _handle_show_all_settings() - Все настройки
```python
async def _handle_show_all_settings(self, query, question_manager, translator):
    """Показывает детальные настройки всех вопросов."""
    
    # 1. Собрать все данные
    questions_summary = await question_manager.get_user_questions_summary(user.id)
    user_data = await user_ops.get_user_settings(user.id)
    
    # 2. Сформировать детальный текст
    settings_text = self._format_settings_text(questions_summary, user_data, translator)
    
    # 3. Показать с кнопкой назад
    keyboard = KeyboardGenerator.single_button_keyboard(
        translator.translate("questions.back"), 
        "menu_questions"
    )
```

### _handle_toggle_question() - Toggle статуса вопроса
```python
async def _handle_toggle_question(self, query, data, question_manager, translator):
    """Toggle активности конкретного вопроса."""
    
    # 1. Извлечь question_id
    question_id = int(data.split(":")[1])
    
    # 2. Toggle статуса
    success = await question_manager.question_ops.toggle_question_status(question_id)
    
    # 3. Обновить меню
    if success:
        await self._handle_questions_menu(query, translator)
```

### _handle_test_question() - Тестирование вопроса
```python
async def _handle_test_question(self, query, data, question_manager, translator):
    """Отправляет тестовый вопрос пользователю."""
    
    # 1. Извлечь question_id
    question_id = int(data.split(":")[1])
    
    # 2. Отправить тест
    success = await question_manager.send_test_question(user.id, question_id)
    
    # 3. Показать результат
    if success:
        await query.edit_message_text(translator.translate("questions.test_sent"))
```

## 🔄 Settings Operations (ДЕТАЛЬНО)

### questions_toggle_notifications - ОБРАЗЕЦ INLINE ЛОГИКИ
```python
elif data == "questions_toggle_notifications":
    # ✅ ПРАВИЛЬНО: Всё в 6 строк, НЕ отдельный метод!
    from bot.database.user_operations import UserOperations
    user_ops = UserOperations(self.db_client, self.user_cache)
    user_data = await user_ops.get_user_settings(query.from_user.id)
    current_enabled = user_data.get("enabled", True) if user_data else True
    await user_ops.update_user_settings(query.from_user.id, {"enabled": not current_enabled})
    await self.user_cache.invalidate(f"user_settings_{query.from_user.id}")
    await self._handle_questions_menu(query, translator)
```

### Почему именно inline?
1. **Простая операция** - toggle boolean значения
2. **Нет сложной логики** - просто NOT operation
3. **Избегаем раздувания** handler (уже 642 строки)
4. **Следуем принципу** - отдельные методы только для сложной логики

## 💾 Database Patterns в Handler

### User Settings Pattern
```python
# Стандартная работа с настройками пользователя
from bot.database.user_operations import UserOperations

user_ops = UserOperations(self.db_client, self.user_cache)

# Get
user_data = await user_ops.get_user_settings(user_id)
current_value = user_data.get("setting_key", default_value) if user_data else default_value

# Update  
await user_ops.update_user_settings(user_id, {"setting_key": new_value})

# КРИТИЧНО: Cache invalidation
await self.user_cache.invalidate(f"user_settings_{user_id}")
```

### Question Operations Pattern
```python
# Работа с вопросами через QuestionManager
question_manager = QuestionManager(self.db_client, self.config, self.user_cache)

# Summary для UI
questions_summary = await question_manager.get_user_questions_summary(user_id)

# Direct operations через question_ops
await question_manager.question_ops.toggle_question_status(question_id)
await question_manager.question_ops.get_question_details(question_id)

# Business logic через manager
await question_manager.send_test_question(user_id, question_id)
```

## 🎨 UI Generation Patterns

### Questions Menu Keyboard
```python
# В KeyboardGenerator.questions_menu_keyboard()
keyboard = []

# 1. Global notifications toggle
notif_status = "✅" if notifications_enabled else "❌"
notif_text = translator.translate("questions.notifications_toggle", status=notif_status)
keyboard.append([InlineKeyboardButton(notif_text, callback_data="questions_toggle_notifications")])

# 2. Individual questions
for question in questions:
    status = "✅" if question['active'] else "❌"
    text = f"{status} {question['name']}"
    callback_data = f"questions_toggle:{question['id']}"
    keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])

# 3. Action buttons
keyboard.append([
    InlineKeyboardButton("➕ Создать", callback_data="questions_create"),
    InlineKeyboardButton("📋 Все настройки", callback_data="questions_show_all")
])
```

### Settings Display Format
```python
# В _handle_show_all_settings()
settings_text = f"{translator.translate('questions.all_settings_title')}\n\n"

# Global status
notif_status = "✅ Включены" if notifications_enabled else "❌ Выключены"
settings_text += f"{translator.translate('questions.notifications_status', status=notif_status)}\n\n"

# Questions list
for question in questions:
    status = "✅ Активен" if question['active'] else "❌ Неактивен"
    settings_text += f"• {question['name']} {status}\n"
    settings_text += f"   ⏰ {question['window_start']}-{question['window_end']}\n"
    settings_text += f"   📊 {question['interval_minutes']} мин\n\n"
```

## 🚨 Error Handling Patterns

### Standard Error Template
```python
async def _handle_some_action(self, query, data, question_manager, translator):
    user = query.from_user
    try:
        # Основная логика
        result = await self.risky_operation()
        
        # Success
        await self._handle_questions_menu(query, translator)
        self.logger.info("Action completed", user_id=user.id, action=data)
        
    except (ValueError, IndexError) as e:
        # ID parsing errors
        self.logger.error("Invalid action data", user_id=user.id, data=data, error=str(e))
        await query.edit_message_text(translator.translate("errors.general"))
        
    except Exception as e:
        # General errors
        self.logger.error("Action failed", user_id=user.id, action=data, error=str(e))
        await query.edit_message_text(translator.translate("errors.general"))
```

### Rate Limiting Integration
```python
# Rate limiting автоматически применяется через decorator на router level
# НЕ нужно добавлять rate limiting в handler methods
```

## 🧪 Testing Guidelines

### Test Structure for Questions Handler
```python
@pytest.mark.asyncio
async def test_questions_toggle_notifications():
    # Setup
    handler = QuestionsCallbackHandler(mock_db, mock_config, mock_cache)
    query = create_mock_query(user_id=12345)
    
    # Mock user operations
    mock_user_ops = AsyncMock()
    mock_user_ops.get_user_settings.return_value = {"enabled": True}
    mock_user_ops.update_user_settings.return_value = True
    
    # Execute
    await handler.handle_callback(query, "questions_toggle_notifications", mock_translator, mock_context)
    
    # Assert
    mock_user_ops.update_user_settings.assert_called_with(12345, {"enabled": False})
    handler.user_cache.invalidate.assert_called_with("user_settings_12345")
```

## 📊 Performance Considerations

### Caching Strategy
```python
# User settings: 5-minute TTL
cache_key = f"user_settings_{user_id}"
ttl = 300  # 5 minutes

# Questions summary: 5-minute TTL  
cache_key = f"user_questions_{user_id}"
ttl = 300

# Cache invalidation triggers:
# 1. Settings update → invalidate user_settings_*
# 2. Question changes → invalidate user_questions_*
```

### Database Optimization
```python
# Batch operations для multiple questions
async def bulk_toggle_questions(self, question_ids: List[int]):
    for question_id in question_ids:
        await question_manager.question_ops.toggle_question_status(question_id)
    
    # Single cache invalidation after batch
    await self.user_cache.invalidate(f"user_questions_{user_id}")
```

## 🚫 Common Mistakes

### ❌ ОШИБКА: Создание отдельного метода для toggle
```python
# НЕ ДЕЛАЙ ТАК!
elif data == "questions_toggle_notifications":
    await self._handle_toggle_notifications(query, translator)  # ❌

async def _handle_toggle_notifications(self, query, translator):  # ❌ Лишний метод
    # 5 строк кода в отдельном методе - overkill!
```

### ❌ ОШИБКА: Использование settings_* callbacks
```python
# НЕ ИСПОЛЬЗУЙ!
callback_data = "settings_toggle_notifications"  # ❌ Handler удален!

# ИСПОЛЬЗУЙ:
callback_data = "questions_toggle_notifications"  # ✅ Правильно
```

### ❌ ОШИБКА: Забыть cache invalidation
```python
# НЕ ЗАБЫВАЙ!
await user_ops.update_user_settings(user_id, {"enabled": False})
# ❌ ЗАБЫЛ: await self.user_cache.invalidate(f"user_settings_{user_id}")
```

## 📋 Checklist для нового Callback

### Добавляя новый questions_* callback:
- [ ] Определить тип операции (simple toggle vs complex action)
- [ ] Если simple → inline логика (2-5 строк)
- [ ] Если complex → отдельный метод (только если handler <400 строк)
- [ ] Добавить error handling
- [ ] Добавить logging
- [ ] Добавить cache invalidation если изменяет данные
- [ ] Протестировать callback
- [ ] Обновить handlers-map.md

### Checklist для Settings операций:
- [ ] Использовать questions_* prefix (НЕ settings_*)
- [ ] UserOperations для DB операций
- [ ] Cache invalidation после update
- [ ] Refresh menu после изменений
- [ ] Proper error messages

## 🔄 Future Improvements

### Краткосрочные (1-2 недели):
- [ ] Разбить на smaller methods (файл 642 строки)
- [ ] Вынести UI generation в отдельный класс
- [ ] Добавить валидацию входных данных

### Среднесрочные (1 месяц):
- [ ] Вынести business logic в QuestionService
- [ ] Реализовать command pattern для actions
- [ ] Добавить comprehensive tests

### Долгосрочные (2-3 месяца):
- [ ] Полное разделение Settings и Questions логики
- [ ] Async UI updates без full refresh
- [ ] Advanced caching strategies

---

**Последнее обновление**: 2025-07-15 21:25  
**Источник**: Анализ bot/handlers/callbacks/questions_callbacks.py  
**Следующее обновление**: При изменении QuestionsCallbackHandler
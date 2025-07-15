# ⚡ БЫСТРЫЙ СПРАВОЧНИК

**ОБЯЗАТЕЛЬНО ОБНОВЛЯТЬ** при добавлении новых паттернов!

## 🔄 Добавление новой кнопки

### 1. Keyboard Generation
**File**: `bot/keyboards/keyboard_generators.py`  
**Pattern**: `{handler_prefix}_{action}`

```python
# Примеры ПРАВИЛЬНЫХ callback_data:
"questions_toggle_notifications"  # ✅ 
"friends_send_request"             # ✅
"admin_broadcast_message"          # ✅

# НЕПРАВИЛЬНЫЕ примеры:
"settings_toggle_notifications"   # ❌ settings handler удален!
"toggle_notifications"             # ❌ нет префикса handler
```

### 2. Handler Logic
**File**: `bot/handlers/callbacks/{handler_name}_callbacks.py`  
**Method**: Добавить в `_handle_{handler}_action()` или `handle_callback()`

### 3. Простые Toggle (INLINE логика)
```python
elif data == "questions_toggle_notifications":
    # ✅ ПРАВИЛЬНО: встроенная логика (2-5 строк)
    from bot.database.user_operations import UserOperations
    user_ops = UserOperations(self.db_client, self.user_cache)
    user_data = await user_ops.get_user_settings(query.from_user.id)
    current_enabled = user_data.get("enabled", True) if user_data else True
    await user_ops.update_user_settings(query.from_user.id, {"enabled": not current_enabled})
    await self.user_cache.invalidate(f"user_settings_{query.from_user.id}")
    await self._handle_questions_menu(query, translator)
```

### 4. ❌ НЕПРАВИЛЬНО: Отдельный метод для простого toggle
```python
# ❌ НЕ ДЕЛАТЬ ТАК:
elif data == "questions_toggle_notifications":
    await self._handle_toggle_notifications(query, question_manager, translator)

async def _handle_toggle_notifications(self, query, question_manager, translator):
    # 20+ строк кода для простого toggle
```

## 💾 Database Operations

### User Settings
```python
from bot.database.user_operations import UserOperations
user_ops = UserOperations(self.db_client, self.user_cache)

# Get settings
user_data = await user_ops.get_user_settings(user_id)
current_value = user_data.get("key", default_value) if user_data else default_value

# Update settings  
await user_ops.update_user_settings(user_id, {"key": new_value})

# ОБЯЗАТЕЛЬНО: Invalidate cache
await self.user_cache.invalidate(f"user_settings_{user_id}")
```

### Questions Operations
```python
# Get question manager в handler
question_manager = QuestionManager(self.db_client, self.config, self.user_cache)

# Common operations
await question_manager.get_user_questions_summary(user_id)
await question_manager.question_ops.toggle_question_status(question_id)
```

## 🎯 Decision Tree для New Features

```
Нужен новый callback?
├─ Простой toggle (2-5 строк)? 
│  └─ ✅ Inline в существующий handler
├─ Сложная логика (>10 строк)?
│  ├─ Логика уже существует?
│  │  └─ ✅ Переиспользовать существующий метод
│  └─ ✅ Новый метод в существующий handler
└─ Новый домен/паттерн?
   └─ ⚠️ Новый handler (очень редко!)
```

## 📋 Templates для Copy-Paste

### Inline Toggle Template
```python
elif data == "handler_toggle_something":
    from bot.database.user_operations import UserOperations
    user_ops = UserOperations(self.db_client, self.user_cache)
    user_data = await user_ops.get_user_settings(query.from_user.id)
    current_value = user_data.get("setting_key", True) if user_data else True
    await user_ops.update_user_settings(query.from_user.id, {"setting_key": not current_value})
    await self.user_cache.invalidate(f"user_settings_{query.from_user.id}")
    await self._handle_handler_menu(query, translator)
```

### Callback with ID Template
```python
elif data.startswith("handler_action:"):
    item_id = int(data.split(":")[1])
    # логика с item_id
    await self._handle_handler_menu(query, translator)
```

### Error Handling Template
```python
try:
    # основная логика
    self.logger.info("Action completed", user_id=user.id, action=data)
except Exception as e:
    self.logger.error("Action failed", user_id=user.id, action=data, error=str(e))
    await query.edit_message_text(translator.translate("errors.general"), parse_mode="Markdown")
```

## 🔍 Поиск и Проверка

### Перед добавлением callback:
```bash
# Проверить существующие handlers
grep -r "callback_data.*your_pattern" bot/keyboards/
grep -r "your_pattern" bot/handlers/callbacks/

# Проверить паттерны
grep -r "def.*handle.*your_action" bot/handlers/

# Проверить can_handle методы
grep -r "can_handle" bot/handlers/callbacks/
```

### Найти handler для callback:
```bash
# По паттерну callback
grep -r "startswith.*pattern" bot/handlers/callbacks/
grep -r "pattern.*in.*callbacks" bot/handlers/callbacks/
```

## ⚠️ Частые Ошибки

### ❌ НЕ ДЕЛАТЬ:
1. Создавать `settings_*` callbacks (handler удален!)
2. Отдельные методы для простых toggle
3. Забывать cache invalidation
4. Дублировать существующую логику
5. Не проверять docs/HANDLERS_MAP.md перед добавлением

### ✅ ДЕЛАТЬ:
1. Использовать `questions_*` для настроек
2. Inline логика для простых операций
3. Всегда invalidate cache после DB update
4. Проверять существующие handlers
5. Обновлять документацию при изменениях

## 🧪 Testing

### Быстрая проверка новой кнопки:
1. Найти кнопку в меню
2. Нажать и проверить логи на ошибки
3. Проверить что изменения сохранились
4. Проверить что UI обновился корректно

### Логи для отладки:
```bash
# Найти ошибки callback routing
grep "No handler found" logs/
grep "Unknown callback data" logs/

# Найти ошибки в конкретном handler
grep "handler_name.*error" logs/
```
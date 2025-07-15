# ➕ Пошаговый процесс добавления Callbacks

Детальное руководство по добавлению новых callback handlers без ошибок и дублирования кода.

## 🗺️ Навигация
- ← [../README.md](../README.md) - Назад к карте AI docs
- → [database-operations.md](database-operations.md) - DB операции
- → [error-patterns.md](error-patterns.md) - Обработка ошибок

## 🎯 Алгоритм добавления Callback

### Шаг 1: Планирование (2 мин)
1. **Определить тип операции**:
   - Simple toggle (2-5 строк) → inline логика
   - Complex action (>10 строк) → отдельный метод
   - New domain → новый handler (очень редко!)

2. **Определить handler** по паттерну:
   ```
   questions_* → QuestionsCallbackHandler
   friends_*   → FriendsCallbackHandler  
   admin_*     → AdminCallbackHandler
   feedback_*  → FeedbackCallbackHandler
   menu_*      → NavigationCallbackHandler
   ```

3. **Проверить размер handler**:
   - Если >400 строк → только inline логика
   - Если <400 строк → можно добавить метод

### Шаг 2: Поиск существующего кода (3 мин)
```bash
# Поиск похожей логики
grep -r "similar_operation" bot/handlers/
grep -r "callback_pattern" bot/keyboards/

# Проверка существующих handlers
grep -r "similar_callback" bot/handlers/callbacks/
```

### Шаг 3: Создание кнопки (2 мин)
```python
# В bot/keyboards/keyboard_generators.py
button_text = translator.translate("button.text")
callback_data = "handler_prefix_action_name"  # Следовать паттерну!

# Примеры правильных callback_data:
"questions_toggle_something"
"friends_send_request:123"
"admin_broadcast_message"

# ❌ НЕПРАВИЛЬНО:
"settings_toggle_something"  # Settings handler удален!
"toggle_something"           # Нет префикса handler
```

### Шаг 4: Добавление обработчика (5-15 мин)

#### Для inline логики (простые операции):
```python
# В соответствующем handler файле
elif data == "handler_prefix_simple_action":
    # ✅ Inline логика (2-5 строк)
    from bot.database.user_operations import UserOperations
    user_ops = UserOperations(self.db_client, self.user_cache)
    success = await user_ops.simple_operation(query.from_user.id)
    await self.user_cache.invalidate(f"cache_key_{query.from_user.id}")
    await self._handle_menu_refresh(query, translator)
```

#### Для сложной логики (отдельный метод):
```python
# В роутинге handler
elif data.startswith("handler_prefix_complex:"):
    await self._handle_complex_action(query, data, manager, translator)

# Новый метод в том же файле
async def _handle_complex_action(self, query, data, manager, translator):
    """Handle complex callback action."""
    user = query.from_user
    try:
        # 1. Extract ID если нужно
        item_id = int(data.split(":")[1])
        
        # 2. Основная логика
        result = await manager.complex_operation(user.id, item_id)
        
        # 3. Cache invalidation
        await self.user_cache.invalidate(f"cache_key_{user.id}")
        
        # 4. UI update
        await self._handle_menu_refresh(query, translator)
        
        # 5. Logging
        self.logger.info("Complex action completed", user_id=user.id, item_id=item_id)
        
    except (ValueError, IndexError) as e:
        self.logger.error("Invalid action data", user_id=user.id, data=data, error=str(e))
        await query.edit_message_text(translator.translate("errors.general"))
    except Exception as e:
        self.logger.error("Action failed", user_id=user.id, error=str(e))
        await query.edit_message_text(translator.translate("errors.general"))
```

### Шаг 5: Тестирование (3 мин)
1. **Manual testing**:
   - Найти кнопку в UI
   - Нажать и проверить результат
   - Проверить логи на ошибки

2. **Check logs**:
   ```bash
   # Проверить отсутствие ошибок
   grep "No handler found" logs/
   grep "Unknown.*action" logs/
   ```

### Шаг 6: Документация (2 мин)
1. **Обновить handlers-map.md** если добавлен новый тип callback
2. **Обновить *-specifics.md** если значительные изменения в handler

## 🎨 Паттерны Callback Data

### Naming Convention:
```python
# Простые действия
"{handler}_{action}"
"questions_toggle_notifications"
"friends_discover"

# Действия с ID
"{handler}_{action}:{id}"
"questions_toggle:123"
"friends_remove:456"

# Действия с параметрами
"{handler}_{action}:{param1}:{param2}"
"friends_discover_page:2"
"questions_create_from_template:daily:5"
```

### Handler Prefixes:
- `questions_` - QuestionsCallbackHandler
- `friends_` - FriendsCallbackHandler  
- `admin_` - AdminCallbackHandler
- `feedback_` - FeedbackCallbackHandler
- `menu_`, `back_` - NavigationCallbackHandler

## 💾 Database Operations Checklist

### Для операций изменяющих данные:
- [ ] Использовать соответствующий Operations класс
- [ ] Добавить proper error handling
- [ ] Инвалидировать cache после update
- [ ] Логировать результат операции

### Примеры операций:
```python
# User settings
user_ops = UserOperations(self.db_client, self.user_cache)
await user_ops.update_user_settings(user_id, {"key": value})
await self.user_cache.invalidate(f"user_settings_{user_id}")

# Questions
question_manager = QuestionManager(self.db_client, self.config, self.user_cache)
await question_manager.question_ops.toggle_question_status(question_id)
await self.user_cache.invalidate(f"user_questions_{user_id}")

# Friends
friend_ops = FriendOperations(self.db_client, self.user_cache)
await friend_ops.send_friend_request(user_id, target_user_id)
await self.user_cache.invalidate(f"friends_list_{user_id}")
```

## 🚨 Error Handling Checklist

### Обязательные элементы:
- [ ] try/except блок для основной логики
- [ ] Специфические исключения если известны
- [ ] Общий Exception handler
- [ ] User-friendly error messages
- [ ] Proper logging с context

### Template:
```python
try:
    # Основная логика
    result = await risky_operation()
    
    # Success handling
    await success_ui_update()
    self.logger.info("Operation success", user_id=user.id, result=result)
    
except SpecificError as e:
    await query.edit_message_text(translator.translate("errors.specific"))
    self.logger.warning("Known error", user_id=user.id, error=str(e))
    
except Exception as e:
    await query.edit_message_text(translator.translate("errors.general"))
    self.logger.error("Unexpected error", user_id=user.id, error=str(e))
```

## 🚫 Частые ошибки

### ❌ НЕ ДЕЛАТЬ:
1. **Settings callbacks**: `settings_*` → используй `questions_*`
2. **Забыть cache invalidation** после DB updates
3. **Отдельные методы для простых toggle** (inline логика!)
4. **Добавлять в большие handlers** (>400 строк) сложную логику
5. **Не проверить существующий код** - может дублировать

### ❌ Примеры неправильного кода:
```python
# ПЛОХО: Settings callback (handler удален!)
callback_data = "settings_toggle_notifications"

# ПЛОХО: Нет префикса handler
callback_data = "toggle_notifications"

# ПЛОХО: Отдельный метод для простого toggle
elif data == "simple_toggle":
    await self._handle_simple_toggle(query, translator)  # Лишний метод!

# ПЛОХО: Забыть cache invalidation
await user_ops.update_user_settings(user_id, {"key": value})
# Забыл: await self.user_cache.invalidate(f"user_settings_{user_id}")
```

## ✅ Checklist перед коммитом

### Functionality:
- [ ] Кнопка создана с правильным callback_data
- [ ] Handler добавлен в правильный файл
- [ ] Логика соответствует требованиям
- [ ] Error handling добавлен
- [ ] Cache invalidation добавлен (если нужно)

### Testing:
- [ ] Manual testing пройден успешно
- [ ] Нет ошибок в логах
- [ ] UI обновляется корректно
- [ ] Existing functionality не поломана

### Code Quality:
- [ ] Следует существующим паттернам
- [ ] Proper logging добавлен
- [ ] Translations используются для текстов
- [ ] Код читаемый и maintainable

### Documentation:
- [ ] handlers-map.md обновлен (если нужно)
- [ ] Коммит message описывает изменения

## 🔄 После добавления callback

### Immediate:
- Мониторинг логов на новые ошибки
- User feedback если применимо

### Short-term:
- Добавить unit tests если сложная логика
- Оптимизировать performance если нужно

---

**Последнее обновление**: 2025-07-15 22:00  
**Применимость**: Все новые callback additions  
**Следующее обновление**: При изменении процесса
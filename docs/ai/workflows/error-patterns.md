# 🚨 Типичные ошибки и их решения

Справочник по самым частым ошибкам в разработке и их стандартным решениям.

## 🗺️ Навигация
- ← [database-operations.md](database-operations.md) - DB операции и кеширование  
- ← [adding-callbacks.md](adding-callbacks.md) - Добавление callbacks
- ↗ [../handlers/patterns.md](../handlers/patterns.md) - Общие паттерны handlers

## 🔴 Callback Handler Errors

### ❌ "No handler found for callback: X"
**Причина**: Кнопка создана, но обработчик не добавлен в handlers

**Решение**:
```python
# 1. Найти правильный handler по префиксу
questions_* → QuestionsCallbackHandler
friends_*   → FriendsCallbackHandler
admin_*     → AdminCallbackHandler

# 2. Добавить обработчик
elif data == "callback_name":
    # inline логика для простых операций
    await simple_operation()
    await self._handle_menu_refresh(query, translator)
```

**Профилактика**:
- Использовать docs/ai/workflows/adding-callbacks.md алгоритм
- Проверять logs после каждого добавления кнопки

### ❌ "Unknown questions action: questions_X:Y"
**Причина**: Callback с параметрами не обработан в роутинге

**Решение**:
```python
# Для callbacks с ID
elif data.startswith("questions_action:"):
    action_id = int(data.split(":")[1])
    await self._handle_action(query, action_id, translator)

# Для более сложных параметров  
elif data.startswith("questions_complex:"):
    parts = data.split(":")
    param1, param2 = parts[1], parts[2]
    await self._handle_complex(query, param1, param2, translator)
```

### ❌ "Settings handler removed" errors
**Причина**: Обращение к удаленному settings handler

**Решение**:
```python
# ❌ НЕПРАВИЛЬНО
callback_data = "settings_toggle_notifications"

# ✅ ПРАВИЛЬНО - всё в questions handler
callback_data = "questions_toggle_notifications"
```

## 🗄️ Database Errors

### ❌ Cache не инвалидируется после update
**Причина**: Забыли инвалидировать cache после изменения данных

**Симптомы**: 
- UI показывает старые данные
- Изменения не видны сразу

**Решение**:
```python
# ✅ ОБЯЗАТЕЛЬНО после любого update
await user_ops.update_user_settings(user_id, {"key": value})
await self.user_cache.invalidate(f"user_settings_{user_id}")  # ← КРИТИЧНО!

# Для операций с друзьями - инвалидировать для обеих сторон
await friend_ops.send_friend_request(user1_id, user2_id)
await self.user_cache.invalidate(f"friends_list_{user1_id}")
await self.user_cache.invalidate(f"friend_requests_{user2_id}")
```

### ❌ "'Object' object has no attribute 'method'"
**Причина**: Метод не реализован в соответствующем классе

**Решение**:
```python
# 1. Найти правильный класс
QuestionManager - для questions операций
UserOperations - для user данных  
FriendOperations - для friends операций

# 2. Добавить недостающий метод или использовать правильный
# Вместо question_manager.missing_method()
await question_manager.question_ops.existing_method()
```

### ❌ N+1 Query Problem
**Причина**: Множественные отдельные запросы вместо batch операции

**Симптомы**: Медленная загрузка списков

**Решение**:
```python
# ❌ ПЛОХО: N отдельных запросов
friends_data = []
for friend_id in friend_ids:
    friend = await friend_ops.get_friend(friend_id)  # N queries!
    friends_data.append(friend)

# ✅ ХОРОШО: Один batch запрос
friends_data = await friend_ops.get_multiple_friends(friend_ids)  # 1 query
```

## 🌐 Translation Errors

### ❌ "Key not found in translations"
**Причина**: Используется несуществующий ключ перевода

**Решение**:
```python
# 1. Проверить существующие ключи в bot/i18n/locales/ru.json
# 2. Добавить недостающий ключ
# 3. Использовать fallback для safety

try:
    text = translator.translate("new.key")
except KeyError:
    text = translator.translate("general.error")  # fallback
```

### ❌ Hardcoded strings в коде
**Причина**: Текст интерфейса прописан прямо в коде

**Решение**:
```python
# ❌ НЕПРАВИЛЬНО
await query.edit_message_text("Настройки сохранены")

# ✅ ПРАВИЛЬНО
await query.edit_message_text(translator.translate("settings.saved"))
```

## ⚡ Performance Errors

### ❌ Медленные операции без кеширования
**Причина**: Часто запрашиваемые данные не кешируются

**Решение**:
```python
# ✅ Cache-first pattern
cache_key = f"expensive_data_{user_id}"
cached_data = await self.user_cache.get(cache_key)

if cached_data:
    return cached_data

# Expensive operation только если нет в cache
data = await expensive_database_operation(user_id)
await self.user_cache.set(cache_key, data, ttl=300)
return data
```

### ❌ Blocking операции в handlers
**Причина**: Синхронные операции блокируют event loop

**Решение**:
```python
# ❌ БЛОКИРУЮЩАЯ операция
import time
time.sleep(5)  # Блокирует всё!

# ✅ АСИНХРОННАЯ операция
import asyncio
await asyncio.sleep(5)  # Не блокирует

# ✅ Для CPU-intensive operations
import asyncio
result = await asyncio.to_thread(cpu_intensive_function, data)
```

## 🏗️ Architecture Errors

### ❌ Создание separate методов для simple toggles
**Причина**: Переоптимизация простых операций

**Решение**:
```python
# ❌ ИЗЛИШНЕ сложно для toggle
elif data == "simple_toggle":
    await self._handle_simple_toggle(query, translator)  # Лишний метод!

async def _handle_simple_toggle(self, query, translator):  # Не нужен!
    # 2 строки логики

# ✅ ПРАВИЛЬНО - inline логика
elif data == "simple_toggle":
    success = await simple_operation()
    await self._handle_menu_refresh(query, translator)
```

### ❌ Нарушение size limits файлов
**Причина**: Файлы больше 400 строк

**Решение**:
- Использовать только inline логику для больших файлов
- Планировать рефакторинг через docs/ai/big-tasks/handlers-refactoring.md
- Не добавлять новые методы в файлы >400 строк

## 🔐 Security Errors

### ❌ Missing authorization checks
**Причина**: Не проверяется ownership ресурсов

**Решение**:
```python
# ✅ ОБЯЗАТЕЛЬНАЯ проверка ownership
question_details = await question_ops.get_question_details(question_id)
if not question_details or question_details.get('user_id') != user.id:
    self.logger.warning("Unauthorized access", user_id=user.id, question_id=question_id)
    await query.edit_message_text(translator.translate("errors.unauthorized"))
    return
```

### ❌ Exposure of sensitive data в логах
**Причина**: Логирование secret данных

**Решение**:
```python
# ❌ ОПАСНО
self.logger.info("User data", user_data=user_data)  # Может содержать секреты!

# ✅ БЕЗОПАСНО
self.logger.info("User data updated", user_id=user.id, fields=list(user_data.keys()))
```

## 🧪 Testing Errors

### ❌ No tests для новой функциональности
**Причина**: Забыли написать тесты

**Решение**:
```python
# Добавить тест в tests/
def test_new_feature():
    # Arrange
    setup_data()
    
    # Act  
    result = new_feature_function()
    
    # Assert
    assert result.success == True
    assert result.data is not None
```

### ❌ Tests не покрывают error cases
**Причина**: Тестируется только happy path

**Решение**:
```python
# Тестировать error scenarios
def test_feature_with_invalid_data():
    with pytest.raises(ValidationError):
        new_feature_function(invalid_data)

def test_feature_with_database_error():
    with patch('database.operation') as mock_db:
        mock_db.side_effect = DatabaseError()
        result = new_feature_function()
        assert result.success == False
```

## 🔧 Error Recovery Patterns

### Standard Error Handler Template:
```python
async def standard_error_handler(self, query, translator, operation_name):
    """Универсальный обработчик ошибок для callbacks."""
    try:
        # Основная логика здесь
        result = await risky_operation()
        
        # Success handling
        await self._handle_success_ui_update(query, translator)
        self.logger.info(f"{operation_name} completed", user_id=query.from_user.id)
        
    except ValidationError as e:
        await query.edit_message_text(translator.translate("errors.validation"))
        self.logger.warning(f"{operation_name} validation failed", 
                          user_id=query.from_user.id, error=str(e))
    
    except PermissionError as e:
        await query.edit_message_text(translator.translate("errors.unauthorized"))
        self.logger.warning(f"{operation_name} unauthorized", 
                          user_id=query.from_user.id, error=str(e))
                          
    except DatabaseConnectionError as e:
        await query.edit_message_text(translator.translate("errors.temporary"))
        self.logger.error(f"{operation_name} DB connection failed", 
                        user_id=query.from_user.id, error=str(e))
                        
    except Exception as e:
        await query.edit_message_text(translator.translate("errors.general"))
        self.logger.error(f"{operation_name} unexpected error", 
                        user_id=query.from_user.id, error=str(e))
```

### Retry Pattern для temporary failures:
```python
async def retry_database_operation(operation_func, max_retries=3):
    """Retry pattern для временных ошибок БД."""
    for attempt in range(max_retries):
        try:
            return await operation_func()
        except DatabaseConnectionError as e:
            if attempt == max_retries - 1:
                raise  # Last attempt failed
            self.logger.warning(f"DB retry {attempt + 1}/{max_retries}", error=str(e))
            await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
```

## 📊 Debugging Checklist

### При любой ошибке callback:
- [ ] Проверить logs на точную ошибку
- [ ] Найти callback_data в keyboard_generators.py
- [ ] Найти соответствующий handler по префиксу
- [ ] Проверить startswith/exact match в routing
- [ ] Убедиться что метод существует

### При проблемах с данными:
- [ ] Проверить cache invalidation после updates
- [ ] Проверить ownership authorization
- [ ] Проверить error handling для DB операций
- [ ] Убедиться в правильности async/await

### При performance проблемах:
- [ ] Поиск N+1 queries
- [ ] Проверить cache usage
- [ ] Найти blocking операции
- [ ] Измерить response times

## 🔄 Prevention Strategies

### Перед добавлением новой функциональности:
1. Читать docs/ai/workflows/adding-callbacks.md
2. Проверять docs/ai/handlers/patterns.md
3. Искать похожий existing код
4. Планировать error handling
5. Планировать testing

### Перед коммитом:
1. Проверить logs на новые ошибки
2. Пройти manual testing основных flows
3. Убедиться что cache invalidation добавлен
4. Проверить что translations используются

---

**Последнее обновление**: 2025-07-15 22:15  
**Применимость**: Все error scenarios в разработке  
**Следующее обновление**: При обнаружении новых паттернов ошибок
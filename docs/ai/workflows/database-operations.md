# 💾 Database Operations - Стандартные паттерны

Руководство по работе с базой данных в callback handlers с правильным caching и error handling.

## 🗺️ Навигация  
- ← [adding-callbacks.md](adding-callbacks.md) - Добавление callbacks
- → [error-patterns.md](error-patterns.md) - Обработка ошибок
- ↗ [../handlers/patterns.md](../handlers/patterns.md) - Общие паттерны handlers

## 🏗️ Repository Pattern Architecture

### Основные операционные классы:
```python
# User operations
from bot.database.user_operations import UserOperations

# Friend operations  
from bot.database.friend_operations import FriendOperations

# Question operations (через менеджер)
from bot.questions.question_manager import QuestionManager
```

## 👤 User Operations Patterns

### Basic User Settings Pattern:
```python
async def handle_user_setting_change(self, user_id: int, setting_key: str, new_value: any):
    """Стандартный паттерн изменения настроек пользователя."""
    user_ops = UserOperations(self.db_client, self.user_cache)
    
    try:
        # 1. Get current settings (for validation/comparison)
        current_settings = await user_ops.get_user_settings(user_id)
        
        # 2. Update setting
        success = await user_ops.update_user_settings(user_id, {setting_key: new_value})
        
        if success:
            # 3. КРИТИЧНО: Cache invalidation
            await self.user_cache.invalidate(f"user_settings_{user_id}")
            
            # 4. Logging
            self.logger.info("User setting updated", 
                           user_id=user_id, 
                           setting=setting_key, 
                           old_value=current_settings.get(setting_key) if current_settings else None,
                           new_value=new_value)
            return True
        else:
            self.logger.error("Failed to update user setting", user_id=user_id, setting=setting_key)
            return False
            
    except Exception as e:
        self.logger.error("Error updating user setting", user_id=user_id, error=str(e))
        return False
```

### Toggle Pattern (НАИБОЛЕЕ ЧАСТЫЙ):
```python
# ✅ ПРАВИЛЬНО: Inline toggle в callback handler
elif data == "questions_toggle_notifications":
    from bot.database.user_operations import UserOperations
    user_ops = UserOperations(self.db_client, self.user_cache)
    user_data = await user_ops.get_user_settings(query.from_user.id)
    current_enabled = user_data.get("enabled", True) if user_data else True
    await user_ops.update_user_settings(query.from_user.id, {"enabled": not current_enabled})
    await self.user_cache.invalidate(f"user_settings_{query.from_user.id}")
    await self._handle_questions_menu(query, translator)
```

### User Data Retrieval Pattern:
```python
async def get_user_data_with_defaults(self, user_id: int) -> Dict:
    """Получение данных пользователя с fallback на defaults."""
    user_ops = UserOperations(self.db_client, self.user_cache)
    
    try:
        user_data = await user_ops.get_user_settings(user_id)
        
        # Provide defaults для критических полей
        if not user_data:
            default_data = {
                "enabled": True,
                "language": "ru",
                "timezone": "UTC"
            }
            # Создать пользователя с defaults
            await user_ops.update_user_settings(user_id, default_data)
            return default_data
            
        return user_data
        
    except Exception as e:
        self.logger.error("Error getting user data", user_id=user_id, error=str(e))
        # Return safe defaults
        return {"enabled": True, "language": "ru"}
```

## 👥 Friend Operations Patterns

### Friend Request Pattern:
```python
async def send_friend_request(self, sender_id: int, target_id: int):
    """Отправка запроса в друзья."""
    friend_ops = FriendOperations(self.db_client, self.user_cache)
    
    try:
        # 1. Validation
        if sender_id == target_id:
            return False, "cannot_add_yourself"
            
        # 2. Check existing relationship
        existing = await friend_ops.get_friendship_status(sender_id, target_id)
        if existing:
            return False, "already_friends_or_pending"
        
        # 3. Send request
        success = await friend_ops.send_friend_request(sender_id, target_id)
        
        if success:
            # 4. Cache invalidation для обоих пользователей
            await self.user_cache.invalidate(f"friends_list_{sender_id}")
            await self.user_cache.invalidate(f"friend_requests_{target_id}")
            
            # 5. Logging
            self.logger.info("Friend request sent", 
                           sender_id=sender_id, 
                           target_id=target_id)
            return True, "request_sent"
        else:
            return False, "request_failed"
            
    except Exception as e:
        self.logger.error("Error sending friend request", 
                         sender_id=sender_id, 
                         target_id=target_id, 
                         error=str(e))
        return False, "general_error"
```

### Friends List Retrieval Pattern:
```python
async def get_friends_with_caching(self, user_id: int) -> List[Dict]:
    """Получение списка друзей с эффективным кешированием."""
    friend_ops = FriendOperations(self.db_client, self.user_cache)
    
    # 1. Check cache first
    cache_key = f"friends_list_{user_id}"
    cached_friends = await self.user_cache.get(cache_key)
    
    if cached_friends:
        self.logger.debug("Friends list cache hit", user_id=user_id)
        return cached_friends
    
    try:
        # 2. Fetch from database (оптимизированный запрос)
        friends_list = await friend_ops.get_user_friends(user_id)
        
        # 3. Cache result (5 minutes TTL)
        await self.user_cache.set(cache_key, friends_list, ttl=300)
        
        self.logger.debug("Friends list loaded from DB", 
                         user_id=user_id, 
                         count=len(friends_list))
        return friends_list
        
    except Exception as e:
        self.logger.error("Error loading friends list", user_id=user_id, error=str(e))
        return []  # Return empty list как fallback
```

## ❓ Question Operations Patterns

### Question Manager Pattern:
```python
async def handle_question_operation(self, user_id: int, question_id: int, operation: str):
    """Универсальный паттерн работы с вопросами."""
    question_manager = QuestionManager(self.db_client, self.config, self.user_cache)
    
    try:
        # 1. Validate question ownership
        question_details = await question_manager.question_ops.get_question_details(question_id)
        if not question_details or question_details.get('user_id') != user_id:
            self.logger.warning("Unauthorized question access", 
                              user_id=user_id, 
                              question_id=question_id)
            return False, "unauthorized"
        
        # 2. Perform operation
        if operation == "toggle":
            success = await question_manager.question_ops.toggle_question_status(question_id)
        elif operation == "delete":
            success = await question_manager.question_ops.delete_question(question_id)
        elif operation == "test":
            success = await question_manager.send_test_question(user_id, question_id)
        else:
            return False, "unknown_operation"
        
        if success:
            # 3. Cache invalidation
            await self.user_cache.invalidate(f"user_questions_{user_id}")
            
            # 4. Logging
            self.logger.info("Question operation completed", 
                           user_id=user_id, 
                           question_id=question_id, 
                           operation=operation)
            return True, "success"
        else:
            return False, "operation_failed"
            
    except Exception as e:
        self.logger.error("Question operation error", 
                         user_id=user_id, 
                         question_id=question_id, 
                         operation=operation,
                         error=str(e))
        return False, "general_error"
```

### Questions Summary Pattern:
```python
async def get_questions_summary_cached(self, user_id: int) -> Dict:
    """Получение сводки вопросов с кешированием."""
    question_manager = QuestionManager(self.db_client, self.config, self.user_cache)
    
    # 1. Check cache
    cache_key = f"user_questions_{user_id}"
    cached_summary = await self.user_cache.get(cache_key)
    
    if cached_summary:
        return cached_summary
    
    try:
        # 2. Generate summary (heavy operation)
        summary = await question_manager.get_user_questions_summary(user_id)
        
        # 3. Cache для UI generation (5 minutes)
        await self.user_cache.set(cache_key, summary, ttl=300)
        
        return summary
        
    except Exception as e:
        self.logger.error("Error getting questions summary", user_id=user_id, error=str(e))
        # Return minimal safe summary
        return {
            "default_question": None,
            "custom_questions": [],
            "total_questions": 0
        }
```

## 🔄 Caching Strategies

### Cache Keys Convention:
```python
# User-related caches
f"user_settings_{user_id}"      # User preferences and settings
f"user_profile_{user_id}"       # User profile data

# Questions-related caches  
f"user_questions_{user_id}"     # User's questions summary
f"question_details_{question_id}"  # Individual question details

# Friends-related caches
f"friends_list_{user_id}"       # User's friends list
f"friend_requests_{user_id}"    # Incoming friend requests
f"discovery_{user_id}_{page}"   # Discovery results (shorter TTL)

# System caches
f"user_stats_{user_id}"         # User statistics
f"app_settings"                 # Global app settings
```

### TTL (Time To Live) Guidelines:
```python
# User settings: 5 minutes (frequently accessed, rarely changed)
await self.user_cache.set(f"user_settings_{user_id}", data, ttl=300)

# Friends list: 5 minutes (social data, moderate changes)
await self.user_cache.set(f"friends_list_{user_id}", data, ttl=300)

# Discovery results: 2 minutes (dynamic content)
await self.user_cache.set(f"discovery_{user_id}_{page}", data, ttl=120)

# Friend requests: 1 minute (real-time important)
await self.user_cache.set(f"friend_requests_{user_id}", data, ttl=60)

# Static data: 30 minutes (rarely changes)
await self.user_cache.set("app_settings", data, ttl=1800)
```

### Cache Invalidation Patterns:
```python
# Single user cache invalidation
async def invalidate_user_caches(self, user_id: int, cache_types: List[str]):
    """Централизованная инвалидация кешей пользователя."""
    cache_keys = []
    
    for cache_type in cache_types:
        if cache_type == "settings":
            cache_keys.append(f"user_settings_{user_id}")
        elif cache_type == "questions":
            cache_keys.append(f"user_questions_{user_id}")
        elif cache_type == "friends":
            cache_keys.append(f"friends_list_{user_id}")
            cache_keys.append(f"friend_requests_{user_id}")
    
    for key in cache_keys:
        await self.user_cache.invalidate(key)
    
    self.logger.debug("Caches invalidated", user_id=user_id, types=cache_types)

# Bulk cache invalidation (для операций затрагивающих несколько пользователей)
async def invalidate_friendship_caches(self, user1_id: int, user2_id: int):
    """Инвалидация кешей при изменении дружбы."""
    await self.invalidate_user_caches(user1_id, ["friends"])
    await self.invalidate_user_caches(user2_id, ["friends"])
```

## 🚨 Error Handling для DB Operations

### Database Error Categories:
```python
# 1. Connection errors (temporary)
except DatabaseConnectionError as e:
    self.logger.error("DB connection failed", error=str(e))
    await query.edit_message_text(translator.translate("errors.temporary"))

# 2. Validation errors (user input)
except ValidationError as e:
    self.logger.warning("Validation failed", user_id=user_id, error=str(e))
    await query.edit_message_text(translator.translate("errors.validation"))

# 3. Permission errors (authorization)  
except PermissionError as e:
    self.logger.warning("Permission denied", user_id=user_id, error=str(e))
    await query.edit_message_text(translator.translate("errors.permission"))

# 4. Generic database errors
except Exception as e:
    self.logger.error("Database operation failed", user_id=user_id, error=str(e))
    await query.edit_message_text(translator.translate("errors.general"))
```

### Retry Pattern для temporary failures:
```python
async def db_operation_with_retry(self, operation_func, max_retries=3):
    """Retry pattern для DB операций."""
    for attempt in range(max_retries):
        try:
            return await operation_func()
        except DatabaseConnectionError as e:
            if attempt == max_retries - 1:
                raise
            self.logger.warning(f"DB operation retry {attempt + 1}/{max_retries}", error=str(e))
            await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
```

## 📊 Performance Considerations

### Query Optimization:
```python
# ✅ ХОРОШО: Batch operations
friend_ids = [1, 2, 3, 4, 5]
friends_data = await friend_ops.get_multiple_friends(friend_ids)

# ❌ ПЛОХО: N+1 queries
friends_data = []
for friend_id in friend_ids:
    friend_data = await friend_ops.get_friend(friend_id)  # N отдельных запросов!
    friends_data.append(friend_data)
```

### Cache-First Pattern:
```python
async def get_data_cache_first(self, user_id: int, data_type: str):
    """Always check cache first pattern."""
    # 1. Cache check
    cache_key = f"{data_type}_{user_id}"
    cached_data = await self.user_cache.get(cache_key)
    
    if cached_data:
        return cached_data
    
    # 2. Database fallback
    data = await self.fetch_from_database(user_id, data_type)
    
    # 3. Cache result
    await self.user_cache.set(cache_key, data, ttl=300)
    
    return data
```

## ✅ Checklist для DB Operations

### Перед добавлением DB операции:
- [ ] Использовать правильный Operations класс
- [ ] Добавить error handling
- [ ] Добавить proper logging
- [ ] Определить нужность кеширования

### После успешной операции:
- [ ] Cache invalidation если данные изменились
- [ ] Logging с достаточным context
- [ ] UI update для отражения изменений

### Performance checklist:
- [ ] Избегать N+1 queries
- [ ] Использовать batch operations где возможно
- [ ] Cache frequently accessed data
- [ ] Monitor query performance

---

**Последнее обновление**: 2025-07-15 22:05  
**Применимость**: Все database operations в handlers  
**Следующее обновление**: При изменении DB архитектуры
# 👥 FriendsCallbackHandler - Детальное руководство

Документация по FriendsCallbackHandler - требует срочного рефакторинга из-за размера файла.

## 🗺️ Навигация
- ← [handlers-map.md](handlers-map.md) - Карта всех handlers
- ← [questions-specifics.md](questions-specifics.md) - Детали Questions handler
- ← [patterns.md](patterns.md) - Общие паттерны

## 🚨 КРИТИЧЕСКОЕ СОСТОЯНИЕ

### Статус файла
- **Location**: `bot/handlers/callbacks/friends_callbacks.py`
- **Pattern**: `friends_*`
- **Lines**: ~719 (CRITICAL priority для рефакторинга)
- **Проблема**: Превышает лимит в 400 строк почти в 2 раза!

### ⚠️ ОГРАНИЧЕНИЯ ДО РЕФАКТОРИНГА
- ❌ **НЕ добавлять** новые крупные методы (>10 строк)
- ✅ **МОЖНО добавлять** только inline логику (2-5 строк)
- 📋 **ОБЯЗАТЕЛЬНО** планировать рефакторинг в big-tasks/
- ⚠️ **ПРЕДУПРЕЖДАТЬ** в коммитах о размере файла

## 🎯 Поддерживаемые Callbacks

### Friend Management
```python
"friends_send_request:{user_id}"     # Отправка запроса в друзья
"friends_accept:{request_id}"        # Принятие запроса
"friends_decline:{request_id}"       # Отклонение запроса
"friends_remove:{friend_id}"         # Удаление из друзей
```

### Friend Discovery  
```python
"friends_discover"                   # Поиск новых друзей
"friends_discover_page:{page}"       # Пагинация в поиске
"friends_by_interest:{interest}"     # Поиск по интересам
```

### Friends List Management
```python
"friends_list"                       # Список друзей
"friends_list_page:{page}"          # Пагинация списка
"friends_requests"                   # Входящие запросы
"friends_sent_requests"             # Исходящие запросы
```

### Navigation
```python
"menu_friends"                      # Главное меню друзей
"friends_back_to_main"             # Возврат в главное меню
```

## 🏗️ Архитектура Handler

### can_handle() Logic
```python
def can_handle(self, data: str) -> bool:
    friends_callbacks = {"menu_friends", "friends"}
    return data in friends_callbacks or data.startswith("friends_")
```

### Основные разделы файла
1. **Friend requests** (~150 строк) - запросы в друзья
2. **Friend discovery** (~200 строк) - поиск друзей  
3. **Friends management** (~150 строк) - управление списком
4. **UI generation** (~100 строк) - генерация интерфейса
5. **Helper methods** (~119 строк) - вспомогательные методы

## 💾 Database Operations

### Friend Operations Pattern
```python
from bot.database.friend_operations import FriendOperations

friend_ops = FriendOperations(self.db_client, self.user_cache)

# Отправка запроса
await friend_ops.send_friend_request(user_id, target_user_id)

# Принятие запроса  
await friend_ops.accept_friend_request(request_id)

# Получение списка друзей
friends_list = await friend_ops.get_user_friends(user_id)

# ВАЖНО: Cache invalidation
await self.user_cache.invalidate(f"friends_list_{user_id}")
```

### Discovery Operations (90% faster!)
```python
# Оптимизированный поиск друзей (500ms → 50ms)
discovered_users = await friend_ops.discover_potential_friends(
    user_id, 
    page=page, 
    limit=10
)

# Поиск по интересам
users_by_interest = await friend_ops.find_users_by_interest(
    user_id,
    interest_tag
)
```

## 🎨 UI Generation Patterns

### Friends List Keyboard
```python
# Типичная генерация списка друзей
keyboard = []
for friend in friends_list:
    # Friend info button
    friend_text = f"👤 {friend.name}"
    callback_data = f"friends_profile:{friend.id}"
    keyboard.append([InlineKeyboardButton(friend_text, callback_data=callback_data)])
    
    # Remove friend button
    remove_text = "❌ Удалить"
    remove_callback = f"friends_remove:{friend.id}"
    keyboard.append([InlineKeyboardButton(remove_text, callback_data=remove_callback)])

# Navigation
keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="menu_friends")])
```

### Discovery Pagination
```python
# Пагинация для discovery
def generate_discovery_keyboard(users, current_page, total_pages):
    keyboard = []
    
    # Users list
    for user in users:
        text = f"➕ {user.name}"
        callback_data = f"friends_send_request:{user.id}"
        keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])
    
    # Pagination controls
    nav_buttons = []
    if current_page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"friends_discover_page:{current_page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="friends_noop"))
    
    if current_page < total_pages:
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"friends_discover_page:{current_page+1}"))
        
    keyboard.append(nav_buttons)
    return InlineKeyboardMarkup(keyboard)
```

## ⚡ Performance Considerations

### Caching Strategy
```python
# Friends list: 5-minute TTL
cache_key = f"friends_list_{user_id}"
ttl = 300

# Discovery results: 2-minute TTL (more dynamic)
cache_key = f"discovery_{user_id}_{page}"
ttl = 120

# Friend requests: 1-minute TTL (real-time)
cache_key = f"friend_requests_{user_id}"
ttl = 60
```

### Rate Limiting
```python
# Friends operations имеют специальные лимиты:
"friends": 5/hour           # Friend requests (anti-spam)
"discovery": 3/minute       # Discovery (resource-intensive)
"general": 20/minute        # Other friend operations
```

## 🚨 Common Issues

### Проблемы производительности
1. **N+1 queries** в списке друзей (частично решено)
2. **Heavy discovery operations** (оптимизированы на 90%)
3. **Cache misses** при частых updates

### Проблемы архитектуры
1. **Монолитный файл** - 719 строк (критично!)
2. **Смешанная ответственность** - UI + business logic
3. **Дублирование кода** между методами

## 📋 План рефакторинга (КРИТИЧНО!)

### Разделение на модули (приоритет HIGH):
```
friends_callbacks.py (719 lines) →
├── friends_requests_handler.py    (~200 lines) - запросы в друзья
├── friends_discovery_handler.py   (~200 lines) - поиск друзей  
├── friends_management_handler.py  (~150 lines) - управление списком
└── friends_navigation_handler.py  (~100 lines) - меню и навигация
```

### Service Layer Extraction:
```python
# Вынести business logic в services
class FriendsService:
    async def send_friend_request(self, user_id, target_id)
    async def accept_request(self, request_id)
    async def discover_friends(self, user_id, filters)
    async def get_friends_with_stats(self, user_id)
```

### Command Pattern Implementation:
```python
# Каждая операция = отдельная команда
class SendFriendRequestCommand:
    async def execute(self, user_id, target_id)

class AcceptRequestCommand:
    async def execute(self, request_id)
```

## 🔄 Temporary Workarounds

### Добавление новых callbacks (до рефакторинга):
```python
# ✅ МОЖНО: Простая inline логика
elif data.startswith("friends_simple_action"):
    # 2-3 строки inline кода
    success = await friend_ops.simple_operation(user_id)
    await self._refresh_friends_menu(query, translator)

# ❌ НЕ ДОБАВЛЯТЬ: Новые крупные методы
# await self._handle_complex_friend_operation(query, data, translator)  # НЕТ!
```

### Error Handling Template:
```python
async def existing_method_with_error_handling(self, ...):
    try:
        # Существующая логика
        result = await self.existing_operation()
        
        # Success handling
        await self._refresh_friends_menu(query, translator)
        self.logger.info("Friends operation completed", user_id=user.id)
        
    except FriendOperationError as e:
        # Specific error
        await query.edit_message_text(translator.translate("friends.operation_failed"))
        self.logger.warning("Friends operation failed", user_id=user.id, error=str(e))
        
    except Exception as e:
        # General error  
        await query.edit_message_text(translator.translate("errors.general"))
        self.logger.error("Unexpected friends error", user_id=user.id, error=str(e))
```

## 🧪 Testing Strategy

### Приоритеты тестирования:
1. **Core operations** - send/accept/decline requests
2. **Discovery algorithm** - performance и correctness
3. **Cache invalidation** - консистентность данных
4. **Rate limiting** - anti-spam protection

### Test Structure:
```python
# Тестировать по функциональным областям
test_friends_requests.py      # Friend request operations
test_friends_discovery.py     # Discovery algorithm
test_friends_management.py    # Friends list management
test_friends_ui.py           # UI generation and navigation
```

## 📊 Metrics и Monitoring

### Performance Metrics:
- **Discovery time**: 50ms (было 500ms) ✅
- **Friends list load**: <100ms ✅  
- **Request processing**: <200ms ✅
- **Cache hit rate**: 85%+ ✅

### Error Rates:
- **Friend request failures**: <1% ✅
- **Discovery timeouts**: <0.1% ✅
- **Cache misses**: <15% ✅

## 🚫 What NOT to Do

### ❌ НЕ добавлять в существующий файл:
- Новые крупные методы (>10 строк)
- Новые сложные features без рефакторинга
- Дополнительные UI generation методы

### ❌ НЕ игнорировать:
- Rate limiting для friend requests
- Cache invalidation после updates  
- Error handling для всех operations

### ❌ НЕ делать:
- Прямые DB queries (использовать FriendOperations)
- Hardcoded user messages (использовать translator)
- Операции без logging

## 📋 Immediate Actions Required

### До любых изменений:
1. **Создать big-tasks/friends-refactoring.md**
2. **Планировать разбиение файла**
3. **Добавлять только критически необходимые фичи**
4. **Предупреждать в коммитах** о размере файла

### При работе с friends callbacks:
1. **Проверить существующий код** - избежать дублирования
2. **Использовать inline логику** для простых операций
3. **Добавить proper error handling**
4. **Инвалидировать кеш** после изменений
5. **Логировать все операции**

---

**Последнее обновление**: 2025-07-15 21:35  
**Статус файла**: 🚨 CRITICAL - требует немедленного рефакторинга  
**Следующее действие**: Создать план рефакторинга в big-tasks/
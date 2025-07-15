# 🎯 Полная карта Callback Handlers

**ОБЯЗАТЕЛЬНО обновлять** при изменении handlers! Этот файл - источник истины для всех callback обработчиков.

## 🗺️ Навигация
- ← [docs/ai/README.md](../README.md) - Назад к карте AI docs
- → [patterns.md](patterns.md) - Общие паттерны handlers
- → [questions-specifics.md](questions-specifics.md) - Детали QuestionsCallbackHandler
- → [friends-specifics.md](friends-specifics.md) - Детали FriendsCallbackHandler

## 📊 Обзор всех Handlers

| Handler | Pattern | Lines | Priority | Status |
|---------|---------|-------|----------|--------|
| QuestionsCallbackHandler | `questions_*` | ~642 | HIGH | ⚠️ Needs refactoring |
| FriendsCallbackHandler | `friends_*` | ~719 | CRITICAL | ⚠️ Needs refactoring |
| AdminCallbackHandler | `admin_*` | ~537 | HIGH | ⚠️ Needs refactoring |
| FeedbackCallbackHandler | `feedback_*` | ~200 | LOW | ✅ Good |
| NavigationCallbackHandler | `menu_*`, `back_*` | ~150 | LOW | ✅ Good |

## 🎯 Детальное описание Handlers

### QuestionsCallbackHandler ⭐ (ОСНОВНОЙ)
**Pattern**: `questions_*`  
**Location**: `bot/handlers/callbacks/questions_callbacks.py`  
**Lines**: ~642 (HIGH priority для рефакторинга)

#### КРИТИЧНО: Обрабатывает ВСЕ настройки!
- **Settings menu УДАЛЕНО** - все настройки здесь!
- **Pattern**: `questions_toggle_notifications`, `questions_show_all`
- **НЕ используй**: `settings_*` callbacks (handler удален!)

#### Поддерживаемые callbacks:
- ✅ `questions_toggle_notifications` - **встроенная логика** (НЕ отдельный метод!)
- ✅ `questions_show_all` - показать все настройки пользователя
- ✅ `questions_create:*`, `questions_edit:*`, `questions_delete:*` - CRUD операции
- ✅ `questions_edit_schedule:*` - редактирование расписания (placeholder)
- ✅ `questions_toggle:*` - toggle статуса вопросов (active/inactive)
- ✅ `questions_test:*` - тестирование вопросов (отправка test question)
- ✅ `questions_templates_cat:*` - категории шаблонов вопросов
- ✅ `questions_use_template:*` - использование готовых шаблонов
- ✅ `questions_create_from_template:*` - создание из шаблона

#### Важные правила:
1. **Простые toggle** - делать inline (2-5 строк), НЕ отдельные методы
2. **Settings operations** - обрабатывать здесь, не создавать SettingsHandler
3. **Cache invalidation** - ОБЯЗАТЕЛЬНО после DB updates
4. **Error handling** - использовать translator для сообщений

#### Методы для изучения:
- `_handle_questions_menu()` - главное меню вопросов
- `_handle_questions_action()` - роутинг по типам action
- `_handle_show_all_settings()` - показ всех настроек
- `_handle_toggle_question()` - toggle статуса вопроса
- `_handle_test_question()` - тестирование вопроса

### FriendsCallbackHandler ⚠️ (ТРЕБУЕТ РЕФАКТОРИНГА)
**Pattern**: `friends_*`  
**Location**: `bot/handlers/callbacks/friends_callbacks.py`  
**Lines**: ~719 (CRITICAL priority для рефакторинга)

#### Поддерживаемые callbacks:
- ✅ `friends_*` - все операции с друзьями
- ⚠️ **СЛИШКОМ БОЛЬШОЙ ФАЙЛ** - требует разбиения

#### Статус рефакторинга:
- 🚨 **CRITICAL**: Файл превышает лимит в 400 строк почти в 2 раза
- 📋 **План**: Разбить на smaller handlers или модули
- ⚠️ **Ограничения**: НЕ добавлять новые крупные методы

### AdminCallbackHandler ⚠️ (ТРЕБУЕТ РЕФАКТОРИНГА) 
**Pattern**: `admin_*`  
**Location**: `bot/handlers/callbacks/admin_callbacks.py`  
**Lines**: ~537 (HIGH priority для рефакторинга)

#### Поддерживаемые callbacks:
- ✅ `admin_*` - административные функции
- ⚠️ **БОЛЬШОЙ ФАЙЛ** - приближается к лимиту

#### Статус рефакторинга:
- ⚠️ **HIGH**: Файл превышает лимит в 400 строк
- 📋 **План**: Разбить админ функции по доменам
- ⚠️ **Ограничения**: Добавлять только inline логику

### FeedbackCallbackHandler ✅ (ХОРОШО)
**Pattern**: `feedback_*`  
**Location**: `bot/handlers/callbacks/feedback_callbacks.py`  
**Lines**: ~200 (LOW priority)

#### Поддерживаемые callbacks:
- ✅ `feedback_*` - система обратной связи
- ✅ GitHub Issues integration
- ✅ Три типа фидбека: bug_report, feature_request, general

#### Статус:
- ✅ **ХОРОШО**: Размер в пределах нормы
- ✅ **МОДУЛЬНО**: Четкое разделение ответственности
- 💚 **МОЖНО РАСШИРЯТЬ**: Есть место для новых фич

### NavigationCallbackHandler ✅ (ХОРОШО)
**Pattern**: `menu_*`, `back_*`  
**Location**: `bot/handlers/callbacks/navigation_callbacks.py`  
**Lines**: ~150 (LOW priority)

#### Поддерживаемые callbacks:
- ✅ `menu_*` - навигация по меню (menu_main, menu_questions, etc.)
- ✅ `back_*` - кнопки возврата (back_to_main, etc.)

#### Статус:
- ✅ **ОТЛИЧНО**: Компактный и функциональный
- ✅ **СТАБИЛЬНО**: Редко требует изменений
- 💚 **ОБРАЗЕЦ**: Хороший пример для других handlers

## 🔍 Алгоритм поиска Handler для Callback

### 1. По паттерну callback_data:
```python
# Определение handler по префиксу
if callback_data.startswith("questions_"):
    return QuestionsCallbackHandler
elif callback_data.startswith("friends_"):
    return FriendsCallbackHandler  
elif callback_data.startswith("admin_"):
    return AdminCallbackHandler
elif callback_data.startswith("feedback_"):
    return FeedbackCallbackHandler
elif callback_data.startswith(("menu_", "back_")):
    return NavigationCallbackHandler
```

### 2. Через CallbackRouter:
```python
# В bot/handlers/base/callback_router.py
def find_handler(self, data: str) -> Optional[BaseCallbackHandler]:
    for handler in self.handlers:
        if handler.can_handle(data):  # ← Проверка паттерна
            return handler
    return None
```

### 3. Метод can_handle в каждом handler:
```python
# Пример из QuestionsCallbackHandler
def can_handle(self, data: str) -> bool:
    questions_callbacks = {"menu_questions", "questions", "questions_noop"}
    return data in questions_callbacks or data.startswith("questions_")
```

## 🚨 Частые ошибки и решения

### ❌ ОШИБКА: "No handler found for callback"
**Причины**:
1. Callback pattern не соответствует ни одному handler
2. Кнопка создана с неправильным callback_data
3. Handler не зарегистрирован в router

**Решение**:
1. Проверить паттерн callback_data в keyboard generation
2. Убедиться что handler поддерживает этот паттерн
3. Проверить регистрацию handler в main.py

### ❌ ОШИБКА: "Unknown action in handler"
**Причины**:
1. Handler найден, но action не обрабатывается
2. Новый callback добавлен без обработчика
3. Опечатка в callback_data

**Решение**:
1. Добавить обработку в `handle_callback()` или `_handle_*_action()`
2. Проверить логику роутинга внутри handler

### ❌ ОШИБКА: Settings callbacks не работают
**Причина**: Settings handler УДАЛЕН!

**Решение**: Использовать `questions_*` callbacks вместо `settings_*`

## 🔄 Процесс добавления нового Callback

### Для простого toggle (рекомендуется):
1. **Определить handler** по паттерну callback_data
2. **Добавить inline логику** (2-5 строк) в существующий handler
3. **НЕ создавать** отдельный метод

### Для сложной логики:
1. **Проверить** существующие методы (избежать дублирования)
2. **Если handler >400 строк** - НЕ добавлять крупные методы
3. **Добавить новый метод** только если really necessary
4. **Планировать рефакторинг** большого handler

### Для нового домена:
1. **Убедиться** что нельзя использовать существующий handler
2. **Создать новый handler** только в крайнем случае
3. **Следовать паттерну** BaseCallbackHandler
4. **Обновить** этот файл (handlers-map.md)

## ⚠️ Правила для Больших Handlers

### Если handler >400 строк (FriendsCallback, AdminCallback):
- ❌ **НЕ добавлять** новые крупные методы (>10 строк)
- ✅ **МОЖНО добавлять** inline логику (2-5 строк)
- ✅ **ПЛАНИРОВАТЬ** рефакторинг в big-tasks/
- ⚠️ **ПРЕДУПРЕЖДАТЬ** в коммитах о размере файла

### Стратегии рефакторинга:
1. **Разбить по доменам** (friends → requests, discovery, management)
2. **Вынести в service layer** (business logic → services/)
3. **Использовать command pattern** (каждая операция = отдельный класс)

## 📋 TODO для улучшения Handlers

### Краткосрочные (1-2 недели):
- [ ] Разбить FriendsCallbackHandler (719 lines → 3 smaller handlers)
- [ ] Разбить AdminCallbackHandler (537 lines → 2 smaller handlers)  
- [ ] Добавить недостающие error handlers из логов

### Среднесрочные (1 месяц):
- [ ] Вынести business logic в service layer
- [ ] Реализовать command pattern для сложных операций
- [ ] Добавить comprehensive tests для всех handlers

### Долгосрочные (2-3 месяца):
- [ ] Полная миграция к модульной архитектуре
- [ ] Автоматическое обнаружение missing handlers
- [ ] Performance оптимизация handler routing

## 📊 Метрики Handlers (обновлено: 2025-07-15)

### По размеру файлов:
```
FriendsCallbackHandler:    719 lines  🚨 CRITICAL
QuestionsCallbackHandler:  642 lines  ⚠️  HIGH  
AdminCallbackHandler:      537 lines  ⚠️  HIGH
FeedbackCallbackHandler:   ~200 lines ✅  GOOD
NavigationCallbackHandler: ~150 lines ✅  GOOD
```

### По приоритету рефакторинга:
1. **🚨 CRITICAL**: FriendsCallbackHandler (719 lines)
2. **⚠️ HIGH**: QuestionsCallbackHandler (642 lines)  
3. **⚠️ HIGH**: AdminCallbackHandler (537 lines)
4. **✅ GOOD**: FeedbackCallbackHandler, NavigationCallbackHandler

### По стабильности:
- **Стабильные**: Navigation, Feedback
- **Часто изменяемые**: Questions, Friends, Admin
- **Проблемные**: Friends (много legacy кода)

---

**Последнее обновление**: 2025-07-15 21:15  
**Источник данных**: Анализ кодовой базы, git history, логи ошибок  
**Следующее обновление**: При изменении handlers или добавлении новых
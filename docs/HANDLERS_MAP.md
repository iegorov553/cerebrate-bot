# 🎯 КАРТА ОБРАБОТЧИКОВ

**ВАЖНО**: Этот файл ОБЯЗАТЕЛЬНО обновлять при изменении handlers!

## Callback Handlers Registry

### QuestionsCallbackHandler ⭐
**Pattern**: `questions_*`  
**Location**: `bot/handlers/callbacks/questions_callbacks.py`  
**Lines**: ~642 (HIGH priority для рефакторинга)

**Handles**:
- ✅ `questions_toggle_notifications` - встроенная логика (НЕ отдельный метод!)
- ✅ `questions_show_all` - показать все настройки  
- ✅ `questions_create:*`, `questions_edit:*`, `questions_delete:*`
- ✅ `questions_edit_schedule:*` - редактирование расписания (placeholder)
- ✅ `questions_toggle:*` - toggle статуса вопросов
- ✅ `questions_test:*` - тестирование вопросов
- ✅ `questions_templates_cat:*` - категории шаблонов
- ✅ `questions_use_template:*` - использование шаблонов

**Important Notes**:
- **Settings toggles обрабатываются здесь** (НЕ в отдельном SettingsHandler!)
- Простые toggle делать inline, НЕ отдельными методами

### FriendsCallbackHandler ⚠️
**Pattern**: `friends_*`  
**Location**: `bot/handlers/callbacks/friends_callbacks.py`  
**Lines**: ~719 (CRITICAL priority для рефакторинга)

**Handles**:
- ✅ `friends_*` - все операции с друзьями
- ⚠️ Требует рефакторинга - слишком большой файл

### AdminCallbackHandler ⚠️
**Pattern**: `admin_*`  
**Location**: `bot/handlers/callbacks/admin_callbacks.py`  
**Lines**: ~537 (HIGH priority для рефакторинга)

**Handles**:
- ✅ `admin_*` - административные функции

### FeedbackCallbackHandler ✅
**Pattern**: `feedback_*`  
**Location**: `bot/handlers/callbacks/feedback_callbacks.py`

**Handles**:
- ✅ `feedback_*` - система обратной связи
- ✅ GitHub Issues integration

### NavigationCallbackHandler ✅
**Pattern**: `menu_*`, `back_*`  
**Location**: `bot/handlers/callbacks/navigation_callbacks.py`

**Handles**:
- ✅ `menu_*` - навигация по меню
- ✅ `back_*` - кнопки назад

## ⚠️ DEPRECATED/REMOVED

### ❌ SettingsCallbackHandler - УДАЛЕН!
- **Было**: Отдельный handler для settings_*
- **Сейчас**: Все настройки в QuestionsCallbackHandler
- **НЕ СОЗДАВАТЬ**: settings_* callbacks
- **ИСПОЛЬЗОВАТЬ**: questions_* callbacks для настроек

## 🔍 Поиск Handler для Callback

### Алгоритм определения handler:
1. `questions_*` → QuestionsCallbackHandler
2. `friends_*` → FriendsCallbackHandler  
3. `admin_*` → AdminCallbackHandler
4. `feedback_*` → FeedbackCallbackHandler
5. `menu_*`, `back_*` → NavigationCallbackHandler

### Если нужен новый callback:
1. **Простой toggle (2-3 строки)** → Добавить inline в существующий handler
2. **Сложная логика** → Добавить новый метод в существующий handler
3. **Новый домен** → Создать новый handler (редко!)

## 📊 Статистика Handlers (обновлено: 2025-07-15)

| Handler | Lines | Priority | Status |
|---------|-------|----------|--------|
| FriendsCallbackHandler | 719 | CRITICAL | Требует рефакторинга |
| QuestionsCallbackHandler | 642 | HIGH | Требует рефакторинга |
| AdminCallbackHandler | 537 | HIGH | Требует рефакторинга |
| FeedbackCallbackHandler | ~200 | LOW | ✅ Хорошо |
| NavigationCallbackHandler | ~150 | LOW | ✅ Хорошо |

## 🚨 Правила для Больших Handlers

### Если handler >400 строк:
1. ❌ НЕ добавлять новые крупные методы
2. ✅ Добавлять только inline логику (2-3 строки)
3. ✅ Планировать рефакторинг

### Перед добавлением нового метода:
1. Проверить существующие методы
2. Убедиться что логика не дублируется
3. Рассмотреть inline реализацию
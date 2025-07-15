# ⚙️ Рефакторинг больших Callback Handlers

## Статус: 📋 Планируется
**Приоритет**: CRITICAL  
**Ожидаемое время**: 2-3 часа (несколько сессий)  
**Зависимости**: callback-cleanup.md завершен

## 🎯 Цель задачи
Разбить монолитные callback handlers на модульные компоненты согласно принципу единственной ответственности и лимиту 400 строк на файл.

## 🚨 КРИТИЧЕСКАЯ ПРОБЛЕМА

### Текущее состояние:
```
FriendsCallbackHandler:    719 lines  🚨 CRITICAL (179% лимита)
QuestionsCallbackHandler:  642 lines  ⚠️  HIGH     (160% лимита)  
AdminCallbackHandler:      537 lines  ⚠️  HIGH     (134% лимита)
```

### Проблемы:
- **Нарушение принципа SRP** - один класс делает слишком много
- **Сложность поддержки** - трудно найти нужный код
- **Высокий риск конфликтов** - много людей меняют один файл
- **Тестирование** - сложно покрыть тестами монолит

## ✅ Чеклист выполнения

### Фаза 1: FriendsCallbackHandler (719 → 4×~180 lines)
#### Анализ и планирование (30 мин)
- [ ] Проанализировать структуру friends_callbacks.py
- [ ] Определить границы модулей по functionality
- [ ] Создать схему разбиения на 4 handler
- [ ] Спланировать миграцию shared code

#### Разбиение FriendsCallbackHandler (90 мин)
- [ ] Создать FriendsRequestsHandler (~200 lines)
  - send_request, accept_request, decline_request
  - incoming/outgoing requests management
- [ ] Создать FriendsDiscoveryHandler (~200 lines)  
  - discover_friends, pagination, filters
  - by_interest, by_location поиск
- [ ] Создать FriendsManagementHandler (~150 lines)
  - friends_list, remove_friend, friend_profile
  - friends statistics и management
- [ ] Создать FriendsNavigationHandler (~100 lines)
  - menu_friends, navigation между разделами
  - back buttons, breadcrumbs

#### Интеграция и тестирование (30 мин)
- [ ] Обновить router регистрацию handlers
- [ ] Добавить shared utilities если нужно
- [ ] Протестировать все friends операции
- [ ] Обновить документацию handlers

### Фаза 2: QuestionsCallbackHandler (642 → 3×~215 lines)
#### Анализ и планирование (20 мин)
- [ ] Проанализировать структуру questions_callbacks.py
- [ ] Учесть что settings integrated в questions
- [ ] Определить логическое разделение

#### Разбиение QuestionsCallbackHandler (60 мин)
- [ ] Создать QuestionsSettingsHandler (~200 lines)
  - questions_toggle_notifications, show_all_settings
  - user preferences, global question settings
- [ ] Создать QuestionsCRUDHandler (~220 lines)
  - create, edit, delete, toggle questions
  - question management operations  
- [ ] Создать QuestionsTemplatesHandler (~200 lines)
  - templates_cat, use_template, create_from_template
  - template system и question generation

#### Интеграция и тестирование (20 мин)
- [ ] Обновить router для questions handlers
- [ ] Протестировать settings operations
- [ ] Протестировать CRUD operations
- [ ] Обновить документацию

### Фаза 3: AdminCallbackHandler (537 → 2×~270 lines)
#### Анализ и планирование (15 мин)
- [ ] Проанализировать admin_callbacks.py
- [ ] Определить границы по admin functionality

#### Разбиение AdminCallbackHandler (45 мин)
- [ ] Создать AdminSystemHandler (~270 lines)
  - system operations, monitoring, health checks
  - database operations, maintenance
- [ ] Создать AdminUsersHandler (~270 lines)
  - user management, moderation
  - broadcast, announcements

#### Интеграция и тестирование (15 мин)
- [ ] Обновить router для admin handlers
- [ ] Протестировать admin operations
- [ ] Обновить документацию

### Фаза 4: Финализация (30 мин)
- [ ] Удалить старые монолитные файлы
- [ ] Обновить imports во всех зависимых файлах
- [ ] Обновить все AI documentation
- [ ] Запустить полный набор тестов
- [ ] Провести final review архитектуры

## 🏗️ Архитектура после рефакторинга

### Новая структура handlers:
```
bot/handlers/callbacks/
├── friends/
│   ├── friends_requests_handler.py     (~200 lines)
│   ├── friends_discovery_handler.py    (~200 lines)
│   ├── friends_management_handler.py   (~150 lines)
│   └── friends_navigation_handler.py   (~100 lines)
├── questions/
│   ├── questions_settings_handler.py   (~200 lines)
│   ├── questions_crud_handler.py       (~220 lines)
│   └── questions_templates_handler.py  (~200 lines)
├── admin/
│   ├── admin_system_handler.py         (~270 lines)
│   └── admin_users_handler.py          (~270 lines)
├── feedback_callbacks.py               (~200 lines) ✅ Good
└── navigation_callbacks.py             (~150 lines) ✅ Good
```

### Shared Components:
```
bot/handlers/shared/
├── base_handler.py           # BaseCallbackHandler
├── callback_router.py        # CallbackRouter
└── handler_utils.py          # Shared utilities
```

## 🎯 Критерии успеха

### Функциональные:
- ✅ Все файлы ≤400 строк (target ~200-250)
- ✅ Все existing functionality сохранена
- ✅ Все тесты проходят без изменений
- ✅ Performance не деградировал

### Архитектурные:
- ✅ Четкое разделение ответственности
- ✅ Minimal coupling между handlers
- ✅ Shared code вынесен в utilities
- ✅ Consistent patterns между модулями

### Качественные:
- ✅ Код легче читать и поддерживать
- ✅ Новые features легче добавлять
- ✅ Тестирование стало проще
- ✅ Документация актуализирована

## 🚨 Риски и митигация

### Риск: Поломка existing functionality
**Митигация**:
- Поэтапная миграция по одному handler
- Comprehensive testing после каждого этапа
- Сохранение backup версий
- Rollback plan готов

### Риск: Performance regression
**Митигация**:
- Benchmark существующих операций
- Не менять core logic, только структуру
- Monitoring после deployment
- Optimization при необходимости

### Риск: Увеличение complexity routing
**Митигация**:
- Четкие паттерны для новых handlers
- Документация routing logic
- Автоматические тесты router
- Fallback mechanisms

### Риск: Conflicts с parallel development
**Митигация**:
- Координация с командой
- Atomic commits по этапам
- Clear communication о changes
- Feature freeze период при рефакторинге

## 🔧 Implementation Strategy

### Подход "Strangler Fig Pattern":
1. **Создать новые handlers** рядом со старыми
2. **Постепенно переносить functionality**
3. **Обновлять router по частям**
4. **Удалять старые handlers** когда всё перенесено

### Shared Code Strategy:
```python
# bot/handlers/shared/handler_utils.py
class HandlerUtilities:
    @staticmethod
    async def standard_error_handler(query, translator, error):
        """Unified error handling."""
        
    @staticmethod  
    async def invalidate_user_cache(cache, user_id, cache_types):
        """Unified cache invalidation."""
        
    @staticmethod
    def extract_id_from_callback(data, separator=":"):
        """Unified ID extraction."""
```

### Router Update Strategy:
```python
# Поэтапная регистрация новых handlers
# Фаза 1: Friends
router.register_handler(FriendsRequestsHandler(...))
router.register_handler(FriendsDiscoveryHandler(...))
router.register_handler(FriendsManagementHandler(...))
router.register_handler(FriendsNavigationHandler(...))

# Фаза 2: Questions  
router.register_handler(QuestionsSettingsHandler(...))
router.register_handler(QuestionsCRUDHandler(...))
router.register_handler(QuestionsTemplatesHandler(...))
```

## 🧪 Testing Strategy

### Pre-refactoring:
- [ ] Создать comprehensive test suite для existing functionality
- [ ] Benchmark performance всех операций
- [ ] Документировать все edge cases

### During refactoring:
- [ ] Unit tests для каждого нового handler
- [ ] Integration tests для cross-handler operations
- [ ] Regression tests для existing features

### Post-refactoring:
- [ ] Full end-to-end testing
- [ ] Performance comparison
- [ ] Load testing с новой архитектурой

## 📊 Ожидаемые метрики после рефакторинга

### File Sizes:
```
До:  3 файла × 400+ строк = монолиты
После: 9 файлов × ~200 строк = модули

FriendsCallbackHandler 719 → 4×~175 = 700 строк всего
QuestionsCallbackHandler 642 → 3×~215 = 645 строк всего  
AdminCallbackHandler 537 → 2×~270 = 540 строк всего
```

### Maintainability:
- **Cyclomatic complexity**: Снижение на 60%
- **Coupling**: Снижение на 70%
- **Cohesion**: Увеличение на 80%

### Development velocity:
- **Time to find code**: -50%
- **Time to add features**: -30%
- **Merge conflicts**: -60%

## 📋 Dependencies и Prerequisites

### До начала рефакторинга:
- ✅ callback-cleanup.md завершен
- ✅ Все existing bugs исправлены
- ✅ Comprehensive test coverage
- ✅ Performance baseline established

### External dependencies:
- Coordination с другими developers
- Code freeze период для major files
- Backup strategy готов

## 📝 Документация Updates

### Обновить после завершения:
- [ ] docs/ai/handlers/handlers-map.md - новая структура
- [ ] docs/ai/handlers/*-specifics.md - разделить по новым handlers
- [ ] docs/ai/project-facts.md - архитектурные изменения
- [ ] README.md - новая структура файлов

## 📊 Прогресс

**Статус**: 📋 Планируется (ждет завершения callback-cleanup)  
**Завершено**: 0% (0/25 major пунктов)

**Estimated timeline**:
- **Фаза 1 (Friends)**: 2.5 часа
- **Фаза 2 (Questions)**: 1.5 часа  
- **Фаза 3 (Admin)**: 1.25 часа
- **Фаза 4 (Finalization)**: 0.5 часа
- **Total**: ~6 часов (распределить на несколько дней)

## 🔄 Post-refactoring Tasks

### Immediate (same day):
- Monitoring логов на errors
- Performance monitoring
- User feedback collection

### Short-term (1 week):
- Optimization opportunities
- Documentation improvements  
- Team training на новую структуру

### Long-term (1 month):
- Architecture review
- Additional modularization opportunities
- Lessons learned documentation

---

**Последнее обновление**: 2025-07-15 21:50  
**Приоритет**: 🚨 CRITICAL - файлы превышают лимиты в 2 раза  
**Следующее действие**: Ждать завершения callback-cleanup, затем начать Фазу 1
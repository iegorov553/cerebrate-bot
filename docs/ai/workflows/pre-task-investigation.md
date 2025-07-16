# 🔍 Pre-Task Investigation Protocol

Обязательный протокол исследования перед началом любой задачи.

## 🎯 Цель протокола

Предотвратить 53% всех проблем разработки через систематическое изучение существующего кода и архитектуры.

## 📋 Checklist обязательных действий

### 1. Изучение документации (5 минут)
- [ ] Прочитать [docs/ai/project-facts.md](../project-facts.md)
- [ ] Проверить [docs/ai/forbidden-actions.md](../forbidden-actions.md) на ограничения
- [ ] Найти релевантные файлы в [docs/ai/handlers/](../handlers/)

### 2. Поиск аналогичных решений (10 минут)
```bash
# Поиск patterns в коде
grep -r "pattern" bot/ --include="*.py" -A 3 -B 3

# Для callback handlers
grep -r "callback_data" bot/keyboards/
grep -r "can_handle" bot/handlers/callbacks/

# Для database операций
grep -r "async def.*get_" bot/database/
grep -r "async def.*update_" bot/database/

# Для configuration
grep -r "Config" bot/ --include="*.py"
```

### 3. Анализ архитектуры (5 минут)
- [ ] Проверить существующие ConversationHandler patterns
- [ ] Изучить handler priorities и groups
- [ ] Понять взаимодействие компонентов

### 4. Warning Analysis (5 минут)
```bash
# Запуск в clean environment
python3 -c "import bot; print('Import OK')"

# Проверка на baseline warnings
python3 -m pytest tests/test_handlers_integration.py::TestHandlerIntegration::test_callback_handlers_registration -v

# Запись baseline warnings для сравнения
python3 your_command 2>&1 | grep -i warning > baseline_warnings.txt
```

## 🔄 Специализированные протоколы

### Для Callback Handlers
```bash
# 1. Полный аудит существующих handlers
find bot/handlers/callbacks/ -name "*.py" -exec grep -l "can_handle" {} \;

# 2. Анализ keyboard generators
grep -r "InlineKeyboardButton" bot/keyboards/ -A 2 -B 2

# 3. Проверка ConversationHandler patterns
find . -name "*conversation*" -type f -exec grep -l "ConversationHandler" {} \;

# 4. Анализ handler priorities
grep -r "add_handler.*group=" bot/
```

### Для Database Operations
```bash
# 1. Поиск существующих операций
grep -r "async def" bot/database/ | grep -E "(get_|update_|delete_|create_)"

# 2. Анализ cache patterns
grep -r "cache.*invalidate" bot/
grep -r "TTLCache" bot/

# 3. Проверка authorization patterns
grep -r "user_id.*!=" bot/database/
grep -r "PermissionError" bot/
```

### Для API Integrations
```bash
# 1. Поиск существующих integrations
grep -r "aiohttp" bot/
grep -r "async.*session" bot/

# 2. Анализ error handling patterns
grep -r "except.*Exception" bot/ -A 3 -B 1

# 3. Проверка timeout patterns
grep -r "asyncio.wait_for" bot/
grep -r "timeout" bot/
```

## 🕐 Планирование времени

### Распределение времени на исследование (25% от общего времени задачи):
- **Документация**: 20% исследования (5% от общего времени)
- **Поиск аналогов**: 40% исследования (10% от общего времени)
- **Анализ архитектуры**: 20% исследования (5% от общего времени)
- **Warning analysis**: 20% исследования (5% от общего времени)

### Примеры для разных типов задач:
- **Простая задача (30 мин)**: 7 минут исследования
- **Средняя задача (1 час)**: 15 минут исследования
- **Сложная задача (2 часа)**: 30 минут исследования

## 📊 Checklist результатов исследования

### После завершения исследования должно быть понимание:
- [ ] Существуют ли аналогичные решения в коде?
- [ ] Какие архитектурные ограничения нужно учесть?
- [ ] Какие patterns использовать для реализации?
- [ ] Какие warnings могут возникнуть и как их избежать?
- [ ] Какие тесты нужно написать?
- [ ] Какие edge cases нужно обработать?

### Критерии готовности к реализации:
- [ ] Найдены 2-3 аналогичных решения в коде
- [ ] Понятна архитектура взаимодействия компонентов
- [ ] Выявлены potential conflicts с существующим кодом
- [ ] Составлен план тестирования
- [ ] Оценены risks и potential issues

## 🚫 Частые ошибки в исследовании

### 1. Поверхностный поиск
```bash
# ❌ Неправильно - слишком узкий поиск
grep "exact_string" bot/

# ✅ Правильно - широкий поиск с контекстом
grep -r "pattern" bot/ --include="*.py" -A 3 -B 3
```

### 2. Игнорирование warnings
```bash
# ❌ Неправильно - не читать warnings
python3 command > output.txt 2>&1

# ✅ Правильно - анализировать warnings
python3 command 2>&1 | tee output.txt
grep -i warning output.txt
```

### 3. Недостаточное понимание архитектуры
```bash
# ❌ Неправильно - смотреть только один файл
cat bot/handlers/callbacks/admin_callbacks.py

# ✅ Правильно - понимать полную картину
find bot/handlers/ -name "*.py" -exec grep -l "admin" {} \;
grep -r "admin" bot/keyboards/
```

## 📈 Метрики успешности

### Индикаторы качественного исследования:
- Найдено 3+ аналогичных решений
- Выявлены все архитектурные ограничения
- Понятны все warnings и их причины
- Составлен realistic план реализации

### Индикаторы недостаточного исследования:
- Нет аналогичных решений в коде
- Неожиданные conflicts при реализации
- Неожиданные warnings
- Необходимость переписывания кода

## 🔄 Continuous Improvement

### После каждой задачи:
- [ ] Добавить новые patterns в документацию
- [ ] Обновить forbidden-actions.md если найдены новые ограничения
- [ ] Создать templates для частых операций
- [ ] Улучшить search commands для будущих задач

---

**Статус**: Обязательно к применению  
**Последнее обновление**: 2025-07-16 16:40  
**Применимость**: Все задачи разработки без исключений
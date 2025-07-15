# 🔧 Исправление Callback Handlers

## Статус: 📋 Готов к запуску  
**Приоритет**: HIGH  
**Ожидаемое время**: 45 минут  
**Зависимости**: ai-documentation-restructure.md (почти завершен)

## 🎯 Цель задачи
Устранить все ошибки callback handlers из production логов и обеспечить полное покрытие всех кнопок обработчиками.

## 📋 Проблемы из логов

### Исправлено ранее ✅
- ~~`Unknown questions action: questions_edit_schedule:5`~~ - добавлен placeholder handler
- ~~`'QuestionManager' object has no attribute 'send_test_question'`~~ - добавлен метод
- ~~`No handler found for callback: settings_toggle_notifications`~~ - исправлен на questions_*

### Требует проверки 🔍
- **Missing handlers**: Могут быть другие кнопки без обработчиков
- **Placeholder implementations**: Нужно реализовать полную логику для placeholders
- **Error handling**: Улучшить обработку ошибок в существующих handlers

## ✅ Чеклист выполнения

### Этап 1: Аудит кнопок и callbacks (15 мин)
- [ ] Найти все кнопки в keyboard_generators.py
- [ ] Сопоставить с handlers в callback files
- [ ] Создать список missing handlers
- [ ] Проверить логи за последние дни на новые ошибки

### Этап 2: Реализация missing handlers (20 мин)
- [ ] Добавить обработчики для найденных missing callbacks
- [ ] Реализовать placeholder logic для questions_edit_schedule
- [ ] Добавить error handling для edge cases
- [ ] Следовать паттернам из docs/ai/handlers/patterns.md

### Этап 3: Улучшение существующих handlers (10 мин)
- [ ] Улучшить error messages с переводами
- [ ] Добавить proper logging для всех операций  
- [ ] Стандартизировать error handling patterns
- [ ] Проверить cache invalidation во всех операциях

## 🔍 План аудита

### Поиск всех callback_data в keyboards:
```bash
# Найти все кнопки
grep -r "callback_data=" bot/keyboards/ | grep -o '"[^"]*"' > all_callbacks.txt

# Найти все обработчики
grep -r "startswith\|in.*callbacks" bot/handlers/callbacks/ > all_handlers.txt

# Сравнить списки
```

### Проверка логов на missing handlers:
```bash
# Поиск ошибок callback routing
grep "No handler found" logs/ | tail -20
grep "Unknown.*action" logs/ | tail -20
grep "callback.*error" logs/ | tail -20
```

## 🎯 Критерии успеха

### Функциональные:
- ✅ Все кнопки имеют working handlers
- ✅ Нет ошибок "No handler found" в логах  
- ✅ Нет ошибок "Unknown action" в логах
- ✅ Все placeholder handlers имеют basic implementation

### Качественные:
- ✅ Consistent error handling across all handlers
- ✅ Proper logging для всех callback operations
- ✅ User-friendly error messages с переводами
- ✅ Cache invalidation там где нужно

## 🚨 Риски и митигация

### Риск: Поломка существующих handlers
**Митигация**: 
- Минимальные изменения в working code
- Тестирование каждого callback после изменений
- Rollback plan готов

### Риск: Missing edge cases
**Митигация**:
- Systematic audit всех кнопок
- Проверка production логов
- Добавление general error handling

### Риск: Performance impact
**Митигация**:
- Использовать inline логику для простых операций
- Не добавлять тяжелые операции без caching
- Следовать существующим паттернам

## 📊 Ожидаемые находки

### Вероятные missing handlers:
- Questions: schedule editing, advanced settings
- Friends: complex discovery operations
- Admin: некоторые административные функции
- Navigation: edge case меню

### Типичные проблемы:
- Кнопки добавлены, handlers забыты
- Placeholder handlers без implementation
- Неконсистентный error handling
- Missing translations для error messages

## 🔧 Implementation Guidelines

### Для простых missing handlers:
```python
elif data == "simple_callback":
    # Inline логика (2-5 строк)
    success = await simple_operation()
    await refresh_menu_method(query, translator)
```

### Для сложных missing handlers:
```python
elif data.startswith("complex_callback:"):
    await self._handle_complex_callback(query, data, translator)

async def _handle_complex_callback(self, query, data, translator):
    try:
        # Полная implementation
        result = await complex_operation()
        self.logger.info("Operation completed", user_id=user.id)
    except Exception as e:
        self.logger.error("Operation failed", user_id=user.id, error=str(e))
        await query.edit_message_text(translator.translate("errors.general"))
```

### Error handling template:
```python
try:
    # Основная логика
    await main_operation()
except SpecificError as e:
    await query.edit_message_text(translator.translate("errors.specific"))
    self.logger.warning("Known error", user_id=user.id, error=str(e))
except Exception as e:
    await query.edit_message_text(translator.translate("errors.general"))
    self.logger.error("Unexpected error", user_id=user.id, error=str(e))
```

## 🧪 Testing Plan

### Manual Testing:
- [ ] Пройти по всем меню и нажать каждую кнопку
- [ ] Проверить что нет ошибок в логах
- [ ] Убедиться что UI обновляется корректно

### Automated Checks:
- [ ] Запустить существующие тесты
- [ ] Добавить тесты для новых handlers если нужно
- [ ] Проверить что все callback_data имеют handlers

## 📝 Документация updates

### Обновить при завершении:
- [ ] docs/ai/handlers/handlers-map.md - добавить новые handlers
- [ ] docs/ai/handlers/*-specifics.md - если изменены major handlers
- [ ] Этот файл - отметить completion

## 📊 Прогресс

**Статус**: 📋 Готов к запуску после завершения ai-documentation-restructure  
**Завершено**: 0% (0/13 пунктов чеклиста)

## 🔄 Следующие шаги после завершения
1. Мониторинг логов в течение дня
2. Исправление любых новых проблем  
3. Запуск handlers-refactoring.md для больших файлов

## 💡 Важные заметки
- **Приоритет inline логике** для простых операций
- **Избегать новых методов** в больших handlers (>400 строк)
- **Следовать паттернам** из docs/ai/handlers/patterns.md
- **Обновлять документацию** при значительных изменениях

---

**Последнее обновление**: 2025-07-15 21:45  
**Готов к запуску**: После завершения ai-documentation-restructure  
**Следующая задача**: handlers-refactoring.md
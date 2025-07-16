# 🤖 AI Development Documentation

Модульная документация для Claude Code - структурированные инструкции для эффективной разработки без дублирования кода.

## 🗺️ Карта документации

### 📋 Основные файлы
- **[project-facts.md](project-facts.md)** - Критические факты о проекте (≤800 строк)
- **[forbidden-actions.md](forbidden-actions.md)** - Что НЕ делать + примеры ошибок
- **[retro.md](retro.md)** - Ретроспектива разработки (анализ коммитов)

### 🎯 Handlers (Callback обработчики)
- **[handlers/handlers-map.md](handlers/handlers-map.md)** - Полная карта всех handlers
- **[handlers/patterns.md](handlers/patterns.md)** - Общие паттерны и подходы
- **[handlers/questions-specifics.md](handlers/questions-specifics.md)** - Особенности QuestionsCallbackHandler
- **[handlers/friends-specifics.md](handlers/friends-specifics.md)** - Особенности FriendsCallbackHandler
- **[handlers/callback-development.md](handlers/callback-development.md)** - Workflow разработки callback handlers

### 📊 Крупные задачи и планирование
- **[big-tasks/README.md](big-tasks/README.md)** - Трекер всех больших задач
- **[big-tasks/ai-documentation-restructure.md](big-tasks/ai-documentation-restructure.md)** - 🔄 Текущая: Реструктуризация документации
- **[big-tasks/callback-cleanup.md](big-tasks/callback-cleanup.md)** - 📋 Следующая: Исправление callback errors
- **[big-tasks/handlers-refactoring.md](big-tasks/handlers-refactoring.md)** - 📋 Планируется: Рефакторинг больших handlers

### ⚙️ Процессы и workflows
- **[workflows/adding-callbacks.md](workflows/adding-callbacks.md)** - Пошаговый процесс добавления callbacks
- **[workflows/database-operations.md](workflows/database-operations.md)** - Стандартные DB операции
- **[workflows/error-patterns.md](workflows/error-patterns.md)** - Типичные ошибки и решения
- **[workflows/pre-task-investigation.md](workflows/pre-task-investigation.md)** - Протокол исследования перед задачей
- **[workflows/warning-management.md](workflows/warning-management.md)** - Систематическая обработка warnings
- **[workflows/process-improvements.md](workflows/process-improvements.md)** - Анализ ретроспектив и улучшения

## 🎯 Как использовать эту документацию

### Для новой задачи:
1. **[CLAUDE.md](../CLAUDE.md)** → алгоритм + критические факты
2. **[workflows/pre-task-investigation.md](workflows/pre-task-investigation.md)** → обязательный протокол исследования
3. **[project-facts.md](project-facts.md)** → детальная информация о проекте
4. **[handlers/handlers-map.md](handlers/handlers-map.md)** → найти нужный handler
5. **[workflows/](workflows/)** → пошаговый процесс выполнения

### Для большой задачи:
1. **[big-tasks/README.md](big-tasks/README.md)** → проверить существующие планы
2. Создать новый файл в **big-tasks/** если нужно
3. Следовать чеклисту задачи

### Для коммита:
1. Обновить соответствующие файлы в **docs/ai/**
2. Обновить **big-tasks/** если завершена крупная задача

## 🏗️ Принципы архитектуры AI docs

### ✅ Что мы делаем правильно:
- **Модульность** - каждый файл отвечает за свою область
- **Навигация** - быстрый переход между связанными темами
- **Планирование** - большие задачи описываются детально
- **Актуальность** - алгоритмы обновления встроены в процесс

### 🚫 Чего мы избегаем:
- **Дублирования** - информация хранится в одном месте
- **Перегрузки** - каждый файл ≤800 строк
- **Устаревания** - четкие процедуры обновления
- **Templates** - живые примеры вместо мертвых шаблонов

## 📊 Статистика документации

| Категория | Файлов | Статус |
|-----------|--------|--------|
| Основные | 3 | ✅ Завершено |
| Handlers | 5 | 🔄 В разработке |
| Big Tasks | 4 | ✅ Завершено |
| Workflows | 6 | ✅ Завершено |
| **Всего** | **18** | **75% готово** |

## 🔄 Текущий прогресс

### ✅ Завершено
- [x] Структура папок создана
- [x] CLAUDE.md сокращен до навигатора (54 строки)
- [x] big-tasks/ai-documentation-restructure.md создан
- [x] docs/ai/README.md создан (этот файл)
- [x] Все 3 топ-приоритетных улучшения процесса внедрены:
  - [x] Pre-Task Investigation Checklist
  - [x] Handler Development Workflow
  - [x] Warning Management System
- [x] Обновлены forbidden-actions.md с новыми чеклистами
- [x] Создана полная система workflow документации

### 🔄 В работе
- [ ] Тестирование новых процессов на практике
- [ ] Мониторинг эффективности улучшений

## 🚀 Roadmap

### Фаза 1: Основа (сегодня)
- Создать все основные файлы
- Мигрировать информацию из старых docs
- Протестировать навигацию

### Фаза 2: Наполнение (по мере работы)
- Добавлять новые big-tasks по мере появления
- Расширять handlers-specifics при работе с кодом
- Пополнять workflows при решении типовых задач

### Фаза 3: Оптимизация (постоянно)
- Рефакторинг разросшихся файлов
- Улучшение навигации
- Автоматизация обновлений

---

**Последнее обновление**: 2025-07-16 16:50  
**Следующая задача**: Мониторинг эффективности новых процессов
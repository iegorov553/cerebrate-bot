# 📚 Документация Doyobi Diary

Эта папка содержит всю техническую документацию проекта **Doyobi Diary** - современного Telegram-бота для отслеживания активности с enterprise-архитектурой.

## 📁 Структура документации

### 🏗️ Архитектура и разработка
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Детальная архитектура системы
  - Hybrid modular architecture (75% миграции завершено)
  - Компоненты и паттерны проектирования
  - Диаграммы потоков данных
  - Планы миграции к полностью модульной структуре

### 🤖 AI Development (Claude Code)
- **[ai/README.md](ai/README.md)** - Карта AI документации (НОВАЯ СТРУКТУРА)
  - Модульная структура руководств для ИИ
  - Пошаговые алгоритмы и паттерны
  - Управление большими задачами
- **[ai/project-facts.md](ai/project-facts.md)** - Критические факты проекта
  - Текущее состояние архитектуры
  - Важные ограничения и правила
  - Migration status (75% завершена)
- **[ai/forbidden-actions.md](ai/forbidden-actions.md)** - Что НЕЛЬЗЯ делать
  - Критические запреты и анти-паттерны
  - Security и performance ограничения
  - Предупреждающие знаки для остановки

### 🚀 Развертывание и настройка
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Полное руководство по развертыванию
  - Railway (bot hosting) и Vercel (web app)
  - Supabase (PostgreSQL) настройка
  - GitHub Actions CI/CD pipeline
  - Переменные окружения и секреты
  - Мониторинг и health checks


### 🌍 Интернационализация и UX
- **[I18N_GUIDE.md](I18N_GUIDE.md)** - Система переводов
  - 3 языка: Русский, Английский, Испанский
  - Автоопределение языка пользователя
  - Шаблоны с переменными
  - Добавление новых языков

### ⚡ Производительность и мониторинг
- **[PERFORMANCE.md](PERFORMANCE.md)** - Оптимизация производительности
  - 90% ускорение поиска друзей
  - 80% ускорение UI через TTL кеширование
  - SQL оптимизации и N+1 устранение
  - Performance benchmarks и targets

- **[MONITORING.md](MONITORING.md)** - Система мониторинга
  - Sentry интеграция для error tracking
  - Structured logging с correlation IDs
  - Health checks и system metrics
  - Alerting и incident response

### 🧪 Тестирование и качество
- **[TESTING.md](TESTING.md)** - Стратегия тестирования
  - 25+ автоматических тестов (60%+ coverage)
  - Unit, integration, и performance тесты
  - Мокирование зависимостей
  - CI/CD интеграция



## 🎯 Быстрый старт по документации

### Для разработчиков
1. Начните с **[../CLAUDE.md](../CLAUDE.md)** - навигатор для Claude Code
2. Читайте **[ai/project-facts.md](ai/project-facts.md)** - критические факты
3. Изучите **[ARCHITECTURE.md](ARCHITECTURE.md)** - архитектуру системы
4. Настройте окружение по **[DEPLOYMENT.md](DEPLOYMENT.md)**
5. Ознакомьтесь с **[TESTING.md](TESTING.md)** - стратегией тестирования

### Для DevOps
1. **[DEPLOYMENT.md](DEPLOYMENT.md)** - production deployment
2. **[MONITORING.md](MONITORING.md)** - мониторинг и алерты

### Для product managers
1. **[../README.md](../README.md)** - обзор функциональности
2. **[PERFORMANCE.md](PERFORMANCE.md)** - достижения производительности
3. **[I18N_GUIDE.md](I18N_GUIDE.md)** - поддержка языков

## 🔗 Связанные файлы проекта

### В корне проекта
- **[../README.md](../README.md)** - Основная документация пользователя
  - Функциональность и возможности
  - Инструкции по установке
  - Примеры использования
  
- **[../CLAUDE.md](../CLAUDE.md)** - Техническая документация для разработки
  - Архитектурные компоненты
  - Development guidelines
  - Code patterns и standards

- **[../REFACTORING_PLAN.md](../REFACTORING_PLAN.md)** - План рефакторинга
  - Файлы требующие разделения
  - Приоритеты и временные рамки
  - Architecture evolution strategy

### Конфигурационные файлы
- **[../pyproject.toml](../pyproject.toml)** - Python tools configuration
- **[../pytest.ini](../pytest.ini)** - Testing configuration  
- **[../requirements.txt](../requirements.txt)** - Dependencies
- **[../Dockerfile](../Dockerfile)** - Container setup

## 📊 Статус документации

### ✅ Полностью актуальные
- ARCHITECTURE.md - обновлен с modular components
- DEPLOYMENT.md - включает Railway/Vercel setup
- TESTING.md - отражает текущую test suite
- I18N_GUIDE.md - актуальная i18n система

### 🔄 Все файлы актуальны
Документация полностью обновлена и соответствует текущему состоянию проекта.

## 🤝 Контрибуция в документацию

При добавлении новых функций:
1. Обновите соответствующие .md файлы
2. Добавьте примеры кода и конфигурации
3. Обновите архитектурные диаграммы если нужно
4. Проверьте ссылки между документами

### Стандарты документации
- Используйте GitHub Flavored Markdown
- Добавляйте code examples с syntax highlighting
- Включайте диаграммы для сложных концепций
- Структурируйте с помощью заголовков и списков
- Всегда указывайте актуальные пути к файлам
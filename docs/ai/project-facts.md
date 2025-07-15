# 📋 Критические факты о проекте

Детальная информация о Doyobi Diary для эффективной разработки без ошибок.

## 🏗️ Архитектура системы

### Hybrid Modular Architecture (75% миграции завершено)
- **Новые компоненты**: Полностью модульные в `/bot/` директории
- **Legacy handlers**: Постепенно рефакторятся в модули
- **Backward compatibility**: Поддерживается во время переходного периода

### Основные паттерны
- **Repository Pattern**: Data access через `bot/database/` модули
- **Dependency Injection**: Конфигурация и сервисы через конструкторы
- **Handler Pattern**: BaseCallbackHandler → специализированные классы
- **Strategy Pattern**: Множественные стратегии rate limiting
- **Factory Pattern**: Создание сервисов и schedulers
- **Command Pattern**: Архитектура handlers
- **Observer Pattern**: Event-driven уведомления scheduler

## 🎯 Callback Handlers System

### КРИТИЧЕСКИ ВАЖНО: Settings Menu УДАЛЕНО!
- **Было**: Отдельное меню settings с собственными handlers
- **Сейчас**: Все настройки интегрированы в questions menu
- **Handler**: QuestionsCallbackHandler обрабатывает все настройки
- **Pattern**: Используй `questions_*` callbacks, НЕ `settings_*`

### Паттерны Callback Data
```
questions_*     → QuestionsCallbackHandler  (настройки + вопросы)
friends_*       → FriendsCallbackHandler
admin_*         → AdminCallbackHandler  
feedback_*      → FeedbackCallbackHandler
menu_*, back_*  → NavigationCallbackHandler
```

### Routing механизм
1. **CallbackRouter** получает callback query
2. Вызывает `can_handle(data)` у каждого handler
3. Первый подходящий handler обрабатывает запрос
4. Если handler не найден → логируется warning + fallback

### Важные методы handlers
- `can_handle(data: str) -> bool` - проверка совместимости
- `handle_callback(query, data, translator, context)` - основная логика
- `execute(query, data, context)` - entry point из router

## 💾 Database Layer

### Repository Pattern Implementation
- **UserOperations**: `bot/database/user_operations.py`
- **FriendOperations**: `bot/database/friend_operations.py`  
- **QuestionOperations**: `bot/database/question_operations.py`
- **DatabaseClient**: `bot/database/client.py` - connection pooling

### Типичные операции
```python
# User Settings (ЧАСТО ИСПОЛЬЗУЕТСЯ)
from bot.database.user_operations import UserOperations
user_ops = UserOperations(self.db_client, self.user_cache)
user_data = await user_ops.get_user_settings(user_id)
await user_ops.update_user_settings(user_id, {"key": value})

# ОБЯЗАТЕЛЬНО: Cache invalidation после DB updates
await self.user_cache.invalidate(f"user_settings_{user_id}")
```

### Performance Optimizations
- **Connection pooling**: Автоматическое управление соединениями
- **SQL functions**: Сложные операции (friends-of-friends) в БД
- **90% improvement**: Friend discovery (500ms → 50ms)

## ⚡ Caching System

### TTL Cache (`bot/cache/ttl_cache.py`)
- **TTL**: 5 минут для user settings
- **Auto-cleanup**: Background очистка expired entries
- **Memory efficient**: Ограничения размера
- **80% performance boost**: UI operations

### Ключи кеша
```python
f"user_settings_{user_id}"     # Настройки пользователя
f"user_questions_{user_id}"    # Вопросы пользователя  
f"friends_list_{user_id}"      # Список друзей
```

### КРИТИЧНО: Cache Invalidation
```python
# После ЛЮБОГО DB update:
await self.user_cache.invalidate(cache_key)

# Типичные сценарии:
# 1. Toggle notifications
await user_ops.update_user_settings(user_id, {"enabled": not enabled})
await self.user_cache.invalidate(f"user_settings_{user_id}")

# 2. Question changes  
await question_ops.update_question(question_id, data)
await self.user_cache.invalidate(f"user_questions_{user_id}")
```

## 🚦 Rate Limiting System

### Multi-Tier Rate Limits (`bot/utils/rate_limiter.py`)
```python
# Action-specific limits:
"general": 20/minute        # Общие команды
"friends": 5/hour          # Friend requests (anti-spam)
"discovery": 3/minute      # Discovery (resource-intensive)  
"voice": 10/hour           # Voice messages (API costs)
"feedback": 3/hour         # Feedback (GitHub API)
"admin": 50/minute         # Admin operations
"callback": 30/minute      # Callback queries
```

### Алгоритм
- **Sliding window**: Справедливое распределение
- **User isolation**: Изоляция между пользователями
- **Graceful degradation**: Мягкие лимиты с предупреждениями

## 🌍 Internationalization

### Система переводов (`bot/i18n/`)
- **3 языка**: Русский (default), English, Spanish
- **Auto-detection**: Из Telegram user preferences
- **Template variables**: Поддержка параметров
- **Fallback**: На русский при отсутствии перевода

### Использование
```python
from bot.i18n.translator import Translator
translator = Translator()
await translator.set_language(user_id)  # Auto-detect

# With parameters
text = translator.translate("questions.interval_minutes", minutes=120)
# → "Интервал: 120 минут"
```

### Структура файлов
```
bot/i18n/locales/
├── ru.json    # Русский (базовый)
├── en.json    # English
└── es.json    # Español
```

## 🎤 Voice Recognition System

### Multi-Provider Architecture (`bot/services/whisper_client.py`)
1. **Primary**: Groq whisper-large-v3 (30s timeout)
2. **Fallback**: Groq whisper-large-v3-turbo (30s timeout)  
3. **Final**: OpenAI whisper-1 (60s timeout)

### Intelligent Fallback
- **Rate limit detection**: Автоматическое переключение
- **Admin notifications**: Уведомления о переключениях
- **Smart caching**: Кеширование для всех провайдеров
- **Graceful degradation**: Работа при недоступности сервисов

### Configuration
```bash
# Environment variables
GROQ_API_KEY="gsk_your_groq_key"
OPENAI_API_KEY="sk_your_openai_key"
GROQ_PRIMARY_MODEL="whisper-large-v3"
GROQ_FALLBACK_MODEL="whisper-large-v3-turbo"
```

## 🔧 Configuration Management

### Dataclass-based Config (`bot/config.py`)
```python
@dataclass
class Config:
    # Required
    telegram_bot_token: str
    supabase_url: str
    supabase_service_role_key: str
    
    # Optional with defaults
    admin_user_id: Optional[int] = None
    groq_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    
    # Feature flags
    def is_groq_enabled(self) -> bool
    def is_voice_recognition_enabled(self) -> bool
```

### Environment Variables
```bash
# Required
TELEGRAM_BOT_TOKEN="your_bot_token"
SUPABASE_URL="your_supabase_url" 
SUPABASE_SERVICE_ROLE_KEY="your_service_key"

# Optional
ADMIN_USER_ID="your_telegram_id"
SENTRY_DSN="your_sentry_dsn"
GITHUB_FEEDBACK_TOKEN="your_github_token"
```

## 📝 Question Management System

### QuestionManager (`bot/questions/question_manager.py`)
- **Business logic**: Высокоуровневая логика вопросов
- **Versioning**: Система версионирования вопросов
- **Validation**: Проверка данных вопросов
- **Reply tracking**: Отслеживание ответов

### Question Operations (`bot/database/question_operations.py`)
- **CRUD operations**: Create, Read, Update, Delete
- **Status management**: Active/Inactive вопросы
- **Scheduling**: Управление расписанием
- **User association**: Связь пользователь-вопрос

### Типичные операции
```python
question_manager = QuestionManager(self.db_client, self.config, self.user_cache)

# Get summary
summary = await question_manager.get_user_questions_summary(user_id)

# Toggle status
await question_manager.question_ops.toggle_question_status(question_id)

# Send test question
await question_manager.send_test_question(user_id, question_id)
```

## 🔄 Background Services

### Scheduler Service (`bot/services/scheduler_service.py`)
- **APScheduler integration**: Интеграция с APScheduler
- **Job management**: Управление фоновыми задачами
- **Error handling**: Обработка ошибок в jobs

### Multi-Question Scheduler (`bot/services/multi_question_scheduler.py`)
- **Individual schedules**: Персональные расписания пользователей
- **Question rotation**: Ротация вопросов
- **Time window management**: Управление временными окнами

### Health Service (`bot/services/health_service.py`)
- **System monitoring**: Мониторинг компонентов системы
- **Health checks**: Проверки работоспособности
- **Metrics collection**: Сбор метрик производительности

## 🎨 UI Generation

### Keyboard Generator (`bot/keyboards/keyboard_generators.py`)
- **Inline keyboards**: Генерация inline клавиатур
- **Dynamic content**: Динамическое содержимое кнопок
- **Localization integration**: Интеграция с переводами

### Паттерны кнопок
```python
# Single button
KeyboardGenerator.single_button_keyboard(text, callback_data)

# Multiple buttons with callback pattern
InlineKeyboardButton(text, callback_data=f"questions_action:{item_id}")
```

## 🚨 Error Handling

### Exception Hierarchy (`bot/utils/exceptions.py`)
```python
# Custom exceptions
RateLimitExceeded      # Rate limiting exceeded
AdminRequired          # Admin access required  
UserNotFound          # User not found in database

# Voice recognition
GroqRateLimitError    # Groq API rate limit
GroqApiError          # Groq API general error
ProviderExhaustedError # All providers failed
```

### Error Handler (`bot/handlers/error_handler.py`)
- **Centralized handling**: Единая точка обработки ошибок
- **User-friendly messages**: Понятные сообщения пользователям
- **Logging integration**: Интеграция с системой логирования

## 📊 Monitoring and Logging

### Structured Logging
```python
from monitoring import get_logger
logger = get_logger(__name__)

# Structured logging with context
logger.info("Action completed", user_id=user.id, action=action)
logger.error("Action failed", user_id=user.id, error=str(e))
```

### Sentry Integration
- **Error tracking**: Автоматическое отслеживание ошибок
- **Performance monitoring**: Мониторинг производительности
- **Alert system**: Система уведомлений

### Health Checks
- **Database connectivity**: Проверка подключения к БД
- **Cache availability**: Доступность кеша
- **External APIs**: Статус внешних API (Groq, OpenAI)

## 🧪 Testing Infrastructure

### КРИТИЧНО: Testing Requirements
- **Любая новая функциональность**: ОБЯЗАТЕЛЬНО покрывать автоматическими тестами
- **Участки без тестов**: Предлагать пользователю добавить тесты  
- **Цель**: Поддерживать coverage >60% для новых модулей
- **Обязательные инструменты**: pytest, mypy, Bandit, pip-audit

### Test Coverage: 60%+ and Growing
- **pytest**: Основной фреймворк тестирования
- **pytest-asyncio**: Поддержка async tests
- **pytest-mock**: Мокирование зависимостей
- **pytest-cov**: Анализ покрытия

### Testing Workflow
```bash
# ОБЯЗАТЕЛЬНО перед КАЖДЫМ коммитом
python3 -m pytest  # Все тесты должны пройти
ruff check .        # Линтинг
ruff format .       # Форматирование  
mypy .             # Проверка типов
bandit -r .        # Security scan
```

### Test Structure
```
tests/
├── conftest.py                 # Shared fixtures
├── test_handlers_integration.py # Handler tests
├── test_rate_limiter.py        # Rate limiting tests
├── test_i18n.py               # Internationalization tests
└── test_groq_whisper_integration.py # Voice tests
```

### Test Commands
```bash
# All tests
python3 -m pytest

# With coverage
python3 -m pytest --cov=. --cov-report=html

# Only unit tests  
python3 -m pytest tests/ -m "not integration"
```

## 📏 Code Quality Standards

### File Size Limits
- **Максимум**: 400 строк на файл
- **При превышении**: ОБЯЗАТЕЛЬНО предлагать рефакторинг пользователю
- **Текущие проблемы**: 
  - `friends_callbacks.py` - 719 строк (КРИТИЧНО)
  - `questions_callbacks.py` - 642 строки 
  - `admin_callbacks.py` - 537 строк

### Function Size Limits  
- **Максимум**: 50 строк на функцию
- **При превышении**: Предлагать разбить на подфункции
- **Исключения**: Только для complex business logic с комментариями

### Communication Guidelines
- **Каждый шаг**: Поясняй подробно и понятным языком
- **Профтермины**: Расшифровывай кратко (например: "Repository Pattern - паттерн доступа к данным")
- **Сложные операции**: Объясняй зачем и как

### Environment Support
- **Нет инструментов**: Запрашивай у пользователя установку или права
- **Сторонние сервисы**: ВСЕГДА согласовывай изменения (Supabase, Telegram API)
- **Environment**: Просить настроить окружение если что-то недоступно

## 📋 Planning Process

### Uncertainty Assessment
- **Перед началом**: Оцени uncertainty задачи (0-1 scale)
- **Порог**: Если >0.1, задавай уточняющие вопросы пользователю
- **Цель**: Снизить до ≤0.1 перед началом работы

### Feature Development Workflow
```
1. Получение задачи от пользователя
2. Оценка неопределённости (0-1)
3. Если >0.1: уточняющие вопросы
4. Формирование детального плана
5. Согласование с пользователем  
6. Выполнение по плану
```

### New Feature Requirements
- **Всегда**: Сначала формируй подробный план действий
- **Опиши пользователю**: Весь план и подходы
- **Согласуй**: Дальнейшую работу перед началом
- **Не начинай**: Реализацию без одобрения плана

## 🛠️ Development Tools Requirements

### Обязательные инструменты
- **Ruff**: Linting и formatting (заменяет flake8, black, isort)
- **mypy**: Type checking
- **Bandit**: Security scanning
- **pip-audit**: Dependency vulnerability scanning
- **Poetry**: Package management (если используется)
- **pre-commit**: Git hooks
- **pytest**: Testing framework

### Docker Integration
- **Production**: Описывай в Dockerfile
- **Testing**: Выполняй в том же Docker образе
- **Development**: Поддерживай Docker для consistency

## 📝 Documentation Standards

### Documentation Language
- **Проектная документация**: ТОЛЬКО английский язык (README, docs/)
- **AI документация**: Русский язык (docs/ai/ только для Claude)
- **Исключение**: docs/ai/ может быть на русском для Claude Code

### Documentation Updates
- **Перед каждым коммитом**: Обновляй соответствующие файлы документации
- **CLAUDE.md**: Должен содержать краткое описание + ссылки на документацию
- **Назначение**: Разработчик или ИИ-агент быстро находят нужную информацию

### Text Externalization
- **НЕ помещай**: Текстовые строки интерфейса в код напрямую  
- **Выноси**: В отдельные словари или файлы ресурсов (i18n система)
- **Локализация**: Используй translator.translate() для всех UI текстов

## 🚀 Deployment Architecture

### Infrastructure
- **Railway**: Bot hosting with auto-scaling
- **Vercel**: Web application with CDN
- **Supabase**: PostgreSQL with RLS policies
- **GitHub Actions**: CI/CD automation

### Environment Configuration
- **Production**: Railway with environment variables
- **Development**: Local with .env files
- **Testing**: Docker containers


## 🔄 Migration Status

### ✅ Fully Migrated (Modular)
- Configuration management
- Database layer with optimization  
- Caching and rate limiting
- Internationalization system
- Service layer and background tasks
- Feedback and monitoring systems

### ⚠️ Requires Refactoring
Согласно `REFACTORING_PLAN.md`:
- `handlers/command_handlers.py` - 736 lines (CRITICAL)
- `handlers/callbacks/friends_callbacks.py` - 719 lines (CRITICAL)
- `handlers/callbacks/questions_callbacks.py` - 642 lines (HIGH)  
- `handlers/callbacks/admin_callbacks.py` - 537 lines (HIGH)

### Refactoring Approach
1. **Split monolithic handlers** по доменам
2. **Extract business logic** в service layer
3. **Implement command pattern** для handlers
4. **Add comprehensive tests** для refactored components

---

**Последнее обновление**: 2025-07-15 22:30  
**Источники**: CLAUDE.md, ARCHITECTURE.md, user requirements  
**Следующее обновление**: При изменении архитектуры
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Doyobi Diary** is a modern Telegram bot for activity tracking and social connections with Enterprise-grade architecture. The project features a comprehensive ecosystem including a bot, web application, and monitoring system with hybrid modular architecture.

## Technology Stack

- **Backend**: Python 3.8+ with python-telegram-bot==20.3, Supabase (PostgreSQL), APScheduler
- **Frontend**: Next.js 15 with TypeScript, React 18.3.1, Tailwind CSS
- **Infrastructure**: Docker, Railway (bot), Vercel (web app), GitHub Actions
- **Development**: pytest, black, flake8, mypy, bandit, pre-commit
- **Monitoring**: Sentry, structured logging, health checks

## Development Commands

### Testing
```bash
# Run all tests
python3 -m pytest

# Run with coverage
python3 -m pytest --cov=. --cov-report=html

# Run only unit tests
python3 -m pytest tests/ -m "not integration"

# Run integration tests
python3 -m pytest tests/ -m "integration"
```

### Code Quality
```bash
# Linting
flake8 . --max-line-length=127

# Formatting
black .

# Type checking
mypy . --ignore-missing-imports

# Security scanning
bandit -r . -ll
```

### Docker Development
```bash
# Build image
docker build -t doyobi-diary .

# Run with docker-compose
docker-compose up -d

# Development with live reload
docker-compose -f docker-compose.dev.yml up
```

## Architecture

### Hybrid Architecture (75% Migration Complete)
The project uses a hybrid approach combining:
- **Modular structure** for new components (`/bot/` directory) ✅ 
- **Legacy monolithic handlers** being gradually refactored ⚠️
- **Backward compatibility** maintained during transition

### Current Module Structure
```
bot/
├── config.py              # ✅ Centralized configuration (dataclass)
├── database/              # ✅ Repository pattern data access
│   ├── client.py          #     Database client with connection pooling
│   ├── user_operations.py #     User management with caching
│   ├── friend_operations.py #   90% faster friend discovery
│   └── question_operations.py # Question management
├── admin/                 # ✅ Administrative functions  
│   ├── admin_operations.py #    Admin utilities and verification
│   └── broadcast_manager.py #   Mass messaging with batching
├── questions/             # ✅ Question system with versioning
│   ├── question_manager.py #    Business logic with 5-question limit
│   └── question_templates.py #  Predefined templates
├── services/              # ✅ Background services
│   ├── scheduler_service.py #   APScheduler integration
│   ├── multi_question_scheduler.py # Individual schedules
│   ├── health_service.py  #     System monitoring
│   └── whisper_client.py  #     Multi-provider voice transcription (Groq + OpenAI)
├── cache/                 # ✅ TTL caching (80% UI speed improvement)
│   └── ttl_cache.py       #     5-minute TTL with auto-cleanup
├── handlers/              # ⚠️ REFACTORING NEEDED
│   ├── base/              # ✅ Modular callback routing
│   ├── callbacks/         # ⚠️ Large files need splitting
│   ├── command_handlers.py # ⚠️ 736 lines - needs refactoring
│   ├── error_handler.py   # ✅ Centralized error handling
│   └── rate_limit_handler.py # ✅ Rate limiting integration
├── utils/                 # ✅ Cross-cutting utilities
│   ├── rate_limiter.py    #     Multi-tier rate limiting
│   ├── datetime_utils.py  #     Safe parsing utilities
│   ├── cache_manager.py   #     Cache operations
│   └── exceptions.py      #     Custom exceptions
├── keyboards/             # ✅ UI generation
│   └── keyboard_generators.py # Inline keyboard creation
├── i18n/                  # ✅ Internationalization (3 languages)
│   ├── translator.py      #     Template-based translations
│   ├── language_detector.py #   Auto language detection
│   └── locales/           #     ru.json, en.json, es.json
└── feedback/              # ✅ GitHub Issues integration
    ├── feedback_manager.py #    User feedback collection
    └── github_client.py   #     GitHub API automation
```

### Core Components

#### Configuration Management (`bot/config.py`)
- **Dataclass-based** configuration with validation
- **Environment variable** loading with defaults  
- **Feature flags** for optional services (Groq, OpenAI, Feedback, Monitoring)
- **Safe parsing** of admin IDs and numeric values
- **Multi-provider support** with fallback configuration

#### Database Layer (`bot/database/`)
- **Repository pattern** with domain separation
- **Connection pooling** and health checks
- **Optimized queries** - 90% performance improvement for friend discovery
- **SQL functions** for complex operations (friends-of-friends)
- **Cache integration** for frequently accessed data

#### Multi-Tier Rate Limiting (`bot/utils/rate_limiter.py`)
- **Action-specific limits**:
  - General commands: 20/minute
  - Friend requests: 5/hour (anti-spam)
  - Discovery: 3/minute (resource-intensive)
  - Voice messages: 10/hour (API costs)
  - Feedback: 3/hour (GitHub API)
  - Admin: 50/minute
- **Sliding window algorithm** for fair distribution
- **User isolation** preventing cross-user impact

#### TTL Caching System (`bot/cache/ttl_cache.py`)
- **5-minute TTL** for user settings
- **Automatic invalidation** on data updates
- **80% performance improvement** for UI operations
- **Background cleanup** of expired entries
- **Memory-efficient** with size limits

#### Internationalization (`bot/i18n/`)
- **3 languages**: Russian (default), English, Spanish
- **Automatic detection** from Telegram user preferences
- **Template variables** with parameter substitution
- **Fallback mechanism** for missing translations
- **Pluralization support** for complex grammar

#### Service Layer (`bot/services/`)
- **Multi-question scheduler** with individual user schedules
- **Health monitoring** for system components
- **Multi-provider voice recognition** with intelligent fallback
- **Background task management** with error tracking

#### Voice Recognition System (`bot/services/whisper_client.py`)
- **Primary Provider**: Groq whisper-large-v3 (30s timeout)
- **Fallback Provider**: Groq whisper-large-v3-turbo (30s timeout)
- **Final Fallback**: OpenAI whisper-1 (60s timeout)
- **Automatic switching** on rate limits with admin notifications
- **Smart caching** for all providers to reduce API costs
- **Graceful degradation** when services are unavailable

#### Feedback System (`bot/feedback/`)
- **GitHub Issues automation** for bug reports and feature requests
- **3 feedback types**: bug_report, feature_request, general
- **Rate limiting** and session management
- **Admin notification** integration

## Testing Infrastructure

### Test Coverage: 60%+ and Growing
- **pytest** with async support and fixtures
- **pytest-cov** for coverage analysis  
- **pytest-mock** for dependency isolation
- **25+ automated tests** covering:
  - Unit tests (utility functions)
  - Component tests (rate limiter, cache)
  - Integration tests (database operations)
  - i18n tests (translation validation)

### Test Configuration
- `/pytest.ini` - test discovery and markers
- `/pyproject.toml` - coverage configuration  
- `/tests/conftest.py` - shared fixtures and mocks
- CI/CD integration with GitHub Actions

## Performance Achievements

### Measured Improvements
- **Friend discovery**: 90% faster (500ms+ → 50ms) via SQL optimization
- **Settings loading**: 80% faster (200ms → 40ms) via TTL caching
- **Database queries**: N+1 problems eliminated
- **Test coverage**: 0% → 60%+ with automated testing
- **Cache hit rate**: 85%+ efficiency

### Performance Targets
- Response time: <100ms for cached operations
- Throughput: 1000+ requests/minute
- Uptime: 99.9%+ availability
- Error rate: <0.1% unhandled errors

## Security Features

### Multi-Layer Security
- **Input validation** with Python type hints
- **SQL injection prevention** via Supabase ORM
- **Rate limiting** by action type and user
- **Admin authorization** with secure verification
- **Error boundary isolation** preventing system failures
- **Secure configuration** with environment variable validation

## Monitoring and Operations

### Production Monitoring
- **Sentry integration** for error tracking and alerting
- **Structured logging** with correlation IDs
- **Health checks** for all system components
- **Performance metrics** collection
- **GitHub Actions** for CI/CD monitoring

### Deployment Architecture
- **Railway** for bot hosting with auto-scaling
- **Vercel** for web application with CDN
- **Supabase** for PostgreSQL with RLS policies
- **GitHub Actions** for automated testing and deployment

## Code Guidelines

### Development Standards
- **Python 3.8+** with comprehensive type hints
- **Modular architecture** with clear separation of concerns
- **Repository pattern** for data access
- **Dependency injection** through constructors
- **Error handling** with custom exceptions
- **Never hardcode** user-facing text (use i18n system)

### Quality Requirements
- **All new features** must have automated tests
- **Code coverage** minimum 60% for new modules
- **PEP 8 compliance** enforced by black formatter
- **Type checking** with mypy
- **Security scanning** with bandit
- **Documentation** updated before commits

## Architectural Patterns

- **Repository Pattern**: Data access abstraction (`database/` modules)
- **Dependency Injection**: Configuration and services via constructors
- **Strategy Pattern**: Multiple rate limiting strategies
- **Factory Pattern**: Service and scheduler creation
- **Command Pattern**: Handler architecture
- **Observer Pattern**: Event-driven scheduler notifications

## Migration Status and Refactoring Needs

### ✅ Fully Migrated (Modular)
- Configuration management
- Database layer with optimization
- Caching and rate limiting
- Internationalization system
- Service layer and background tasks
- Feedback and monitoring systems

### ⚠️ Requires Refactoring
According to `REFACTORING_PLAN.md`, these files exceed recommended sizes:
- `handlers/command_handlers.py` - 736 lines (CRITICAL)
- `handlers/callbacks/friends_callbacks.py` - 719 lines (CRITICAL)  
- `handlers/callbacks/questions_callbacks.py` - 642 lines (HIGH)
- `handlers/callbacks/admin_callbacks.py` - 537 lines (HIGH)

### Recommended Refactoring Approach
1. Split monolithic handlers by domain
2. Extract business logic to service layer
3. Implement command pattern for handlers
4. Add comprehensive tests for refactored components

## Important Development Notes

- Always use `python3` command, never `python`
- Push changes **only** to `staging` branch; `main` branch pushes are forbidden
- Run tests before every commit to ensure all pass
- Use Docker for both production and testing environments
- Update documentation before each commit
- File size limit: 400 lines per file, 50 lines per function
- Rate limiting is enabled by default - test with appropriate delays

## Environment Variables

### Voice Recognition (Optional)
```bash
# Primary provider (recommended)
export GROQ_API_KEY="gsk_your_groq_key"

# Fallback provider
export OPENAI_API_KEY="sk_your_openai_key"

# Model configuration (optional)
export GROQ_PRIMARY_MODEL="whisper-large-v3"        # Default
export GROQ_FALLBACK_MODEL="whisper-large-v3-turbo" # Default
export GROQ_TIMEOUT_SECONDS="30"                    # Default
```

### Other Configuration
```bash
# Required
export TELEGRAM_BOT_TOKEN="your_bot_token"
export SUPABASE_URL="your_supabase_url"
export SUPABASE_SERVICE_ROLE_KEY="your_service_key"

# Optional
export ADMIN_USER_ID="your_telegram_id"
export SENTRY_DSN="your_sentry_dsn"
export GITHUB_FEEDBACK_TOKEN="your_github_token"
```

## 📚 Documentation Links

### 🏗️ Architecture and Development
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Detailed system architecture
  - Hybrid modular architecture (75% migration complete)
  - Component diagrams and data flow
  - Migration roadmap and patterns
  - Performance architecture details

### 🚀 Deployment and Operations
- **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Complete deployment guide
  - Railway (bot) + Vercel (webapp) + Supabase setup
  - Environment variables and CI/CD configuration
  - Health checks and monitoring setup
  - Troubleshooting and rollback procedures

- **[docs/MONITORING.md](docs/MONITORING.md)** - Production monitoring
  - Sentry integration and error tracking
  - Structured logging with correlation IDs
  - Performance metrics and alerting
  - Dashboard configuration and best practices

### ⚡ Performance and Quality
- **[docs/PERFORMANCE.md](docs/PERFORMANCE.md)** - Performance optimization
  - 90% faster friend discovery (500ms → 50ms)
  - 80% faster UI with TTL caching
  - Database optimization and N+1 elimination
  - Benchmark results and monitoring

- **[docs/TESTING.md](docs/TESTING.md)** - Testing strategy
  - 25+ automated tests with 60%+ coverage
  - Unit, integration, and performance testing
  - CI/CD pipeline and test automation
  - Test fixtures and mocking patterns

### 🌍 Internationalization and UX
- **[docs/I18N_GUIDE.md](docs/I18N_GUIDE.md)** - Translation system
  - 3 languages: Russian, English, Spanish
  - Automatic language detection
  - Template variables and fallback mechanisms
  - Adding new languages guide

### 📋 Project Management
- **[docs/README.md](docs/README.md)** - Documentation overview
  - Complete documentation structure
  - Quick start guides for different roles
  - File relationships and dependencies
  - Documentation standards and guidelines

- **[REFACTORING_PLAN.md](REFACTORING_PLAN.md)** - Architecture evolution
  - Files requiring refactoring (handlers layer)
  - Priority levels and size limits
  - Migration timeline and strategy

### 🗂️ Core Project Files
- **[README.md](README.md)** - User-facing project documentation
  - Feature overview and capabilities
  - Installation and setup instructions
  - User guide and API reference
  - Performance achievements and updates

- **[pyproject.toml](pyproject.toml)** - Development tools configuration
- **[pytest.ini](pytest.ini)** - Testing framework setup
- **[requirements.txt](requirements.txt)** - Python dependencies
- **[Dockerfile](Dockerfile)** - Container configuration
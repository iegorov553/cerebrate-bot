# CLAUDE.md - Technical Reference

This document provides essential technical guidance for working with the Doyobi Diary Telegram bot project. It serves as a technical reference for code maintenance and architecture understanding.

## Project Overview

**Doyobi Diary** is a production-ready Telegram bot built with modular architecture for activity tracking, social features, and voice message processing.

**Core Features:**
- Activity tracking with personalized notifications
- Voice message transcription via OpenAI Whisper API
- Social friend system with discovery algorithms
- Multi-language support (Russian, English, Spanish)
- Health monitoring and admin management
- Web interface integration

**Version:** 2.1.19
**Architecture:** Modular async Python with dependency injection
**Database:** Supabase (PostgreSQL)
**Deployment:** Railway (bot) + Vercel (webapp)

## Environment Variables

### Required Configuration
```bash
TELEGRAM_BOT_TOKEN=<bot_token_from_botfather>
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service_role_key>
```

### Optional Services
```bash
OPENAI_API_KEY=sk-<key>              # Voice message transcription
ADMIN_USER_ID=<telegram_id>          # Admin access
GITHUB_FEEDBACK_TOKEN=ghp-<token>    # GitHub Issues integration
GITHUB_REPO=iegorov553/cerebrate-bot
SENTRY_DSN=https://<dsn>@sentry.io   # Error monitoring
WEBAPP_URL=https://doyobi-diary.vercel.app
BOT_VERSION=2.1.19
ENVIRONMENT=production
```

## Architecture Overview

### Entry Point
**File:** `main.py`
**Pattern:** Factory + Dependency Injection
**Components:**
- `create_application()` - application factory
- Component initialization: DatabaseClient, MultiTierRateLimiter, TTLCache
- Handler setup via `setup_*` functions
- Multi-question scheduler service startup

### Core Components

#### Configuration (`bot/config.py`)
- `Config` dataclass with environment variable loading
- `from_env()` factory method
- `validate()` for required parameter checking

#### Database Layer (`bot/database/`)
- `DatabaseClient` - Supabase wrapper with health checks
- `UserOperations` - user management with TTL caching
- `FriendOperations` - optimized friend operations and discovery
- `QuestionOperations` - custom question system

#### Handlers (`bot/handlers/`)
- `command_handlers.py` - slash commands (/start, /settings, etc.)
- `callback_handlers.py` - inline keyboard callbacks with central dispatcher
- `voice_handlers.py` - OpenAI Whisper integration
- `admin_handlers.py` - admin functionality
- Rate limiting via decorators, monitoring via structlog

#### Services (`bot/services/`)
- `MultiQuestionScheduler` - time-based notification system
- `WhisperClient` - OpenAI Whisper API integration
- `HealthService` - system health monitoring

#### Utilities (`bot/utils/`)
- `MultiTierRateLimiter` - sliding window rate limiting
- `TTLCache` - time-to-live caching with background cleanup
- `version.py` - version management and display

### Architectural Patterns

#### Core Patterns
- **Repository Pattern** - database operations abstraction
- **Factory Pattern** - application and component creation
- **Strategy Pattern** - different handler types and languages
- **Decorator Pattern** - rate limiting and monitoring
- **Chain of Responsibility** - handler processing

#### Optimization Patterns
- **TTL Caching** - reduce database load
- **Batch Loading** - avoid N+1 queries in friend operations
- **Background Workers** - async cleanup and maintenance
- **Circuit Breaker** - external service failure handling

## Development Commands

```bash
python3 main.py                      # Run bot
python3 -m pytest                    # Run tests
python3 -m pytest --cov=. --cov-report=html  # Coverage report
flake8 .                             # Linting
black .                              # Code formatting
python3 scripts/update_version.py    # Version increment
```

## Database Schema

### Core Tables
```sql
-- User management
CREATE TABLE users (
    tg_id BIGINT PRIMARY KEY,
    tg_username TEXT,
    tg_first_name TEXT,
    enabled BOOLEAN DEFAULT true,
    window_start TIME DEFAULT '09:00',
    window_end TIME DEFAULT '22:00',
    interval_min INTEGER DEFAULT 120,
    language VARCHAR(5) DEFAULT 'ru'
);

-- Activity logging
CREATE TABLE tg_jobs (
    id BIGSERIAL PRIMARY KEY,
    tg_id BIGINT REFERENCES users(tg_id),
    job_text TEXT NOT NULL,
    jobs_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Friend system
CREATE TABLE friendships (
    id BIGSERIAL PRIMARY KEY,
    requester_id BIGINT REFERENCES users(tg_id),
    addressee_id BIGINT REFERENCES users(tg_id),
    status TEXT CHECK (status IN ('pending', 'accepted', 'declined')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Custom questions
CREATE TABLE user_questions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(tg_id),
    question_text TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE user_question_schedules (
    id BIGSERIAL PRIMARY KEY,
    user_question_id BIGINT REFERENCES user_questions(id),
    window_start TIME NOT NULL,
    window_end TIME NOT NULL,
    interval_minutes INTEGER NOT NULL
);
```

## Key Technical Features

### Rate Limiting
```python
LIMITS = {
    "general": (20, 60),           # 20 requests per minute
    "friend_request": (5, 3600),   # 5 requests per hour
    "feedback": (3, 3600),         # 3 feedback messages per hour
    "voice_message": (10, 3600),   # 10 voice messages per hour
    "admin": (50, 60),             # 50 requests per minute
}
```

### Internationalization
- **Languages:** Russian (default), English, Spanish
- **Implementation:** `bot.i18n.translator.Translator`
- **Usage:** `translator.translate('key', variable=value)`
- **Fallback:** English if key missing in target language
- **Auto-detection:** From Telegram user.language_code

### Voice Message Processing
- **Service:** OpenAI Whisper API integration
- **Formats:** MP3, MP4, MPEG, MPGA, M4A, WAV, WebM, OGG, OGA
- **Limits:** 25MB file size, 120 seconds duration
- **Caching:** TTL cache for transcription results
- **Flow:** Download → Validate → Transcribe → Process as text

### Friend Discovery Algorithm
- **Method:** "friends of friends" with SQL optimization
- **Implementation:** `FriendOperations.get_friends_of_friends_optimized()`
- **Filtering:** Excludes existing friends and pending requests
- **UI:** Inline keyboards with mutual friend details
- **Performance:** Batch queries to avoid N+1 problems

### Health Monitoring
- **Command:** `/health` for basic checks
- **Admin Interface:** Detailed system health via admin panel
- **Components:** Database, Telegram API, scheduler status
- **Metrics:** Response time, error rates, uptime
- **Implementation:** `bot.services.health_service.HealthService`

## Error Handling

### Exception Hierarchy
```python
# Custom exceptions in bot.utils.exceptions
class BotException(Exception): pass
class RateLimitExceeded(BotException): pass
class AdminRequired(BotException): pass
class ValidationError(BotException): pass
```

### Monitoring Integration
- **Sentry:** Error tracking and performance monitoring
- **Structlog:** Structured logging with context
- **Health Checks:** System component monitoring
- **Rate Limiting:** Multi-tier protection against abuse

## Testing Infrastructure

### Test Structure
```
tests/
├── test_new_components.py      # 7 architectural component tests
├── test_rate_limiter.py        # 14 rate limiting tests  
├── test_i18n.py               # 24 internationalization tests
├── test_handlers_integration.py # 7 handler integration tests
└── test_integration.py        # 4 integration tests
```

### Coverage Areas
- Handler functionality and error cases
- Rate limiting behavior and edge cases
- Internationalization with template variables
- Database operations and caching
- Voice message processing workflow

## Deployment Configuration

### Production Stack
- **Bot Service:** Railway with automatic deployments
- **Web Interface:** Vercel with Next.js
- **Database:** Supabase (managed PostgreSQL)
- **Monitoring:** Sentry for error tracking
- **Version Control:** Git hooks for automated versioning

### Docker Support
- **Dockerfile:** Multi-stage build with security best practices
- **docker-compose.yml:** Development and production configurations
- **Health Checks:** Built-in container health monitoring
- **Security:** Non-root user, minimal attack surface

### Environment-Specific Settings
```bash
# Development
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Production  
ENVIRONMENT=production
LOG_LEVEL=INFO
RAILWAY_GIT_COMMIT_SHA=<commit_hash>
```

## Code Organization Principles

### Modular Design
- **Separation of Concerns:** Each module has single responsibility
- **Loose Coupling:** Modules interact through well-defined interfaces
- **High Cohesion:** Related functionality grouped together
- **Dependency Injection:** Components passed through bot_data

### Naming Conventions
- **Files:** snake_case for Python modules
- **Classes:** PascalCase with descriptive names
- **Functions:** snake_case with verb_noun pattern
- **Constants:** UPPER_SNAKE_CASE

### Import Organization
```python
# Standard library imports
import asyncio
from typing import Optional

# Third-party imports
from telegram import Update
from telegram.ext import Application

# Local imports
from bot.database.client import DatabaseClient
from bot.utils.exceptions import BotException
```

## Security Considerations

### Input Validation
- All user inputs sanitized before database operations
- Markdown escaping for message formatting
- File size and type validation for voice messages
- SQL injection prevention through parameterized queries

### Access Control
- Admin functionality restricted by user ID validation
- Rate limiting to prevent abuse
- Sensitive data excluded from logs
- Service role keys for database access

### Data Protection
- User data encrypted in transit and at rest
- Minimal data collection principle
- GDPR compliance considerations
- Secure API key management through environment variables

This technical reference should be updated when architectural changes are made to maintain accuracy for code maintenance and development decisions.
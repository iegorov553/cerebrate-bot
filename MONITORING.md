# Monitoring Documentation

This document provides comprehensive monitoring setup and operational guidance for the Hour Watcher Bot production environment.

## Overview

The Hour Watcher Bot employs **enterprise-grade monitoring** with multiple layers of observability, error tracking, and performance monitoring to ensure reliable production operation.

### Monitoring Stack

- **🔍 Sentry**: Error tracking and performance monitoring
- **📊 Structured Logging**: Comprehensive application logging with structlog
- **📈 Performance Metrics**: Response time and throughput tracking
- **🚨 Alerting**: Real-time notifications for critical issues
- **📱 Health Checks**: Continuous availability monitoring
- **🎯 Custom Metrics**: Business logic monitoring and analytics

---

## Sentry Integration

### Setup and Configuration

#### 1. Sentry Project Setup

```bash
# Create Sentry project at https://sentry.io
# Get your DSN from Project Settings > Client Keys (DSN)
export SENTRY_DSN="https://your_key@sentry.io/project_id"
```

#### 2. Environment Configuration

```bash
# Production Environment Variables
SENTRY_DSN=https://your_sentry_dsn@sentry.io/project_id
ENVIRONMENT=production              # or development, staging
RELEASE_VERSION=v2.2.0             # For deployment tracking
DEBUG=false                        # Disable debug in production

# Performance Monitoring (Optional)
SENTRY_TRACES_SAMPLE_RATE=0.1      # 10% of transactions
SENTRY_PROFILES_SAMPLE_RATE=0.1    # 10% for profiling
LOG_LEVEL=INFO                     # INFO, DEBUG, WARNING, ERROR
```

#### 3. Railway Deployment Setup

```bash
# Set production variables
railway variables set SENTRY_DSN=your-sentry-dsn
railway variables set ENVIRONMENT=production
railway variables set RELEASE_VERSION=v2.2.0
railway variables set LOG_LEVEL=INFO

# Verify configuration
railway variables
```

#### 4. Sentry Configuration (`monitoring.py`)

```python
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

def setup_sentry(config: Config):
    """Production-ready Sentry configuration"""
    
    if not config.sentry_dsn:
        logger.warning("Sentry DSN not configured - error tracking disabled")
        return
    
    sentry_sdk.init(
        dsn=config.sentry_dsn,
        
        # Integrations
        integrations=[
            LoggingIntegration(
                level=logging.INFO,        # Capture info and above
                event_level=logging.ERROR  # Send errors as events
            ),
            AioHttpIntegration(transaction_style="method_and_path_pattern"),
        ],
        
        # Performance Monitoring
        traces_sample_rate=0.1,          # 10% of transactions
        profiles_sample_rate=0.1,        # 10% for profiling
        
        # Environment Configuration
        environment=config.environment,
        release=config.release_version,
        
        # Additional Configuration
        attach_stacktrace=True,
        send_default_pii=False,          # Privacy protection
        max_breadcrumbs=50,
        before_send=filter_sensitive_data,
    )
```

### Error Tracking Implementation

#### Automatic Error Capture

```python
# Errors are automatically captured with context
@track_errors
async def critical_function(user_id: int):
    """Function with automatic error tracking"""
    try:
        # Business logic here
        await process_user_request(user_id)
    except Exception as e:
        # Automatically captured by Sentry with full context
        logger.error("Failed to process user request", 
                    user_id=user_id, error=str(e))
        raise
```

#### Manual Error Reporting

```python
import sentry_sdk

# Capture exceptions manually with additional context
try:
    result = await risky_operation()
except Exception as e:
    sentry_sdk.capture_exception(e)
    sentry_sdk.set_extra("operation_context", context_data)
    sentry_sdk.set_tag("operation_type", "friend_discovery")
    raise

# Capture custom messages
sentry_sdk.capture_message(
    "Unusual activity detected",
    level="warning",
    extra={"user_id": user_id, "activity": activity_data}
)
```

#### User Context Setup

```python
def set_user_context(user_id: int, username: str = None, first_name: str = None):
    """Set user context for error tracking"""
    sentry_sdk.set_user({
        "id": str(user_id),
        "username": username,
        "first_name": first_name,
    })
    
    sentry_sdk.set_tag("user_type", "telegram_user")
    sentry_sdk.set_extra("user_metadata", {
        "registration_date": get_user_registration_date(user_id),
        "settings": get_user_settings(user_id)
    })
```

---

## Structured Logging

### Logging Configuration

```python
import structlog
import logging

def setup_logging(config: Config):
    """Configure structured logging with JSON output"""
    
    # Configure standard logging
    logging.basicConfig(
        level=logging.INFO if config.environment == "production" else logging.DEBUG,
        format="%(message)s",
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if config.environment == "production" 
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )
```

### Logging Best Practices

#### Structured Log Messages

```python
logger = get_logger(__name__)

# Good: Structured logging with context
logger.info(
    "User settings updated",
    user_id=user_id,
    settings_changed=["window_start", "interval_min"],
    old_values={"window_start": "09:00", "interval_min": 120},
    new_values={"window_start": "10:00", "interval_min": 60},
    duration_ms=duration.total_seconds() * 1000
)

# Bad: Unstructured logging
logger.info(f"User {user_id} updated settings from 09:00/120 to 10:00/60")
```

#### Performance Logging

```python
@log_performance
async def expensive_operation(user_id: int):
    """Function with automatic performance logging"""
    start_time = time.time()
    
    try:
        result = await complex_database_query(user_id)
        
        logger.info(
            "Database query completed",
            user_id=user_id,
            query_type="friend_discovery",
            result_count=len(result),
            duration_ms=(time.time() - start_time) * 1000,
            cache_hit=False
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Database query failed",
            user_id=user_id,
            query_type="friend_discovery",
            error=str(e),
            duration_ms=(time.time() - start_time) * 1000
        )
        raise
```

#### Security and Privacy

```python
def filter_sensitive_data(event, hint):
    """Filter sensitive data from Sentry events"""
    
    # Remove sensitive fields
    if 'extra' in event:
        sensitive_keys = ['password', 'token', 'api_key', 'secret']
        for key in sensitive_keys:
            if key in event['extra']:
                event['extra'][key] = '[FILTERED]'
    
    # Filter user data
    if 'user' in event and 'ip_address' in event['user']:
        del event['user']['ip_address']
    
    return event

# Log without exposing sensitive data
logger.info(
    "User authentication successful",
    user_id=user_id,
    method="telegram_auth",
    # Don't log tokens or sensitive data
    timestamp=datetime.now().isoformat()
)
```

## 🎯 Мониторируемые операции

### Критические функции

- ✅ `user_registration` - Регистрация пользователей
- ✅ `friends_discovery` - Поиск друзей друзей
- ✅ `admin_broadcast` - Массовые рассылки
- ✅ `database_operations` - Операции с БД
- ✅ `telegram_handlers` - Обработчики команд

### Метрики производительности

- `friends_discovery_request` - Запросы поиска друзей
- `broadcast_initiated` - Начало рассылки
- `broadcast_completed` - Завершение рассылки
- `user_registration_count` - Количество регистраций
- `database_query_time` - Время запросов к БД

## 🛡️ Фильтрация ошибок

### Автоматически игнорируемые ошибки

```python
# Не отправляются в Sentry:
- Telegram API: "forbidden", "blocked", "chat not found"
- Пользовательские ошибки: "user deactivated", "message too old"
- Тестовые события (environment=test)
- Быстрые транзакции (< 100ms)
```

### Кастомные фильтры

```python
def before_send_filter(event, hint):
    # Ваша логика фильтрации
    if should_ignore_error(event):
        return None
    return event
```

## 📊 Дашборды и алерты

### Ключевые метрики в Sentry

1. **Error Rate** - Процент ошибок
2. **Response Time** - Время ответа
3. **User Impact** - Количество затронутых пользователей
4. **Release Health** - Здоровье релизов

### Рекомендуемые алерты

```yaml
Алерты:
  - Error rate > 5% (15 минут)
  - Response time > 2s (10 минут)
  - Broadcast failures > 10% (немедленно)
  - Database errors > 3 в минуту (5 минут)
```

## 🔧 Локальная разработка

### Без Sentry

```bash
# Мониторинг отключается автоматически
unset SENTRY_DSN
python3 cerebrate_bot.py
```

### С локальным Sentry

```bash
# Используйте development DSN
export SENTRY_DSN=https://dev-dsn@sentry.io/project
export ENVIRONMENT=development
python3 cerebrate_bot.py
```

## 🐛 Отладка

### Проверка конфигурации

```python
import sentry_sdk
print(f"Sentry configured: {sentry_sdk.Hub.current.client is not None}")
```

### Тестовая ошибка

```python
# Отправить тестовую ошибку в Sentry
sentry_sdk.capture_message("Test message from Hour Watcher Bot")
```

### Проверка логов

```bash
# Локально
tail -f bot.log

# Railway
railway logs --tail
```

## 📋 Чеклист для production

- [ ] `SENTRY_DSN` настроен
- [ ] `ENVIRONMENT=production`
- [ ] `RELEASE_VERSION` соответствует версии
- [ ] Алерты настроены в Sentry
- [ ] Дашборд создан для метрик
- [ ] Проверена фильтрация ошибок
- [ ] Настроены уведомления команде

---

## CI/CD Integration

### GitHub Actions Integration

```yaml
name: Deploy with Monitoring

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set Release Version
        run: echo "RELEASE_VERSION=v2.2.0-$(git rev-parse --short HEAD)" >> $GITHUB_ENV
      
      - name: Deploy to Railway
        run: |
          railway variables set RELEASE_VERSION=$RELEASE_VERSION
          railway up --detach
      
      - name: Create Sentry Release
        env:
          SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
          SENTRY_ORG: ${{ secrets.SENTRY_ORG }}
          SENTRY_PROJECT: ${{ secrets.SENTRY_PROJECT }}
        run: |
          # Install Sentry CLI
          curl -sL https://sentry.io/get-cli/ | bash
          
          # Create release
          sentry-cli releases new $RELEASE_VERSION
          sentry-cli releases set-commits $RELEASE_VERSION --auto
          sentry-cli releases deploy $RELEASE_VERSION --env production
          
          # Upload source maps if needed
          # sentry-cli releases files $RELEASE_VERSION upload-sourcemaps ./dist
      
      - name: Monitor Deployment
        run: |
          # Wait for health check
          sleep 30
          
          # Verify deployment health
          curl -f https://your-railway-url/health || exit 1
          
          # Finalize release
          sentry-cli releases finalize $RELEASE_VERSION
```

### Railway Environment Variables

```bash
# Set monitoring variables for production
railway variables set SENTRY_DSN=$SENTRY_DSN
railway variables set ENVIRONMENT=production
railway variables set LOG_LEVEL=INFO
railway variables set RELEASE_VERSION=$(git describe --tags --always)

# Verify variables
railway variables list | grep -E "SENTRY|ENVIRONMENT|LOG_LEVEL|RELEASE"
```

---

## Resources and Documentation

### External Documentation
- [Sentry Python SDK](https://docs.sentry.io/platforms/python/)
- [Structlog Documentation](https://www.structlog.org/)
- [Python Logging Best Practices](https://docs.python.org/3/howto/logging.html)
- [Telegram Bot Error Handling](https://github.com/python-telegram-bot/python-telegram-bot/wiki/Exception-Handling)
- [Railway Monitoring](https://docs.railway.app/deployment/monitoring)

### Internal Documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture overview
- [TESTING.md](TESTING.md) - Testing guidelines and procedures
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment instructions
- [PERFORMANCE.md](PERFORMANCE.md) - Performance optimization guide

---

This monitoring documentation ensures comprehensive observability and quick issue resolution in production environments.
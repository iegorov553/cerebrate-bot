"""
Monitoring and logging configuration for Doyobi Diary.
"""

import logging
import os
import time

import sentry_sdk
import structlog
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


def setup_monitoring():
    """Configure Sentry monitoring and structured logging."""

    # Get configuration from environment
    sentry_dsn = os.getenv("SENTRY_DSN")
    environment = os.getenv("ENVIRONMENT", "development")
    release = os.getenv("RELEASE_VERSION", "unknown")

    # Configure Sentry if DSN is provided
    if sentry_dsn:
        logging_integration = LoggingIntegration(
            level=logging.INFO,  # Capture info and above as breadcrumbs
            event_level=logging.ERROR,  # Send errors as events
        )

        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[logging_integration, AsyncioIntegration(auto_enable_integrations=False)],
            environment=environment,
            release=release,
            traces_sample_rate=0.1,  # 10% performance monitoring
            profiles_sample_rate=0.1,  # 10% profiling
            # Additional options
            before_send=before_send_filter,
            before_send_transaction=before_send_transaction_filter,
            # Alert configurations
            attach_stacktrace=True,
            send_default_pii=False,  # Don't send personal info
            max_breadcrumbs=100,
            # Alert thresholds
            shutdown_timeout=5,
        )

        # Set user context
        sentry_sdk.set_context("bot", {"name": "Doyobi Diary", "version": release, "environment": environment})

        # Setup critical alerts
        setup_critical_alerts()

        # Get logger after structlog is configured
        logger = structlog.get_logger(__name__)
        logger.info("Sentry monitoring and alerts configured successfully")

    # Configure structured logging
    configure_structlog()


def before_send_filter(event, hint):
    """Filter events before sending to Sentry."""

    # Don't send test events
    if event.get('environment') == 'test':
        return None

    # Filter out common noisy errors
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']

        # Skip certain telegram errors
        if 'telegram' in str(exc_type).lower():
            # Skip user blocked bot, message too old, etc.
            if any(
                skip_phrase in str(exc_value).lower()
                for skip_phrase in ['forbidden', 'blocked', 'message is too old', 'chat not found', 'user deactivated']
            ):
                return None

    return event


def before_send_transaction_filter(event, hint):
    """Filter transaction events before sending to Sentry."""

    # Don't track test transactions
    if event.get('environment') == 'test':
        return None

    # Skip very fast transactions (< 100ms)
    if event.get('timestamp', 0) - event.get('start_timestamp', 0) < 0.1:
        return None

    return event


def configure_structlog():
    """Configure structured logging with structlog."""

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=None,  # Will be handled by structlog
        level=logging.INFO,
    )

    # Configure structlog
    structlog.configure(
        processors=[
            # Filter by log level
            structlog.stdlib.filter_by_level,
            # Add log level
            structlog.stdlib.add_log_level,
            # Add logger name
            structlog.stdlib.add_logger_name,
            # Process positional arguments
            structlog.stdlib.PositionalArgumentsFormatter(),
            # Add timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Process stack info
            structlog.processors.StackInfoRenderer(),
            # Format exceptions
            structlog.processors.format_exc_info,
            # Add extra fields
            structlog.contextvars.merge_contextvars,
            # Unicode decoder
            structlog.processors.UnicodeDecoder(),
            # Final renderer
            (
                structlog.dev.ConsoleRenderer()
                if os.getenv("ENVIRONMENT") == "development"
                else structlog.processors.JSONRenderer()
            ),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    """Get a structured logger instance."""
    return structlog.get_logger(name)


# Error tracking decorators
def track_errors(operation_name: str = None):
    """Decorator to track errors in Sentry with operation context."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            with sentry_sdk.configure_scope() as scope:
                scope.set_tag("operation", op_name)
                scope.set_context(
                    "function",
                    {
                        "name": func.__name__,
                        "module": func.__module__,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys()),
                    },
                )

                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Log structured error
                    logger = get_logger(func.__module__)
                    logger.error("Function execution failed", function=func.__name__, error=str(e), operation=op_name)

                    # Add extra context to Sentry
                    sentry_sdk.set_extra("function_args", str(args)[:500])  # Truncate long args
                    sentry_sdk.set_extra("function_kwargs", str(kwargs)[:500])

                    raise

        return wrapper

    return decorator


def track_errors_async(operation_name: str = None):
    """Async version of error tracking decorator."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"

            with sentry_sdk.configure_scope() as scope:
                scope.set_tag("operation", op_name)
                scope.set_context(
                    "function",
                    {
                        "name": func.__name__,
                        "module": func.__module__,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys()),
                    },
                )

                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    # Log structured error
                    logger = get_logger(func.__module__)
                    logger.error(
                        "Async function execution failed", function=func.__name__, error=str(e), operation=op_name
                    )

                    # Add extra context to Sentry
                    sentry_sdk.set_extra("function_args", str(args)[:500])
                    sentry_sdk.set_extra("function_kwargs", str(kwargs)[:500])

                    raise

        return wrapper

    return decorator


# Performance monitoring
def track_performance(operation_name: str = None):
    """Decorator to track performance metrics."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__name__}"

            with sentry_sdk.start_transaction(op="function", name=op_name, sampled=True) as transaction:
                transaction.set_tag("function_name", func.__name__)
                transaction.set_tag("module", func.__module__)

                try:
                    result = func(*args, **kwargs)
                    transaction.set_tag("status", "success")
                    return result
                except Exception as e:
                    transaction.set_tag("status", "error")
                    transaction.set_tag("error_type", type(e).__name__)
                    raise

        return wrapper

    return decorator


# Bot-specific monitoring functions
def set_user_context(user_id: int, username: str = None, first_name: str = None):
    """Set user context for better error tracking."""
    sentry_sdk.set_user({"id": str(user_id), "username": username, "name": first_name})


def add_bot_context(command: str = None, chat_type: str = None, message_type: str = None):
    """Add bot-specific context to Sentry."""
    sentry_sdk.set_context(
        "bot_interaction", {"command": command, "chat_type": chat_type, "message_type": message_type}
    )


def log_bot_metrics(metric_name: str, value: float, tags: dict = None):
    """Log bot performance metrics."""
    logger = get_logger("metrics")
    logger.info("Bot metric recorded", metric=metric_name, value=value, tags=tags or {})


# Enhanced alert functions
def setup_critical_alerts():
    """Setup critical alert rules for monitoring."""
    # These would typically be configured in Sentry UI, but we can set defaults

    critical_errors = [
        "Database connection failed",
        "Telegram API unreachable",
        "Bot crashed",
        "Memory limit exceeded",
        "Authentication failed",
    ]

    # Set alert rules in context
    sentry_sdk.set_context(
        "alert_rules",
        {
            "critical_errors": critical_errors,
            "alert_threshold_errors_per_minute": 10,
            "alert_threshold_response_time_ms": 5000,
            "alert_recipients": ["admin@doyobidiary.com"],
        },
    )


def alert_critical_error(error_type: str, details: str = None, user_id: int = None):
    """Send critical error alert to monitoring system."""
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("alert_level", "critical")
        scope.set_tag("error_type", error_type)

        if user_id:
            scope.set_tag("affected_user", str(user_id))

        scope.set_context(
            "alert_details",
            {
                "error_type": error_type,
                "details": details,
                "timestamp": time.time(),
                "requires_immediate_attention": True,
            },
        )

        # This will trigger an immediate alert
        sentry_sdk.capture_message(f"CRITICAL: {error_type}", level="error")

        logger = get_logger("alerts")
        logger.error("Critical alert triggered", error_type=error_type, details=details, user_id=user_id)


def alert_performance_degradation(operation: str, response_time_ms: float, threshold_ms: float = 1000):
    """Alert on performance degradation."""
    if response_time_ms > threshold_ms:
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("alert_level", "warning")
            scope.set_tag("operation", operation)
            scope.set_tag("performance_issue", True)

            scope.set_context(
                "performance",
                {
                    "operation": operation,
                    "response_time_ms": response_time_ms,
                    "threshold_ms": threshold_ms,
                    "degradation_factor": response_time_ms / threshold_ms,
                },
            )

            sentry_sdk.capture_message(
                f"Performance degradation detected: {operation} took {response_time_ms:.0f}ms", level="warning"
            )


def alert_high_error_rate(error_count: int, time_window_minutes: int = 5, threshold: int = 10):
    """Alert when error rate exceeds threshold."""
    if error_count > threshold:
        with sentry_sdk.configure_scope() as scope:
            scope.set_tag("alert_level", "critical")
            scope.set_tag("high_error_rate", True)

            scope.set_context(
                "error_rate",
                {
                    "error_count": error_count,
                    "time_window_minutes": time_window_minutes,
                    "threshold": threshold,
                    "rate_per_minute": error_count / time_window_minutes,
                },
            )

            sentry_sdk.capture_message(
                f"High error rate detected: {error_count} errors in {time_window_minutes} minutes", level="error"
            )


def check_system_health_and_alert(health_status):
    """Check system health and send alerts if needed."""
    from bot.services.health_service import SystemHealth

    if isinstance(health_status, SystemHealth):
        if health_status.status == "unhealthy":
            alert_critical_error(
                "System unhealthy", f"Multiple components failing: {list(health_status.components.keys())}"
            )
        elif health_status.status == "degraded":
            with sentry_sdk.configure_scope() as scope:
                scope.set_tag("alert_level", "warning")
                scope.set_context(
                    "system_health",
                    {
                        "status": health_status.status,
                        "degraded_components": [
                            name for name, comp in health_status.components.items() if comp.status != "healthy"
                        ],
                    },
                )

                sentry_sdk.capture_message("System performance degraded", level="warning")


# Error rate tracking
class ErrorRateTracker:
    """Track error rates for alerting."""

    def __init__(self, window_minutes: int = 5):
        self.window_minutes = window_minutes
        self.errors = []

    def record_error(self):
        """Record an error occurrence."""
        import time

        self.errors.append(time.time())
        self._cleanup_old_errors()

    def _cleanup_old_errors(self):
        """Remove errors outside the time window."""
        import time

        cutoff = time.time() - (self.window_minutes * 60)
        self.errors = [t for t in self.errors if t > cutoff]

    def get_error_rate(self) -> float:
        """Get errors per minute."""
        self._cleanup_old_errors()
        return len(self.errors) / self.window_minutes

    def check_and_alert(self, threshold: float = 2.0):
        """Check error rate and alert if threshold exceeded."""
        rate = self.get_error_rate()
        if rate > threshold:
            alert_high_error_rate(len(self.errors), self.window_minutes, int(threshold * self.window_minutes))


# Global error rate tracker
error_tracker = ErrorRateTracker()


def track_and_alert_error():
    """Track error and potentially send alert."""
    error_tracker.record_error()
    error_tracker.check_and_alert()


# Health monitoring scheduler
async def periodic_health_check(application, health_service, interval_minutes: int = 5):
    """Periodically check system health and send alerts."""
    import asyncio

    while True:
        try:
            health_status = await health_service.get_system_health(application)
            check_system_health_and_alert(health_status)

            # Log health status
            logger = get_logger("health_monitor")
            logger.info(
                "Periodic health check completed", status=health_status.status, uptime=health_status.uptime_seconds
            )

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            alert_critical_error("Health check failure", str(e))

        # Wait for next check
        await asyncio.sleep(interval_minutes * 60)


# Custom Sentry alert decorator
def critical_operation(operation_name: str):
    """Decorator to mark critical operations that should alert on failure."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                alert_critical_error(f"Critical operation failed: {operation_name}", str(e))
                raise

        return wrapper

    return decorator

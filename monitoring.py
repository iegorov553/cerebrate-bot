"""
Monitoring and logging configuration for Hour Watcher Bot.
"""
import os
import logging
import structlog
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.asyncio import AsyncioIntegration


def setup_monitoring():
    """Configure Sentry monitoring and structured logging."""
    
    # Get configuration from environment
    sentry_dsn = os.getenv("SENTRY_DSN")
    environment = os.getenv("ENVIRONMENT", "development")
    release = os.getenv("RELEASE_VERSION", "unknown")
    
    # Configure Sentry if DSN is provided
    if sentry_dsn:
        logging_integration = LoggingIntegration(
            level=logging.INFO,        # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        )
        
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                logging_integration,
                AsyncioIntegration(auto_enable_integrations=False)
            ],
            environment=environment,
            release=release,
            traces_sample_rate=0.1,  # 10% performance monitoring
            profiles_sample_rate=0.1,  # 10% profiling
            # Additional options
            before_send=before_send_filter,
            before_send_transaction=before_send_transaction_filter,
        )
        
        # Set user context
        sentry_sdk.set_context("bot", {
            "name": "Hour Watcher Bot",
            "version": release,
            "environment": environment
        })
    
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
            if any(skip_phrase in str(exc_value).lower() for skip_phrase in [
                'forbidden',
                'blocked',
                'message is too old',
                'chat not found',
                'user deactivated'
            ]):
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
            # Add extra fields
            structlog.contextvars.merge_contextvars,
            # Add timestamp
            structlog.processors.TimeStamper(fmt="ISO"),
            # Add log level
            structlog.processors.add_log_level,
            # Add logger name
            structlog.processors.add_logger_name,
            # Process stack info
            structlog.processors.CallsiteParameterAdder(
                parameters=[structlog.processors.CallsiteParameter.FUNC_NAME]
            ),
            # Format exceptions
            structlog.dev.ConsoleRenderer() if os.getenv("ENVIRONMENT") == "development" 
            else structlog.processors.JSONRenderer()
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.WriteLoggerFactory(),
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
                scope.set_context("function", {
                    "name": func.__name__,
                    "module": func.__module__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                })
                
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # Log structured error
                    logger = get_logger(func.__module__)
                    logger.error(
                        "Function execution failed",
                        function=func.__name__,
                        error=str(e),
                        operation=op_name
                    )
                    
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
                scope.set_context("function", {
                    "name": func.__name__,
                    "module": func.__module__,
                    "args_count": len(args),
                    "kwargs_keys": list(kwargs.keys())
                })
                
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    # Log structured error
                    logger = get_logger(func.__module__)
                    logger.error(
                        "Async function execution failed",
                        function=func.__name__,
                        error=str(e),
                        operation=op_name
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
            
            with sentry_sdk.start_transaction(
                op="function", 
                name=op_name,
                sampled=True
            ) as transaction:
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
    sentry_sdk.set_user({
        "id": str(user_id),
        "username": username,
        "name": first_name
    })


def add_bot_context(command: str = None, chat_type: str = None, message_type: str = None):
    """Add bot-specific context to Sentry."""
    sentry_sdk.set_context("bot_interaction", {
        "command": command,
        "chat_type": chat_type,
        "message_type": message_type
    })


def log_bot_metrics(metric_name: str, value: float, tags: dict = None):
    """Log bot performance metrics."""
    logger = get_logger("metrics")
    logger.info(
        "Bot metric recorded",
        metric=metric_name,
        value=value,
        tags=tags or {}
    )
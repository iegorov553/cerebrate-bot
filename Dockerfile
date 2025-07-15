# Dockerfile для Doyobi Diary Telegram Bot
# Основан на официальном Python image с Alpine Linux для минимального размера

FROM python:3.11-slim as base

# Метаданные
LABEL maintainer="Doyobi Diary Team"
LABEL description="Doyobi Diary - AI-powered activity tracking Telegram bot"
LABEL version="2.1.14"

# Переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"

# Создаем пользователя для запуска приложения (безопасность)
RUN groupadd -r botuser && useradd -r -g botuser -d /app -s /bin/bash botuser

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Создаем и активируем виртуальное окружение
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Обновляем pip
RUN pip install --upgrade pip setuptools wheel

# Создаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install -r requirements.txt

# Копируем исходный код
COPY . .

# Устанавливаем права доступа
RUN chown -R botuser:botuser /app
RUN chmod +x main.py

# Создаем директории для логов и временных файлов
RUN mkdir -p /app/logs /app/tmp && \
    chown -R botuser:botuser /app/logs /app/tmp

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import asyncio; from bot.services.health_service import HealthService; from bot.database.client import DatabaseClient; from bot.config import Config; \
        async def check(): \
            config = Config.from_env(); \
            db = DatabaseClient(config); \
            health = HealthService(db, '2.1.14'); \
            status = await health.get_system_health(); \
            exit(0 if status.status in ['healthy', 'degraded'] else 1); \
        asyncio.run(check())" || exit 1

# Переключаемся на непривилегированного пользователя
USER botuser

# Expose порт для health check (если потребуется HTTP endpoint)
EXPOSE 8080

# Команда запуска
CMD ["python", "main.py"]

# ---
# Multi-stage build для production
# ---

FROM base as production

# Production-specific настройки
ENV ENVIRONMENT=production \
    LOG_LEVEL=INFO

# Удаляем development зависимости (если есть отдельный requirements-prod.txt)
# RUN pip uninstall -y ruff mypy bandit pytest pytest-asyncio pytest-mock pytest-cov coverage

# Оптимизируем образ
RUN pip cache purge && \
    find /opt/venv -name "*.pyc" -delete && \
    find /opt/venv -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# ---
# Development stage
# ---

FROM base as development

# Development-specific настройки
ENV ENVIRONMENT=development \
    LOG_LEVEL=DEBUG

# Дополнительные development зависимости уже установлены из requirements.txt

# Команда для development с hot reload
CMD ["python", "-u", "main.py"]
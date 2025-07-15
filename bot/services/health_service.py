"""
Health Check Service для мониторинга состояния бота.

Этот модуль обеспечивает:
- Проверку подключения к базе данных
- Проверку доступности Telegram API
- Проверку состояния основных сервисов
- HTTP endpoint для внешнего мониторинга
"""

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bot.database.client import DatabaseClient
from monitoring import get_logger

logger = get_logger(__name__)


@dataclass
class HealthStatus:
    """Статус здоровья компонента."""

    status: str  # "healthy", "degraded", "unhealthy"
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class SystemHealth:
    """Общий статус здоровья системы."""

    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: str
    version: str
    uptime_seconds: float
    components: Dict[str, HealthStatus]

    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь для JSON."""
        result = asdict(self)
        # Преобразуем HealthStatus в словари
        result["components"] = {name: asdict(status) for name, status in self.components.items()}
        return result


class HealthService:
    """Сервис для проверки здоровья системы."""

    def __init__(self, db_client: DatabaseClient, version: str = "unknown"):
        """
        Инициализация сервиса здоровья.

        Args:
            db_client: Клиент базы данных
            version: Версия приложения
        """
        self.db_client = db_client
        self.version = version
        self.start_time = time.time()

        logger.info("HealthService инициализирован")

    async def check_database(self) -> HealthStatus:
        """Проверить подключение к базе данных."""
        start_time = time.time()

        try:
            # Проверяем, подключен ли клиент
            if not self.db_client.is_connected():
                latency_ms = (time.time() - start_time) * 1000
                return HealthStatus(
                    status="unhealthy",
                    latency_ms=latency_ms,
                    error="Database client not connected",
                    details={"connection": "failed", "client_initialized": False},
                )

            # Простой запрос для проверки соединения
            result = self.db_client.table("users").select("tg_id").limit(1).execute()

            latency_ms = (time.time() - start_time) * 1000

            if result.data is not None:
                return HealthStatus(
                    status="healthy",
                    latency_ms=latency_ms,
                    details={"connection": "active", "query_success": True, "client_initialized": True},
                )
            else:
                return HealthStatus(
                    status="degraded",
                    latency_ms=latency_ms,
                    error="Query returned None",
                    details={"connection": "active", "query_success": False},
                )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Database health check failed: {e}")

            return HealthStatus(status="unhealthy", latency_ms=latency_ms, error=str(e), details={"connection": "failed"})

    async def check_telegram_api(self, application) -> HealthStatus:
        """Проверить доступность Telegram API."""
        start_time = time.time()

        try:
            # Простая проверка через getMe
            bot_info = await application.bot.get_me()

            latency_ms = (time.time() - start_time) * 1000

            if bot_info and bot_info.id:
                return HealthStatus(
                    status="healthy",
                    latency_ms=latency_ms,
                    details={"bot_id": bot_info.id, "bot_username": bot_info.username, "api_accessible": True},
                )
            else:
                return HealthStatus(
                    status="degraded",
                    latency_ms=latency_ms,
                    error="Invalid bot info received",
                    details={"api_accessible": False},
                )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Telegram API health check failed: {e}")

            return HealthStatus(status="unhealthy", latency_ms=latency_ms, error=str(e), details={"api_accessible": False})

    async def check_scheduler(self, application) -> HealthStatus:
        """Проверить состояние планировщика."""
        try:
            scheduler = application.bot_data.get("multi_question_scheduler")

            if scheduler is None:
                return HealthStatus(
                    status="unhealthy", error="Scheduler not found in bot_data", details={"scheduler_exists": False}
                )

            # Проверим, что планировщик запущен
            if hasattr(scheduler, "running") and scheduler.running:
                return HealthStatus(
                    status="healthy", details={"scheduler_running": True, "scheduler_type": type(scheduler).__name__}
                )
            else:
                return HealthStatus(status="degraded", error="Scheduler not running", details={"scheduler_running": False})

        except Exception as e:
            logger.error(f"Scheduler health check failed: {e}")
            return HealthStatus(status="unhealthy", error=str(e), details={"scheduler_exists": False})

    async def get_system_health(self, application=None) -> SystemHealth:
        """Получить общий статус здоровья системы."""
        logger.debug("Выполняется проверка здоровья системы")

        # Выполним все проверки параллельно
        tasks = {
            "database": self.check_database(),
        }

        if application:
            tasks["telegram_api"] = self.check_telegram_api(application)
            tasks["scheduler"] = self.check_scheduler(application)

        # Ожидаем все проверки
        results = {}
        for name, task in tasks.items():
            try:
                results[name] = await task
            except Exception as e:
                logger.error(f"Health check failed for {name}: {e}")
                results[name] = HealthStatus(status="unhealthy", error=f"Check failed: {e}")

        # Определяем общий статус
        overall_status = self._determine_overall_status(results)

        # Создаем результат
        uptime_seconds = time.time() - self.start_time

        system_health = SystemHealth(
            status=overall_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            version=self.version,
            uptime_seconds=uptime_seconds,
            components=results,
        )

        logger.info(f"System health check completed: {overall_status}")
        return system_health

    def _determine_overall_status(self, components: Dict[str, HealthStatus]) -> str:
        """Определить общий статус на основе компонентов."""
        if not components:
            return "unhealthy"

        statuses = [comp.status for comp in components.values()]

        if all(status == "healthy" for status in statuses):
            return "healthy"
        elif any(status == "unhealthy" for status in statuses):
            return "unhealthy"
        else:
            return "degraded"

    async def get_health_json(self, application=None) -> str:
        """Получить статус здоровья в формате JSON."""
        try:
            health = await self.get_system_health(application)
            return json.dumps(health.to_dict(), indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to generate health JSON: {e}")

            # Fallback статус при ошибке
            fallback_health = SystemHealth(
                status="unhealthy",
                timestamp=datetime.now(timezone.utc).isoformat(),
                version=self.version,
                uptime_seconds=time.time() - self.start_time,
                components={"health_service": HealthStatus(status="unhealthy", error=f"Health check failed: {e}")},
            )
            return json.dumps(fallback_health.to_dict(), indent=2, ensure_ascii=False)

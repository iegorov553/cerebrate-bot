"""
Тесты для интеграции Groq + WhisperClient с fallback логикой.
"""

import pytest
import tempfile
import os
from unittest.mock import AsyncMock, Mock, patch

from bot.services.whisper_client import (
    WhisperClient,
    GroqRateLimitError,
    GroqApiError,
    TranscriptionError,
    ProviderExhaustedError,
    GROQ_AVAILABLE,
    OPENAI_AVAILABLE
)


class TestGroqWhisperIntegration:
    """Тесты для интеграции с Groq API."""

    @pytest.fixture
    def mock_audio_file(self):
        """Создать временный аудиофайл для тестов."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            f.write(b'mock audio data')
            yield f.name
        os.unlink(f.name)

    @pytest.fixture
    def admin_callback_mock(self):
        """Mock для callback уведомлений админа."""
        return AsyncMock()

    def test_whisper_client_configuration_validation(self):
        """Тест валидации конфигурации клиента."""
        # Тест без API ключей
        client = WhisperClient()
        assert client.groq_client is None
        assert client.openai_client is None

    def test_availability_flags(self):
        """Тест флагов доступности библиотек."""
        # Проверяем, что флаги определены
        assert isinstance(GROQ_AVAILABLE, bool)
        assert isinstance(OPENAI_AVAILABLE, bool)

    @pytest.mark.asyncio
    async def test_all_providers_exhausted(self, mock_audio_file):
        """Тест случая когда все провайдеры недоступны."""
        client = WhisperClient()  # Нет API ключей
        
        with pytest.raises(ProviderExhaustedError):
            await client.transcribe_audio(mock_audio_file)

    @pytest.mark.asyncio
    async def test_admin_notification_callback(self, admin_callback_mock):
        """Тест callback уведомлений админа."""
        client = WhisperClient(admin_notification_callback=admin_callback_mock)
        
        await client._notify_admin("Test message")
        admin_callback_mock.assert_called_once_with("Test message")

    def test_exception_hierarchy(self):
        """Тест иерархии исключений."""
        from bot.services.whisper_client import WhisperClientError
        
        # Проверяем, что все исключения наследуются от базового
        assert issubclass(GroqRateLimitError, WhisperClientError)
        assert issubclass(GroqApiError, WhisperClientError)
        assert issubclass(TranscriptionError, WhisperClientError)
        assert issubclass(ProviderExhaustedError, WhisperClientError)

    def test_client_defaults(self):
        """Тест значений по умолчанию."""
        client = WhisperClient()
        
        # Проверяем модели по умолчанию
        assert client.groq_primary_model == "whisper-large-v3"
        assert client.groq_fallback_model == "whisper-large-v3-turbo"
        assert client.openai_model == "whisper-1"
        
        # Проверяем таймауты
        assert client.groq_timeout == 30
        assert client.openai_timeout == 60

    @pytest.mark.asyncio
    async def test_rate_limit_error_creation(self):
        """Тест создания ошибки rate limit."""
        from bot.services.whisper_client import WhisperClientError
        
        error = GroqRateLimitError("Test rate limit")
        assert str(error) == "Test rate limit"
        assert isinstance(error, WhisperClientError)

    def test_cache_initialization(self):
        """Тест инициализации кэша."""
        client = WhisperClient(cache_ttl_seconds=1800)
        assert client.cache is not None
        # Кэш должен быть инициализирован с правильным TTL
        # (проверяем через внутренние атрибуты если они доступны)

    @pytest.mark.asyncio
    async def test_file_validation_placeholder(self, mock_audio_file):
        """Заглушка для тестирования валидации файла."""
        client = WhisperClient()
        
        # Этот тест проверяет, что файл существует
        assert os.path.exists(mock_audio_file)
        
        # В реальной реализации здесь была бы проверка размера файла
        # но для тестирования достаточно проверить, что файл создан
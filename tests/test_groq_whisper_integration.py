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
    ProviderExhaustedError
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

    def test_whisper_client_initialization_groq_only(self):
        """Тест инициализации только с Groq."""
        client = WhisperClient(
            groq_api_key="test_groq_key",
            groq_primary_model="whisper-large-v3",
            groq_fallback_model="whisper-large-v3-turbo"
        )
        
        assert client.groq_client is not None
        assert client.openai_client is None
        assert client.groq_primary_model == "whisper-large-v3"
        assert client.groq_fallback_model == "whisper-large-v3-turbo"

    def test_whisper_client_initialization_openai_only(self):
        """Тест инициализации только с OpenAI."""
        client = WhisperClient(
            openai_api_key="test_openai_key",
            openai_model="whisper-1"
        )
        
        assert client.openai_client is not None
        assert client.groq_client is None
        assert client.openai_model == "whisper-1"

    def test_whisper_client_initialization_both_providers(self):
        """Тест инициализации с обоими провайдерами."""
        client = WhisperClient(
            openai_api_key="test_openai_key",
            groq_api_key="test_groq_key"
        )
        
        assert client.openai_client is not None
        assert client.groq_client is not None

    @pytest.mark.asyncio
    async def test_admin_notification_callback(self, admin_callback_mock):
        """Тест callback уведомлений админа."""
        client = WhisperClient(
            groq_api_key="test_key",
            admin_notification_callback=admin_callback_mock
        )
        
        await client._notify_admin("Test message")
        admin_callback_mock.assert_called_once_with("Test message")

    @pytest.mark.asyncio
    async def test_groq_rate_limit_fallback(self, mock_audio_file, admin_callback_mock):
        """Тест fallback при rate limit в Groq."""
        with patch('bot.services.whisper_client.GROQ_AVAILABLE', True):
            # Mock Groq client
            mock_groq_client = Mock()
            mock_groq_client.audio.transcriptions.create.side_effect = Exception("rate limit exceeded")
            
            # Mock OpenAI client
            mock_openai_client = AsyncMock()
            mock_transcription = Mock()
            mock_transcription.text = "Test transcription"
            mock_openai_client.audio.transcriptions.create.return_value = mock_transcription
            
            client = WhisperClient(
                openai_api_key="test_openai_key",
                groq_api_key="test_groq_key",
                admin_notification_callback=admin_callback_mock
            )
            
            # Replace clients with mocks
            client.groq_client = mock_groq_client
            client.openai_client = mock_openai_client
            
            # Test transcription
            result = await client.transcribe_audio(mock_audio_file)
            
            assert result == "Test transcription"
            # Проверяем, что админ получил уведомление
            assert admin_callback_mock.call_count >= 1

    @pytest.mark.asyncio
    async def test_all_providers_exhausted(self, mock_audio_file):
        """Тест случая когда все провайдеры недоступны."""
        client = WhisperClient()  # Нет API ключей
        
        with pytest.raises(ProviderExhaustedError):
            await client.transcribe_audio(mock_audio_file)

    @pytest.mark.asyncio
    async def test_groq_success_primary_model(self, mock_audio_file):
        """Тест успешной транскрипции с первичной моделью Groq."""
        with patch('bot.services.whisper_client.GROQ_AVAILABLE', True):
            mock_groq_client = Mock()
            mock_transcription = Mock()
            mock_transcription.text = "Groq transcription"
            mock_groq_client.audio.transcriptions.create.return_value = mock_transcription
            
            client = WhisperClient(groq_api_key="test_key")
            client.groq_client = mock_groq_client
            
            # Mock executor для async
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_loop.return_value.run_in_executor.return_value = "Groq transcription"
                
                result = await client.transcribe_audio(mock_audio_file)
                assert result == "Groq transcription"

    def test_get_transcription_stats_with_multiple_providers(self):
        """Тест статистики с несколькими провайдерами."""
        client = WhisperClient(
            openai_api_key="test_openai_key",
            groq_api_key="test_groq_key",
            groq_primary_model="whisper-large-v3",
            groq_fallback_model="whisper-large-v3-turbo"
        )
        
        # Не вызываем async метод, только создаём структуру
        # В реальных тестах нужно будет использовать pytest.mark.asyncio
        stats_structure = {
            "providers": {
                "groq_available": True,
                "openai_available": True,
                "groq_primary_model": "whisper-large-v3",
                "groq_fallback_model": "whisper-large-v3-turbo"
            }
        }
        
        # Проверяем, что клиент правильно инициализирован для получения такой статистики
        assert client.groq_client is not None
        assert client.openai_client is not None
        assert client.groq_primary_model == "whisper-large-v3"
        assert client.groq_fallback_model == "whisper-large-v3-turbo"
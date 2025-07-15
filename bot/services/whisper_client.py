"""
WhisperClient - Интеграция с OpenAI Whisper API для расшифровки голосовых сообщений.

Этот модуль обеспечивает:
- Отправку аудиофайлов в Whisper API
- Обработку ошибок и ограничений
- Кэширование результатов
- Логирование операций
"""

import os
import asyncio
from typing import Optional, Dict, Any, Union
from openai import AsyncOpenAI
from openai.types.audio import Transcription

from bot.cache.ttl_cache import TTLCache
from monitoring import get_logger

# Groq import (will be optional)
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

logger = get_logger(__name__)


class WhisperClientError(Exception):
    """Base exception for WhisperClient errors."""
    pass


class AudioTooLargeError(WhisperClientError):
    """Raised when audio file is too large."""
    pass


class AudioTooLongError(WhisperClientError):
    """Raised when audio is too long."""
    pass


class TranscriptionError(WhisperClientError):
    """Raised when transcription fails."""
    pass


class GroqRateLimitError(WhisperClientError):
    """Raised when Groq rate limit is exceeded."""
    pass


class GroqApiError(WhisperClientError):
    """Raised when Groq API fails."""
    pass


class ProviderExhaustedError(WhisperClientError):
    """Raised when all providers are exhausted."""
    pass


class WhisperClient:
    """Client for OpenAI Whisper API integration."""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        openai_model: str = "whisper-1",
        groq_primary_model: str = "whisper-large-v3",
        groq_fallback_model: str = "whisper-large-v3-turbo",
        groq_timeout_seconds: int = 30,
        openai_timeout_seconds: int = 60,
        max_file_size_mb: int = 25,
        max_duration_seconds: int = 120,
        cache_ttl_seconds: int = 3600,
        admin_notification_callback: Optional[callable] = None
    ):
        """
        Initialize WhisperClient with multiple providers.

        Args:
            openai_api_key: OpenAI API key (optional)
            groq_api_key: Groq API key (optional)
            openai_model: OpenAI model to use (default: whisper-1)
            groq_primary_model: Primary Groq model (default: whisper-large-v3)
            groq_fallback_model: Fallback Groq model (default: whisper-large-v3-turbo)
            groq_timeout_seconds: Timeout for Groq API calls (default: 30)
            openai_timeout_seconds: Timeout for OpenAI API calls (default: 60)
            max_file_size_mb: Maximum file size in MB (default: 25)
            max_duration_seconds: Maximum audio duration in seconds (default: 120)
            cache_ttl_seconds: Cache TTL for transcription results (default: 3600)
            admin_notification_callback: Callback function for admin notifications
        """
        # API clients
        self.openai_client = AsyncOpenAI(api_key=openai_api_key) if openai_api_key else None
        self.groq_client = Groq(api_key=groq_api_key) if groq_api_key and GROQ_AVAILABLE else None
        
        # Models and timeouts
        self.openai_model = openai_model
        self.groq_primary_model = groq_primary_model
        self.groq_fallback_model = groq_fallback_model
        self.groq_timeout = groq_timeout_seconds
        self.openai_timeout = openai_timeout_seconds
        
        # Validation
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.max_duration_seconds = max_duration_seconds

        # Cache for transcription results
        self.cache = TTLCache(ttl_seconds=cache_ttl_seconds)
        
        # Admin notification callback
        self.admin_notification_callback = admin_notification_callback

        # Log initialization
        providers = []
        if self.groq_client:
            providers.append(f"Groq({groq_primary_model}, {groq_fallback_model})")
        if self.openai_client:
            providers.append(f"OpenAI({openai_model})")
        
        logger.info(
            f"WhisperClient initialized with providers: {', '.join(providers)}, "
            f"max_file_size={max_file_size_mb}MB, "
            f"max_duration={max_duration_seconds}s"
        )

    def _get_cache_key(self, file_hash: str) -> str:
        """Generate cache key for audio file."""
        return f"whisper_transcription_{file_hash}"

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate simple hash for audio file (using file size and name)."""
        import hashlib
        stat = os.stat(file_path)
        # Simple hash based on file size and modification time
        hash_input = f"{stat.st_size}_{stat.st_mtime}_{os.path.basename(file_path)}"
        return hashlib.sha256(hash_input.encode()).hexdigest()

    async def _validate_audio_file(self, file_path: str, duration_seconds: Optional[int] = None) -> None:
        """
        Validate audio file constraints.

        Args:
            file_path: Path to audio file
            duration_seconds: Audio duration in seconds (if known)

        Raises:
            AudioTooLargeError: If file is too large
            AudioTooLongError: If audio is too long
        """
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > self.max_file_size_bytes:
            raise AudioTooLargeError(
                f"Audio file size {file_size / (1024 * 1024):.1f}MB exceeds limit "
                f"{self.max_file_size_bytes / (1024 * 1024)}MB"
            )

        # Check duration if provided
        if duration_seconds and duration_seconds > self.max_duration_seconds:
            raise AudioTooLongError(
                f"Audio duration {duration_seconds}s exceeds limit {self.max_duration_seconds}s"
            )

        logger.debug(f"Audio file validation passed: {file_size} bytes, {duration_seconds}s")

    async def _notify_admin(self, message: str) -> None:
        """Send notification to admin if callback is configured."""
        if self.admin_notification_callback:
            try:
                await self.admin_notification_callback(message)
            except Exception as e:
                logger.error(f"Failed to send admin notification: {e}")

    async def _transcribe_with_groq(
        self,
        file_path: str,
        model: str,
        language: Optional[str] = None
    ) -> str:
        """
        Transcribe audio using Groq API.
        
        Args:
            file_path: Path to audio file
            model: Groq model to use
            language: Language code (optional)
            
        Returns:
            Transcribed text
            
        Raises:
            GroqRateLimitError: If rate limit is exceeded
            GroqApiError: If API call fails
        """
        if not self.groq_client:
            raise GroqApiError("Groq client not initialized")
        
        logger.info(f"Transcribing with Groq model: {model}")
        
        try:
            # Run Groq transcription with timeout
            def _groq_transcribe():
                with open(file_path, 'rb') as audio_file:
                    transcription = self.groq_client.audio.transcriptions.create(
                        file=(file_path, audio_file.read()),
                        model=model,
                        language=language
                    )
                    return transcription.text
            
            # Run in executor with timeout
            text = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, _groq_transcribe),
                timeout=self.groq_timeout
            )
            
            if not text or not text.strip():
                raise GroqApiError("Empty transcription result from Groq")
            
            logger.info(f"Groq transcription successful: {len(text)} characters")
            return text.strip()
            
        except asyncio.TimeoutError:
            raise GroqApiError(f"Groq API timeout after {self.groq_timeout}s")
        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "quota" in error_msg:
                raise GroqRateLimitError(f"Groq rate limit exceeded: {e}")
            else:
                raise GroqApiError(f"Groq API error: {e}")

    async def _transcribe_with_openai(
        self,
        file_path: str,
        language: Optional[str] = None
    ) -> str:
        """
        Transcribe audio using OpenAI API.
        
        Args:
            file_path: Path to audio file
            language: Language code (optional)
            
        Returns:
            Transcribed text
            
        Raises:
            TranscriptionError: If transcription fails
        """
        if not self.openai_client:
            raise TranscriptionError("OpenAI client not initialized")
        
        logger.info(f"Transcribing with OpenAI model: {self.openai_model}")
        
        try:
            # OpenAI transcription with timeout
            with open(file_path, 'rb') as audio_file:
                transcription_params = {
                    "model": self.openai_model,
                    "file": audio_file,
                    "response_format": "text"
                }
                
                if language:
                    transcription_params["language"] = language
                
                transcription = await asyncio.wait_for(
                    self.openai_client.audio.transcriptions.create(**transcription_params),
                    timeout=self.openai_timeout
                )
            
            # Extract text from response
            if hasattr(transcription, 'text'):
                text = transcription.text.strip()
            else:
                text = str(transcription).strip()
            
            if not text:
                raise TranscriptionError("Empty transcription result from OpenAI")
            
            logger.info(f"OpenAI transcription successful: {len(text)} characters")
            return text
            
        except asyncio.TimeoutError:
            raise TranscriptionError(f"OpenAI API timeout after {self.openai_timeout}s")
        except Exception as e:
            raise TranscriptionError(f"OpenAI API error: {e}")

    async def transcribe_audio(
        self,
        file_path: str,
        language: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        use_cache: bool = True
    ) -> str:
        """
        Transcribe audio file using fallback strategy: Groq → OpenAI.

        Args:
            file_path: Path to audio file
            language: Language code (e.g., 'ru', 'en'). If None, auto-detect
            duration_seconds: Audio duration in seconds (for validation)
            use_cache: Whether to use cache for results

        Returns:
            Transcribed text

        Raises:
            AudioTooLargeError: If file is too large
            AudioTooLongError: If audio is too long
            ProviderExhaustedError: If all providers fail
        """
        try:
            # Validate audio file
            await self._validate_audio_file(file_path, duration_seconds)

            # Check cache first
            if use_cache:
                file_hash = self._calculate_file_hash(file_path)
                cache_key = self._get_cache_key(file_hash)
                cached_result = await self.cache.get(cache_key)
                if cached_result:
                    logger.info(f"Using cached transcription for {file_path}")
                    return cached_result

            logger.info(f"Starting transcription for {file_path} (language: {language})")

            # Strategy 1: Try Groq primary model
            if self.groq_client:
                try:
                    text = await self._transcribe_with_groq(
                        file_path, 
                        self.groq_primary_model, 
                        language
                    )
                    
                    # Cache successful result
                    if use_cache:
                        await self.cache.set(cache_key, text)
                    
                    logger.info(f"Transcription completed with Groq primary: {len(text)} characters")
                    return text
                    
                except GroqRateLimitError as e:
                    logger.warning(f"Groq primary model rate limited: {e}")
                    await self._notify_admin(f"⚠️ Groq {self.groq_primary_model} лимит исчерпан, переключаемся на {self.groq_fallback_model}")
                    
                except GroqApiError as e:
                    logger.warning(f"Groq primary model failed: {e}")

            # Strategy 2: Try Groq fallback model
            if self.groq_client:
                try:
                    text = await self._transcribe_with_groq(
                        file_path, 
                        self.groq_fallback_model, 
                        language
                    )
                    
                    # Cache successful result
                    if use_cache:
                        await self.cache.set(cache_key, text)
                    
                    logger.info(f"Transcription completed with Groq fallback: {len(text)} characters")
                    return text
                    
                except GroqRateLimitError as e:
                    logger.warning(f"Groq fallback model rate limited: {e}")
                    await self._notify_admin(f"🔄 Groq лимиты исчерпаны, используем OpenAI")
                    
                except GroqApiError as e:
                    logger.warning(f"Groq fallback model failed: {e}")

            # Strategy 3: Try OpenAI
            if self.openai_client:
                try:
                    text = await self._transcribe_with_openai(file_path, language)
                    
                    # Cache successful result
                    if use_cache:
                        await self.cache.set(cache_key, text)
                    
                    logger.info(f"Transcription completed with OpenAI: {len(text)} characters")
                    return text
                    
                except TranscriptionError as e:
                    logger.error(f"OpenAI transcription failed: {e}")

            # All providers failed
            raise ProviderExhaustedError("All transcription providers failed or unavailable")

        except (AudioTooLargeError, AudioTooLongError):
            # Re-raise validation errors as-is
            raise
        except ProviderExhaustedError:
            # Re-raise provider exhaustion as-is
            raise
        except Exception as e:
            logger.error(f"Transcription failed for {file_path}: {e}")
            raise TranscriptionError(f"Failed to transcribe audio: {e}") from e

    async def get_supported_formats(self) -> list[str]:
        """
        Get list of supported audio formats.

        Returns:
            List of supported file extensions
        """
        # OpenAI Whisper supported formats
        return [
            'mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm', 'ogg', 'oga'
        ]

    def is_format_supported(self, file_extension: str) -> bool:
        """
        Check if audio format is supported.

        Args:
            file_extension: File extension (with or without dot)

        Returns:
            True if format is supported
        """
        ext = file_extension.lower().lstrip('.')
        return ext in ['mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm', 'ogg', 'oga']

    async def get_transcription_stats(self) -> Dict[str, Any]:
        """
        Get transcription statistics.

        Returns:
            Dictionary with statistics
        """
        cache_stats = await self.cache.get_stats()
        
        # Provider information
        providers = {
            "groq_available": self.groq_client is not None,
            "openai_available": self.openai_client is not None,
        }
        
        if self.groq_client:
            providers.update({
                "groq_primary_model": self.groq_primary_model,
                "groq_fallback_model": self.groq_fallback_model,
                "groq_timeout": self.groq_timeout
            })
        
        if self.openai_client:
            providers.update({
                "openai_model": self.openai_model,
                "openai_timeout": self.openai_timeout
            })
        
        return {
            "providers": providers,
            "max_file_size_mb": self.max_file_size_bytes / (1024 * 1024),
            "max_duration_seconds": self.max_duration_seconds,
            "cache_hits": cache_stats.get("hits", 0),
            "cache_misses": cache_stats.get("misses", 0),
            "cache_size": cache_stats.get("size", 0)
        }

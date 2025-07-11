"""
WhisperClient - Интеграция с OpenAI Whisper API для расшифровки голосовых сообщений.

Этот модуль обеспечивает:
- Отправку аудиофайлов в Whisper API
- Обработку ошибок и ограничений
- Кэширование результатов
- Логирование операций
"""

import os
import tempfile
from typing import Optional, Dict, Any
import aiofiles
import aiohttp
from openai import AsyncOpenAI
from openai.types.audio import Transcription

from bot.cache.ttl_cache import TTLCache
from monitoring import get_logger

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


class WhisperClient:
    """Client for OpenAI Whisper API integration."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "whisper-1",
        max_file_size_mb: int = 25,
        max_duration_seconds: int = 120,
        cache_ttl_seconds: int = 3600
    ):
        """
        Initialize WhisperClient.
        
        Args:
            api_key: OpenAI API key
            model: Whisper model to use (default: whisper-1)
            max_file_size_mb: Maximum file size in MB (default: 25)
            max_duration_seconds: Maximum audio duration in seconds (default: 120)
            cache_ttl_seconds: Cache TTL for transcription results (default: 3600)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.max_duration_seconds = max_duration_seconds
        
        # Cache for transcription results (to avoid re-transcribing same audio)
        self.cache = TTLCache(ttl_seconds=cache_ttl_seconds)
        
        logger.info(
            f"WhisperClient initialized with model={model}, "
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
        return hashlib.md5(hash_input.encode()).hexdigest()
    
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
                f"Audio file size {file_size / (1024*1024):.1f}MB exceeds limit "
                f"{self.max_file_size_bytes / (1024*1024)}MB"
            )
        
        # Check duration if provided
        if duration_seconds and duration_seconds > self.max_duration_seconds:
            raise AudioTooLongError(
                f"Audio duration {duration_seconds}s exceeds limit {self.max_duration_seconds}s"
            )
        
        logger.debug(f"Audio file validation passed: {file_size} bytes, {duration_seconds}s")
    
    async def transcribe_audio(
        self,
        file_path: str,
        language: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        use_cache: bool = True
    ) -> str:
        """
        Transcribe audio file using Whisper API.
        
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
            TranscriptionError: If transcription fails
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
            
            # Transcribe using OpenAI Whisper
            logger.info(f"Starting transcription for {file_path} (language: {language})")
            
            try:
                # OpenAI client requires regular file objects, not async
                with open(file_path, 'rb') as audio_file:
                    transcription_params = {
                        "model": self.model,
                        "file": audio_file,
                        "response_format": "text"
                    }
                    
                    if language:
                        transcription_params["language"] = language
                    
                    logger.info(f"Calling OpenAI Whisper API with model={self.model}, language={language}")
                    transcription: Transcription = await self.client.audio.transcriptions.create(
                        **transcription_params
                    )
                    logger.info(f"OpenAI API call successful")
            except Exception as api_error:
                logger.error(f"OpenAI API call failed: {type(api_error).__name__}: {api_error}")
                raise
                
                # Extract text from response
                if hasattr(transcription, 'text'):
                    text = transcription.text.strip()
                else:
                    # Handle different response formats
                    text = str(transcription).strip()
                
                if not text:
                    raise TranscriptionError("Empty transcription result")
                
                # Cache successful result
                if use_cache:
                    await self.cache.set(cache_key, text)
                
                logger.info(
                    f"Transcription completed successfully: {len(text)} characters, "
                    f"language: {language or 'auto'}"
                )
                
                return text
                
        except (AudioTooLargeError, AudioTooLongError):
            # Re-raise validation errors as-is
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
        return {
            "model": self.model,
            "max_file_size_mb": self.max_file_size_bytes / (1024 * 1024),
            "max_duration_seconds": self.max_duration_seconds,
            "cache_hits": cache_stats.get("hits", 0),
            "cache_misses": cache_stats.get("misses", 0),
            "cache_size": cache_stats.get("size", 0)
        }
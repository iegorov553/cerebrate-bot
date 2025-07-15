# Voice Recognition System

## Overview

The Doyobi Diary bot features a sophisticated multi-provider voice recognition system that provides reliable speech-to-text transcription with automatic fallback capabilities. The system prioritizes cost-effective and fast providers while maintaining high accuracy through intelligent provider switching.

## Architecture

### Multi-Provider Fallback System

The voice recognition system uses a three-tier fallback architecture:

1. **Primary Provider**: Groq whisper-large-v3 (30s timeout)
2. **Fallback Provider**: Groq whisper-large-v3-turbo (30s timeout)  
3. **Final Fallback**: OpenAI whisper-1 (60s timeout)

### Provider Selection Logic

```python
async def transcribe_audio(self, file_path: str, language: Optional[str] = None) -> str:
    # Strategy 1: Try Groq primary model
    if self.groq_client:
        try:
            text = await self._transcribe_with_groq(file_path, self.groq_primary_model, language)
            return text
        except GroqRateLimitError:
            await self._notify_admin(f"⚠️ Groq {self.groq_primary_model} лимит исчерпан")
    
    # Strategy 2: Try Groq fallback model
    if self.groq_client and self.groq_fallback_model:
        try:
            text = await self._transcribe_with_groq(file_path, self.groq_fallback_model, language)
            return text
        except GroqRateLimitError:
            await self._notify_admin(f"⚠️ Groq {self.groq_fallback_model} лимит исчерпан")
    
    # Strategy 3: Try OpenAI fallback
    if self.openai_client:
        try:
            text = await self._transcribe_with_openai(file_path, language)
            return text
        except Exception as e:
            await self._notify_admin(f"❌ OpenAI Whisper ошибка: {str(e)}")
    
    # All providers exhausted
    raise ProviderExhaustedError("All voice recognition providers are unavailable")
```

## Configuration

### Environment Variables

```bash
# Primary provider (recommended)
export GROQ_API_KEY="gsk_your_groq_key"

# Fallback provider
export OPENAI_API_KEY="sk_your_openai_key"

# Model configuration (optional)
export GROQ_PRIMARY_MODEL="whisper-large-v3"        # Default
export GROQ_FALLBACK_MODEL="whisper-large-v3-turbo" # Default
export GROQ_TIMEOUT_SECONDS="30"                    # Default
```

### Configuration Class

The system uses a centralized configuration approach in `bot/config.py`:

```python
@dataclass
class Config:
    groq_api_key: Optional[str] = None
    groq_primary_model: str = "whisper-large-v3"
    groq_fallback_model: str = "whisper-large-v3-turbo"
    groq_timeout_seconds: int = 30
    openai_api_key: Optional[str] = None
    
    def is_groq_enabled(self) -> bool:
        return bool(self.groq_api_key)
    
    def is_voice_recognition_enabled(self) -> bool:
        return self.is_groq_enabled() or bool(self.openai_api_key)
```

## Provider Details

### Groq Whisper Models

#### whisper-large-v3 (Primary)
- **Accuracy**: Highest quality transcription
- **Speed**: Fast processing (typically 2-5 seconds)
- **Cost**: Cost-effective compared to OpenAI
- **Timeout**: 30 seconds
- **Use Case**: General voice messages, high accuracy required

#### whisper-large-v3-turbo (Fallback)
- **Accuracy**: Good quality transcription
- **Speed**: Faster than primary model
- **Cost**: More cost-effective than primary
- **Timeout**: 30 seconds
- **Use Case**: High-volume scenarios, rate limit fallback

### OpenAI Whisper (Final Fallback)

#### whisper-1
- **Accuracy**: High quality transcription
- **Speed**: Slower than Groq models
- **Cost**: Higher cost per request
- **Timeout**: 60 seconds
- **Use Case**: Emergency fallback when Groq is unavailable

## Error Handling

### Exception Hierarchy

```python
class GroqApiError(Exception):
    """Base exception for Groq API errors"""
    pass

class GroqRateLimitError(GroqApiError):
    """Raised when Groq API rate limit is exceeded"""
    pass

class ProviderExhaustedError(Exception):
    """Raised when all voice recognition providers are unavailable"""
    pass
```

### Rate Limit Detection

The system automatically detects rate limits and switches providers:

```python
async def _transcribe_with_groq(self, file_path: str, model: str, language: Optional[str] = None) -> str:
    try:
        # ... transcription logic
    except Exception as e:
        error_message = str(e).lower()
        if "rate_limit_exceeded" in error_message or "rate limit" in error_message:
            raise GroqRateLimitError(f"Groq rate limit exceeded for model {model}")
        raise GroqApiError(f"Groq API error: {str(e)}")
```

### Admin Notifications

When providers fail or rate limits are hit, the system automatically notifies administrators:

```python
async def _notify_admin(self, message: str):
    """Send notification to admin about provider issues"""
    if self.admin_notify_callback:
        try:
            await self.admin_notify_callback(message)
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
```

## Performance Optimization

### Caching Strategy

The system implements intelligent caching across all providers:

```python
# Cache key includes provider info for debugging
cache_key = f"voice_{hash(file_path)}_{language or 'auto'}"
cached_result = self.cache.get(cache_key)
if cached_result:
    return cached_result

# Cache successful results regardless of provider
self.cache.set(cache_key, transcription_text, ttl=3600)  # 1 hour
```

### Timeout Management

Different providers have optimized timeouts:
- **Groq models**: 30 seconds (fast processing expected)
- **OpenAI**: 60 seconds (slower but more reliable)

```python
async def _transcribe_with_groq(self, file_path: str, model: str, language: Optional[str] = None) -> str:
    try:
        async with asyncio.timeout(self.groq_timeout_seconds):
            # ... transcription logic
    except asyncio.TimeoutError:
        raise GroqApiError(f"Groq transcription timeout after {self.groq_timeout_seconds}s")
```

## Usage Examples

### Basic Usage

```python
from bot.services.whisper_client import WhisperClient
from bot.config import Config

config = Config()
whisper_client = WhisperClient(config)

# Transcribe with automatic provider selection
text = await whisper_client.transcribe_audio("/path/to/audio.ogg")
```

### With Language Detection

```python
# Specify language for better accuracy
text = await whisper_client.transcribe_audio("/path/to/audio.ogg", language="ru")
```

### With Admin Notifications

```python
async def admin_callback(message: str):
    # Send message to admin via Telegram
    await bot.send_message(chat_id=ADMIN_ID, text=message)

whisper_client = WhisperClient(config, admin_notify_callback=admin_callback)
```

## Rate Limiting Integration

The voice recognition system integrates with the bot's rate limiting system:

```python
# In voice_handlers.py
@rate_limit("voice_message", 10, 3600)  # 10 per hour
async def handle_voice_message(update: Update, context: CallbackContext):
    try:
        transcription = await whisper_client.transcribe_audio(file_path)
        # ... handle transcription
    except ProviderExhaustedError:
        await update.message.reply_text(
            translator.get_text("error_all_providers_exhausted", update.effective_user.language_code)
        )
```

## Monitoring and Logging

### Structured Logging

```python
import structlog

logger = structlog.get_logger(__name__)

async def transcribe_audio(self, file_path: str, language: Optional[str] = None) -> str:
    logger.info(
        "voice_transcription_started",
        file_path=file_path,
        language=language,
        primary_provider="groq",
        fallback_available=self.openai_client is not None
    )
```

### Performance Metrics

The system tracks key performance indicators:
- **Provider success rates**
- **Average transcription time**
- **Cache hit rates**
- **Rate limit occurrences**
- **Fallback usage patterns**

## Troubleshooting

### Common Issues

#### 1. All Providers Unavailable
```
Error: ProviderExhaustedError: All voice recognition providers are unavailable
```
**Solution**: Check API keys and network connectivity

#### 2. Rate Limit Exceeded
```
Error: GroqRateLimitError: Groq rate limit exceeded for model whisper-large-v3
```
**Solution**: System automatically falls back to next provider

#### 3. File Format Issues
```
Error: Unsupported audio format
```
**Solution**: Ensure audio is in supported format (OGG, MP3, WAV, M4A)

### Debug Mode

Enable debug logging for detailed provider information:

```python
import logging
logging.getLogger("bot.services.whisper_client").setLevel(logging.DEBUG)
```

## Testing

### Unit Tests

```python
# tests/test_voice_recognition.py
import pytest
from unittest.mock import AsyncMock, patch
from bot.services.whisper_client import WhisperClient, GroqRateLimitError

@pytest.mark.asyncio
async def test_groq_primary_fallback():
    """Test fallback from primary to turbo model"""
    config = Config(groq_api_key="test_key")
    
    with patch('groq.AsyncGroq') as mock_groq:
        mock_client = AsyncMock()
        mock_groq.return_value = mock_client
        
        # Primary model fails with rate limit
        mock_client.audio.transcriptions.create.side_effect = [
            Exception("rate_limit_exceeded"),
            AsyncMock(text="transcribed text")
        ]
        
        whisper_client = WhisperClient(config)
        result = await whisper_client.transcribe_audio("test.ogg")
        
        assert result == "transcribed text"
        assert mock_client.audio.transcriptions.create.call_count == 2
```

### Integration Tests

```python
@pytest.mark.integration
async def test_end_to_end_voice_recognition():
    """Test complete voice recognition flow"""
    config = Config(
        groq_api_key=os.getenv("GROQ_API_KEY"),
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
    
    whisper_client = WhisperClient(config)
    
    # Test with real audio file
    result = await whisper_client.transcribe_audio("tests/fixtures/test_audio.ogg")
    
    assert isinstance(result, str)
    assert len(result) > 0
```

## Future Enhancements

### Planned Features

1. **Dynamic Provider Selection**
   - Quality-based routing
   - Cost optimization algorithms
   - Performance-based switching

2. **Advanced Caching**
   - Persistent cache storage
   - Cache warming strategies
   - Intelligent cache invalidation

3. **Analytics Dashboard**
   - Provider performance metrics
   - Cost analysis and optimization
   - Usage patterns and trends

4. **Language-Specific Optimization**
   - Provider selection based on language
   - Language-specific model fine-tuning
   - Confidence scoring

### Contributing

When adding new providers or features:

1. Extend the `WhisperClient` class
2. Add appropriate error handling
3. Update configuration system
4. Add comprehensive tests
5. Update documentation
6. Maintain backward compatibility

For detailed implementation guidance, see [ARCHITECTURE.md](ARCHITECTURE.md) and [DEVELOPMENT.md](DEVELOPMENT.md).
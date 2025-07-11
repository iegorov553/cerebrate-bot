"""
Voice message handlers for the Telegram bot.

This module handles voice messages by:
1. Downloading audio files from Telegram
2. Transcribing them using Whisper API
3. Processing transcribed text as regular messages
"""

import os
import tempfile
from typing import Optional
import aiofiles
from telegram import Update, Voice
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from bot.cache.ttl_cache import TTLCache
from bot.config import Config
from bot.database.client import DatabaseClient
from bot.services.whisper_client import (
    WhisperClient, 
    WhisperClientError, 
    AudioTooLargeError, 
    AudioTooLongError,
    TranscriptionError
)
from bot.utils.rate_limiter import MultiTierRateLimiter, rate_limit
from monitoring import get_logger, set_user_context, track_errors_async

logger = get_logger(__name__)


async def download_voice_file(voice: Voice, bot, temp_dir: str) -> tuple[str, str]:
    """
    Download voice file from Telegram.
    
    Args:
        voice: Telegram Voice object
        bot: Telegram bot instance
        temp_dir: Temporary directory for file storage
        
    Returns:
        Tuple of (file_path, file_extension)
        
    Raises:
        Exception: If download fails
    """
    try:
        # Get file from Telegram
        file = await bot.get_file(voice.file_id)
        
        # Determine file extension (Telegram usually sends .oga for voice)
        file_extension = 'oga'
        if file.file_path:
            _, ext = os.path.splitext(file.file_path)
            if ext:
                file_extension = ext.lstrip('.')
        
        # Create temporary file
        temp_file_path = os.path.join(temp_dir, f"{voice.file_id}.{file_extension}")
        
        # Download file
        await file.download_to_drive(temp_file_path)
        
        logger.info(f"Voice file downloaded: {temp_file_path}, size: {os.path.getsize(temp_file_path)} bytes")
        
        return temp_file_path, file_extension
        
    except Exception as e:
        logger.error(f"Failed to download voice file {voice.file_id}: {e}")
        raise


async def send_voice_processing_message(update: Update, translator) -> int:
    """
    Send temporary processing message to user.
    
    Args:
        update: Telegram update
        translator: User translator instance
        
    Returns:
        Message ID of the processing message
    """
    try:
        processing_text = translator.translate('voice.processing')
        message = await update.message.reply_text(processing_text)
        return message.message_id
    except Exception as e:
        logger.error(f"Failed to send processing message: {e}")
        return None


async def update_processing_message(update: Update, message_id: int, text: str, bot) -> None:
    """
    Update processing message with final result.
    
    Args:
        update: Telegram update
        message_id: ID of message to update
        text: New text for the message
        bot: Bot instance
    """
    try:
        if message_id:
            await bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=text
            )
    except Exception as e:
        logger.error(f"Failed to update processing message: {e}")


@rate_limit("voice_message")
@track_errors_async("handle_voice_message")
async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle voice messages by transcribing them and processing as text."""
    user = update.effective_user
    message = update.message
    
    if not user or not message or not message.voice:
        return
    
    set_user_context(user.id, user.username, user.first_name)
    
    # Get dependencies
    db_client: DatabaseClient = context.bot_data['db_client']
    user_cache: TTLCache = context.bot_data['user_cache']
    config: Config = context.bot_data['config']
    
    # Get user translator
    from bot.handlers.callback_handlers import get_user_translator
    translator = await get_user_translator(user.id, db_client, user_cache)
    
    # Send processing message
    processing_message_id = await send_voice_processing_message(update, translator)
    
    # Create temporary directory for audio file
    temp_dir = None
    temp_file_path = None
    
    try:
        # Check if Whisper is configured
        if not config.openai_api_key:
            error_text = translator.translate('voice.error_not_configured')
            await update_processing_message(update, processing_message_id, error_text, context.bot)
            return
        
        # Create WhisperClient
        whisper_client = WhisperClient(
            api_key=config.openai_api_key,
            model=config.whisper_model,
            max_file_size_mb=config.max_voice_file_size_mb,
            max_duration_seconds=config.max_voice_duration_seconds
        )
        
        # Check if file format is supported
        file_extension = 'oga'  # Default for Telegram voice messages
        if not whisper_client.is_format_supported(file_extension):
            error_text = translator.translate('voice.error_unsupported_format')
            await update_processing_message(update, processing_message_id, error_text, context.bot)
            return
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp(prefix='voice_')
        
        # Download voice file
        try:
            temp_file_path, file_extension = await download_voice_file(
                message.voice, 
                context.bot, 
                temp_dir
            )
        except Exception as e:
            logger.error(f"Failed to download voice file: {e}")
            error_text = translator.translate('voice.error_download')
            await update_processing_message(update, processing_message_id, error_text, context.bot)
            return
        
        # Determine language for transcription
        # Use user's preferred language if available, otherwise auto-detect
        from bot.database.user_operations import UserOperations
        user_ops = UserOperations(db_client, user_cache)
        user_settings = await user_ops.get_user_settings(user.id)
        
        transcription_language = None
        if user_settings and user_settings.get('language'):
            # Map bot language codes to Whisper language codes
            lang_map = {'ru': 'ru', 'en': 'en', 'es': 'es'}
            transcription_language = lang_map.get(user_settings['language'])
        
        # Transcribe audio
        try:
            transcribed_text = await whisper_client.transcribe_audio(
                temp_file_path,
                language=transcription_language,
                duration_seconds=message.voice.duration
            )
            
            if not transcribed_text or not transcribed_text.strip():
                error_text = translator.translate('voice.error_empty_transcription')
                await update_processing_message(update, processing_message_id, error_text, context.bot)
                return
            
        except AudioTooLargeError:
            error_text = translator.translate(
                'voice.error_too_large',
                max_size=config.max_voice_file_size_mb
            )
            await update_processing_message(update, processing_message_id, error_text, context.bot)
            return
            
        except AudioTooLongError:
            error_text = translator.translate(
                'voice.error_too_long',
                max_duration=config.max_voice_duration_seconds
            )
            await update_processing_message(update, processing_message_id, error_text, context.bot)
            return
            
        except TranscriptionError as e:
            logger.error(f"Transcription error: {e}")
            error_text = translator.translate('voice.error_transcription')
            await update_processing_message(update, processing_message_id, error_text, context.bot)
            return
            
        except Exception as e:
            logger.error(f"Unexpected error during transcription: {e}")
            error_text = translator.translate('voice.error_api')
            await update_processing_message(update, processing_message_id, error_text, context.bot)
            return
        
        # Process transcribed text as regular message
        try:
            # Ensure user exists in database
            await user_ops.ensure_user_exists(
                tg_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            # Initialize question manager and ensure user has default question
            from bot.questions import QuestionManager
            question_manager = QuestionManager(db_client, user_cache)
            await question_manager.ensure_user_has_default_question(user.id)
            
            # Determine which question this message responds to
            reply_to_message_id = None
            if message.reply_to_message:
                reply_to_message_id = message.reply_to_message.message_id
            
            question_id, status = await question_manager.determine_question_for_message(
                user.id, reply_to_message_id
            )
            
            if question_id:
                # Log the transcribed text as activity
                success = await user_ops.log_activity(
                    user.id, 
                    transcribed_text, 
                    question_id=question_id
                )
                
                if success:
                    logger.info(
                        f"Voice message transcribed and logged: user_id={user.id}, "
                        f"question_id={question_id}, transcription_length={len(transcribed_text)}"
                    )
                    
                    # Update processing message with success
                    success_text = translator.translate('voice.success', text=transcribed_text)
                    await update_processing_message(update, processing_message_id, success_text, context.bot)
                else:
                    error_text = translator.translate('voice.error_save')
                    await update_processing_message(update, processing_message_id, error_text, context.bot)
            else:
                error_text = translator.translate('voice.error_no_question')
                await update_processing_message(update, processing_message_id, error_text, context.bot)
                
        except Exception as e:
            logger.error(f"Error processing transcribed text: {e}")
            error_text = translator.translate('voice.error_processing')
            await update_processing_message(update, processing_message_id, error_text, context.bot)
            
    except Exception as e:
        logger.error(f"Unexpected error in voice message handling: {e}")
        error_text = translator.translate('voice.error_general')
        await update_processing_message(update, processing_message_id, error_text, context.bot)
        
    finally:
        # Clean up temporary files
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.debug(f"Temporary file removed: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {temp_file_path}: {e}")
        
        if temp_dir and os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
                logger.debug(f"Temporary directory removed: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary directory {temp_dir}: {e}")


def setup_voice_handlers(
    application: Application,
    db_client: DatabaseClient,
    user_cache: TTLCache,
    rate_limiter: MultiTierRateLimiter,
    config: Config
) -> None:
    """Setup voice message handlers."""
    
    # Ensure bot_data is populated
    application.bot_data.update({
        'db_client': db_client,
        'user_cache': user_cache,
        'rate_limiter': rate_limiter,
        'config': config
    })
    
    # Register voice message handler
    voice_handler = MessageHandler(
        filters.VOICE,
        handle_voice_message
    )
    application.add_handler(voice_handler, group=1)  # Same priority as text messages
    
    logger.info("Voice message handlers registered successfully")
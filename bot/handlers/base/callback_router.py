"""
Central callback query router.

This module provides the CallbackRouter class that distributes callback queries
to specialized handlers based on the callback data pattern.
"""

from typing import List, Optional
from telegram import Update
from telegram.ext import ContextTypes

from bot.cache.ttl_cache import TTLCache
from bot.config import Config
from bot.database.client import DatabaseClient
from bot.utils.rate_limiter import rate_limit
from monitoring import get_logger, track_errors_async

from .base_handler import BaseCallbackHandler


logger = get_logger(__name__)


class CallbackRouter:
    """
    Central router for callback queries.
    
    Routes callback queries to appropriate specialized handlers based on
    callback data patterns. Maintains a registry of handlers and provides
    fallback mechanisms.
    """
    
    def __init__(self, 
                 db_client: DatabaseClient, 
                 config: Config, 
                 user_cache: TTLCache):
        """Initialize router with dependencies."""
        self.db_client = db_client
        self.config = config
        self.user_cache = user_cache
        self.handlers: List[BaseCallbackHandler] = []
        self.logger = get_logger(__name__)
    
    def register_handler(self, handler: BaseCallbackHandler) -> None:
        """
        Register a callback handler.
        
        Args:
            handler: Handler instance to register
        """
        self.handlers.append(handler)
        self.logger.debug("Registered callback handler", 
                         handler_class=handler.__class__.__name__)
    
    def find_handler(self, data: str) -> Optional[BaseCallbackHandler]:
        """
        Find appropriate handler for callback data.
        
        Args:
            data: Callback data string
            
        Returns:
            Handler instance that can process the callback, or None
        """
        for handler in self.handlers:
            if handler.can_handle(data):
                self.logger.debug("Found handler for callback", 
                                callback_data=data, 
                                handler_class=handler.__class__.__name__)
                return handler
        
        self.logger.warning("No handler found for callback", callback_data=data)
        return None
    
    @rate_limit("callback")
    @track_errors_async("route_callback_query")
    async def route_callback(self, 
                           update: Update, 
                           context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Route callback query to appropriate handler.
        
        Args:
            update: Telegram update containing callback query
            context: Bot context
        """
        query = update.callback_query
        user = update.effective_user
        
        if not query or not user:
            self.logger.warning("Invalid callback query or user")
            return
        
        # Answer the callback query to stop loading animation
        await query.answer()
        
        # Get callback data
        data = query.data
        if not data:
            self.logger.warning("Empty callback data", user_id=user.id)
            return
        
        self.logger.debug("Routing callback query", 
                         user_id=user.id, 
                         callback_data=data)
        
        # Find appropriate handler
        handler = self.find_handler(data)
        
        if handler:
            try:
                await handler.execute(query, data, context)
                self.logger.debug("Callback handled successfully", 
                                user_id=user.id, 
                                callback_data=data,
                                handler_class=handler.__class__.__name__)
                
            except Exception as e:
                self.logger.error("Handler execution failed", 
                                user_id=user.id, 
                                callback_data=data,
                                handler_class=handler.__class__.__name__,
                                error=str(e))
                raise
        else:
            # Fallback for unhandled callbacks
            await self._handle_unknown_callback(query, data)
    
    async def _handle_unknown_callback(self, 
                                     query, 
                                     data: str) -> None:
        """
        Handle unknown callback data.
        
        Args:
            query: Telegram callback query
            data: Unknown callback data
        """
        user_id = query.from_user.id if query.from_user else None
        
        self.logger.warning("Unknown callback data", 
                          user_id=user_id, 
                          callback_data=data)
        
        try:
            # Try to get user's language for error message
            from .base_handler import BaseCallbackHandler
            temp_handler = type('TempHandler', (BaseCallbackHandler,), {
                'handle_callback': lambda *args: None,
                'can_handle': lambda *args: False
            })(self.db_client, self.config, self.user_cache)
            
            if user_id:
                translator = await temp_handler.get_user_translator(user_id)
                error_text = translator.translate('errors.unknown_action')
            else:
                error_text = "❌ Unknown action. Please try again."
            
            await query.edit_message_text(
                text=error_text,
                parse_mode='HTML'
            )
            
        except Exception as e:
            self.logger.error("Failed to handle unknown callback", 
                            user_id=user_id, 
                            error=str(e))
    
    def get_handler_stats(self) -> dict:
        """
        Get statistics about registered handlers.
        
        Returns:
            Dictionary with handler statistics
        """
        return {
            'total_handlers': len(self.handlers),
            'handler_classes': [h.__class__.__name__ for h in self.handlers]
        }
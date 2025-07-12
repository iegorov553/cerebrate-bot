"""
Feedback callback handlers.

Handles user feedback submission including bug reports, feature requests, and general feedback.
"""

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.handlers.base.base_handler import BaseCallbackHandler
from bot.i18n.translator import Translator
from monitoring import get_logger


logger = get_logger(__name__)


class FeedbackCallbackHandler(BaseCallbackHandler):
    """
    Handles feedback-related callback queries.

    Responsible for:
    - Feedback menu display
    - Feedback type selection (bug report, feature request, general)
    - Feedback session initialization
    - Rate limiting checks
    """

    def can_handle(self, data: str) -> bool:
        """Check if this handler can process the callback data."""
        feedback_callbacks = {
            'menu_feedback',
            'feedback_menu'
        }

        return (data in feedback_callbacks
                or data.startswith('feedback_'))

    async def handle_callback(self, 
                            query: CallbackQuery, 
                            data: str, 
                            translator: Translator, 
                            context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle feedback callback queries."""

        if data in ["menu_feedback", "feedback_menu"]:
            await self._handle_feedback_menu(query, translator)

        elif data.startswith("feedback_"):
            await self._handle_feedback_action(query, data, translator)

        else:
            self.logger.warning("Unhandled feedback callback", callback_data=data)

    async def _handle_feedback_menu(self, 
                                  query: CallbackQuery, 
                                  translator: Translator) -> None:
        """Handle feedback menu display."""
        user = query.from_user

        # Check if feedback is enabled in configuration
        if not self.config.is_feedback_enabled():
            await self._show_feedback_disabled(query, translator)
            return

        # Create feedback menu keyboard
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                translator.translate("feedback.bug_report"), 
                callback_data="feedback_bug_report"
            )],
            [InlineKeyboardButton(
                translator.translate("feedback.feature_request"), 
                callback_data="feedback_feature_request"
            )],
            [InlineKeyboardButton(
                translator.translate("feedback.general"), 
                callback_data="feedback_general"
            )],
            [InlineKeyboardButton(
                translator.translate("menu.back"), 
                callback_data="back_main"
            )]
        ])

        await query.edit_message_text(
            f"**{translator.translate('feedback.title')}**\n\n"
            f"{translator.translate('feedback.description')}",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

        self.logger.debug("Feedback menu displayed", user_id=user.id)

    async def _handle_feedback_action(self, 
                                    query: CallbackQuery, 
                                    data: str, 
                                    translator: Translator) -> None:
        """Handle feedback action selection."""
        user = query.from_user

        # Check if feedback is enabled
        if not self.config.is_feedback_enabled():
            await self._show_feedback_disabled(query, translator)
            return

        # Handle specific feedback types
        if data in ["feedback_bug_report", "feedback_feature_request", "feedback_general"]:
            await self._start_feedback_session(query, data, translator)
        else:
            self.logger.warning("Unknown feedback action", 
                              user_id=user.id, 
                              action=data)

    async def _start_feedback_session(self, 
                                    query: CallbackQuery, 
                                    data: str, 
                                    translator: Translator) -> None:
        """Start a feedback session for the user."""
        user = query.from_user
        feedback_type = data.replace("feedback_", "")

        try:
            # Initialize feedback manager
            from bot.feedback import FeedbackManager
            from bot.utils.rate_limiter import MultiTierRateLimiter

            rate_limiter = MultiTierRateLimiter(
                feedback_rate_limit=self.config.feedback_rate_limit
            )
            feedback_manager = FeedbackManager(
                self.config, 
                rate_limiter, 
                self.user_cache
            )

            # Check rate limit
            if not await feedback_manager.check_rate_limit(user.id):
                await self._show_rate_limited(query, translator)
                return

            # Get user language for feedback session
            user_language = await self.get_user_language(user.id)

            # Start feedback session
            success = await feedback_manager.start_feedback_session(
                user.id, 
                feedback_type, 
                user_language
            )

            if success:
                await self._show_feedback_prompt(query, feedback_type, translator)

                self.logger.info("Feedback session started", 
                               user_id=user.id, 
                               feedback_type=feedback_type)
            else:
                await self._show_rate_limited(query, translator)

        except Exception as e:
            self.logger.error("Error starting feedback session", 
                            user_id=user.id, 
                            feedback_type=feedback_type,
                            error=str(e))

            # Show generic error
            await self._show_feedback_error(query, translator)

    async def _show_feedback_disabled(self, 
                                    query: CallbackQuery, 
                                    translator: Translator) -> None:
        """Show feedback disabled message."""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                translator.translate("menu.back"), 
                callback_data="back_main"
            )]
        ])

        await query.edit_message_text(
            translator.translate('feedback.disabled'),
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

        self.logger.debug("Feedback disabled message shown", 
                         user_id=query.from_user.id)

    async def _show_rate_limited(self, 
                               query: CallbackQuery, 
                               translator: Translator) -> None:
        """Show rate limited message."""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                translator.translate("menu.back"), 
                callback_data="feedback_menu"
            )]
        ])

        await query.edit_message_text(
            translator.translate('feedback.rate_limited'),
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

        self.logger.debug("Rate limited message shown", 
                         user_id=query.from_user.id)

    async def _show_feedback_prompt(self, 
                                  query: CallbackQuery, 
                                  feedback_type: str, 
                                  translator: Translator) -> None:
        """Show feedback description prompt."""
        description_key = f"feedback.{feedback_type}_description"

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                translator.translate("menu.back"), 
                callback_data="feedback_menu"
            )]
        ])

        await query.edit_message_text(
            f"{translator.translate(description_key)}\n\n"
            f"{translator.translate('feedback.enter_description')}",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

        self.logger.debug("Feedback prompt shown", 
                         user_id=query.from_user.id,
                         feedback_type=feedback_type)

    async def _show_feedback_error(self, 
                                 query: CallbackQuery, 
                                 translator: Translator) -> None:
        """Show feedback error message."""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                translator.translate("menu.back"), 
                callback_data="feedback_menu"
            )]
        ])

        await query.edit_message_text(
            translator.translate('errors.general'),
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

        self.logger.debug("Feedback error message shown", 
                         user_id=query.from_user.id)
"""
Navigation callback handlers.

Handles main menu navigation, language changes, and basic routing.
"""

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes

from bot.handlers.base.base_handler import BaseCallbackHandler
from bot.i18n.translator import Translator
from bot.keyboards.keyboard_generators import KeyboardGenerator
from monitoring import get_logger


logger = get_logger(__name__)


class NavigationCallbackHandler(BaseCallbackHandler):
    """
    Handles navigation-related callback queries.

    Responsible for:
    - Main menu display
    - Language selection and changes
    - History/webapp access
    - Basic navigation routing
    """

    def can_handle(self, data: str) -> bool:
        """Check if this handler can process the callback data."""
        navigation_callbacks = {
            'back_main',      # Standard "back to main menu" button
            'menu_language'   # Language selection menu
        }

        return (data in navigation_callbacks
                or data.startswith('language_'))

    async def handle_callback(self,
                            query: CallbackQuery,
                            data: str,
                            translator: Translator,
                            context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle navigation callback queries."""

        if data == "back_main":
            await self._handle_main_menu(query, translator)

        elif data == "menu_language":
            await self._handle_language_menu(query, translator)

        elif data.startswith("language_"):
            await self._handle_language_change(query, data, translator)

        else:
            self.logger.warning("Unhandled navigation callback", callback_data=data)

    async def _handle_main_menu(self,
                              query: CallbackQuery,
                              translator: Translator) -> None:
        """Handle main menu display."""
        user = query.from_user

        # Check if user is admin
        is_admin = (self.config.is_admin_configured()
                    and user.id == self.config.admin_user_id)

        # Generate main menu keyboard
        keyboard = KeyboardGenerator.main_menu(is_admin, translator)

        # Create welcome message
        welcome_text = f"👋 {translator.translate('welcome.greeting', name=user.first_name)}\n\n"
        welcome_text += translator.translate('welcome.description')

        await query.edit_message_text(
            welcome_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

        self.logger.debug("Main menu displayed",
                         user_id=user.id,
                         is_admin=is_admin)

    async def _handle_language_menu(self,
                                  query: CallbackQuery,
                                  translator: Translator) -> None:
        """Handle language selection menu."""
        user = query.from_user

        # Get current user language
        current_language = await self.get_user_language(user.id)

        # Generate language menu
        keyboard = KeyboardGenerator.language_menu(current_language, translator)

        help_text = f"{translator.translate('language.title')}\n\n{translator.translate('language.subtitle')}"

        await query.edit_message_text(
            help_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

        self.logger.debug("Language menu displayed",
                         user_id=user.id,
                         current_language=current_language)

    async def _handle_language_change(self,
                                    query: CallbackQuery,
                                    data: str,
                                    translator: Translator) -> None:
        """Handle language change selection."""
        user = query.from_user
        new_language = data.replace("language_", "")

        # Validate language code
        if new_language not in ['ru', 'en', 'es']:
            self.logger.warning("Invalid language selected",
                              user_id=user.id,
                              language=new_language)
            return

        try:
            # Update user language in database
            from bot.database.user_operations import UserOperations
            user_ops = UserOperations(self.db_client, self.user_cache)
            success = await user_ops.update_user_settings(
                user.id,
                {'language': new_language}
            )

            # Force cache invalidation after language change
            if self.user_cache:
                await self.user_cache.invalidate(f"user_settings_{user.id}")
                await self.user_cache.invalidate(f"user_{user.id}")

            # Create new translator with new language
            new_translator = Translator()
            new_translator.set_language(new_language)

            # Get language info for display
            lang_info = new_translator.get_language_info(new_language)

            # Check if user is admin for main menu
            is_admin = (self.config.is_admin_configured()
                        and user.id == self.config.admin_user_id)

            if success:
                # Language change successful
                success_message = new_translator.translate(
                    'language.changed',
                    language=lang_info['native'],
                    flag=lang_info['flag']
                )
            else:
                # Language column might not exist, show message anyway
                success_message = new_translator.translate(
                    'language.changed',
                    language=lang_info['native'],
                    flag=lang_info['flag']
                )

            await query.edit_message_text(
                success_message,
                reply_markup=KeyboardGenerator.main_menu(is_admin, new_translator),
                parse_mode='Markdown'
            )

            self.logger.info("User language changed",
                           user_id=user.id,
                           old_language=translator.current_language,
                           new_language=new_language,
                           success=success)

        except Exception as e:
            self.logger.error("Error changing language",
                            user_id=user.id,
                            new_language=new_language,
                            error=str(e))

            # Show error message with fallback translator
            error_translator = Translator()  # Default language
            is_admin = (self.config.is_admin_configured()
                        and user.id == self.config.admin_user_id)

            await query.edit_message_text(
                error_translator.translate('errors.general'),
                reply_markup=KeyboardGenerator.main_menu(is_admin, error_translator),
                parse_mode='Markdown'
            )

    async def _handle_history(self,
                            query: CallbackQuery,
                            translator: Translator) -> None:
        """Handle history/webapp access."""
        user = query.from_user

        # Create web app button
        web_app = WebAppInfo(url=self.config.webapp_url)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                translator.translate('menu.history'),
                web_app=web_app
            )],
            [InlineKeyboardButton(
                translator.translate('menu.back'),
                callback_data="back_main"
            )]
        ])

        await query.edit_message_text(
            f"{translator.title('menu.history')}"
            f"{translator.translate('history.webapp_description')}",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

        self.logger.debug("History menu displayed", user_id=user.id)

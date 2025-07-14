"""
Settings callback handlers.

Handles user settings management including notifications, time windows, and frequency.
"""

from telegram import CallbackQuery
from telegram.ext import ContextTypes

from bot.handlers.base.base_handler import BaseCallbackHandler
from bot.i18n.translator import Translator
from bot.keyboards.keyboard_generators import (
    KeyboardGenerator,
    create_settings_menu
)
from monitoring import get_logger


logger = get_logger(__name__)


class SettingsCallbackHandler(BaseCallbackHandler):
    """
    Handles settings-related callback queries.

    Responsible for:
    - Settings menu display
    - Notification toggle
    - Time window configuration help
    - Frequency configuration help
    - Settings navigation
    """

    def can_handle(self, data: str) -> bool:
        """Check if this handler can process the callback data."""
        settings_callbacks = {
            'menu_settings',
            'settings'
        }

        return (data in settings_callbacks
                or data.startswith('settings_'))

    async def handle_callback(self,
                            query: CallbackQuery,
                            data: str,
                            translator: Translator,
                            context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle settings callback queries."""

        if data in ["menu_settings", "settings"]:
            await self._handle_settings_menu(query, translator)

        elif data.startswith("settings_"):
            await self._handle_settings_action(query, data, translator)

        else:
            self.logger.warning("Unhandled settings callback", callback_data=data)

    async def _handle_settings_menu(self,
                                  query: CallbackQuery,
                                  translator: Translator) -> None:
        """Handle settings menu display."""
        user = query.from_user

        try:
            # Get user settings from database
            from bot.database.user_operations import UserOperations
            user_ops = UserOperations(self.db_client, self.user_cache)
            user_data = await user_ops.get_user_settings(user.id)

            if not user_data:
                # Database error
                is_admin = (self.config.is_admin_configured()
                            and user.id == self.config.admin_user_id)

                await query.edit_message_text(
                    translator.translate('errors.database'),
                    reply_markup=KeyboardGenerator.main_menu(is_admin, translator)
                )
                self.logger.error("Failed to get user settings", user_id=user.id)
                return

            # Generate settings menu keyboard
            keyboard = create_settings_menu(translator)

            # Create localized settings display
            enabled_status = (
                translator.translate('settings.notifications_enabled')
                if user_data['enabled']
                else translator.translate('settings.notifications_disabled')
            )

            settings_text = f"{translator.translate('settings.current_title')}\n\n"
            settings_text += f"{translator.translate('settings.notifications', status=enabled_status)}\n"
            settings_text += (f"{translator.translate('settings.time_window')}: "
                              f"{user_data['window_start']} - {user_data['window_end']}\n")
            settings_text += (f"{translator.translate('settings.frequency')}: "
                              f"{translator.translate('settings.every_minutes', minutes=user_data['interval_min'])}")

            await query.edit_message_text(
                settings_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

            self.logger.debug("Settings menu displayed",
                            user_id=user.id,
                            enabled=user_data['enabled'],
                            interval=user_data['interval_min'])

        except Exception as e:
            self.logger.error("Error displaying settings menu",
                            user_id=user.id,
                            error=str(e))
            raise

    async def _handle_settings_action(self,
                                    query: CallbackQuery,
                                    data: str,
                                    translator: Translator) -> None:
        """Handle settings action callbacks."""
        user = query.from_user
        action = data.replace("settings_", "")

        self.logger.debug("Processing settings action",
                         user_id=user.id,
                         action=action)

        if action == "toggle_notifications":
            await self._handle_toggle_notifications(query, translator)

        elif action == "back":
            await self._handle_back_to_main(query, translator)

        elif action == "time_window":
            await self._handle_time_window_help(query, translator)

        elif action == "frequency":
            await self._handle_frequency_help(query, translator)

        elif action == "view":
            await self._handle_settings_menu(query, translator)

        else:
            self.logger.warning("Unknown settings action",
                              user_id=user.id,
                              action=action)

    async def _handle_toggle_notifications(self,
                                         query: CallbackQuery,
                                         translator: Translator) -> None:
        """Handle notification toggle."""
        user = query.from_user

        try:
            from bot.database.user_operations import UserOperations
            user_ops = UserOperations(self.db_client, self.user_cache)

            # Get current settings
            user_settings = await user_ops.get_user_settings(user.id)
            if not user_settings:
                is_admin = (self.config.is_admin_configured()
                            and user.id == self.config.admin_user_id)

                await query.edit_message_text(
                    translator.translate('settings.error_get'),
                    reply_markup=KeyboardGenerator.main_menu(is_admin, translator)
                )
                self.logger.error("Failed to get user settings for toggle",
                                user_id=user.id)
                return

            # Toggle enabled status
            current_enabled = user_settings.get('enabled', True)
            new_enabled = not current_enabled

            success = await user_ops.update_user_settings(
                user.id,
                {'enabled': new_enabled}
            )

            if success:
                # Always return to questions menu with updated notification status
                from bot.database.question_operations import QuestionOperations
                from bot.keyboards.keyboard_generators import create_questions_menu
                
                question_ops = QuestionOperations(self.db_client, self.user_cache)
                questions_summary = await question_ops.get_user_questions_summary(user.id)
                
                # Create updated keyboard with new notification status
                keyboard = create_questions_menu(questions_summary, new_enabled, translator)
                
                # Keep the same menu text
                menu_text = f"{translator.translate('questions.title')}\n\n"
                menu_text += translator.translate('questions.description')
                
                await query.edit_message_text(
                    menu_text,
                    reply_markup=keyboard
                )

                self.logger.info("Notifications toggled",
                               user_id=user.id,
                               old_enabled=current_enabled,
                               new_enabled=new_enabled)
            else:
                # Show error message
                await query.edit_message_text(
                    translator.translate('settings.error_update'),
                    reply_markup=create_settings_menu(translator)
                )

                self.logger.error("Failed to toggle notifications",
                                user_id=user.id)

        except Exception as e:
            self.logger.error("Error toggling notifications",
                            user_id=user.id,
                            error=str(e))

            # Show generic error
            await query.edit_message_text(
                translator.translate('settings.error_update'),
                reply_markup=create_settings_menu(translator)
            )

    async def _handle_back_to_main(self,
                                 query: CallbackQuery,
                                 translator: Translator) -> None:
        """Handle back to main menu."""
        user = query.from_user

        # Check if user is admin
        is_admin = (self.config.is_admin_configured()
                    and user.id == self.config.admin_user_id)

        # Generate main menu
        keyboard = KeyboardGenerator.main_menu(is_admin, translator)

        # Create welcome message
        welcome_text = f"👋 {translator.translate('welcome.greeting', name=user.first_name)}\n\n"
        welcome_text += translator.translate('welcome.description')

        await query.edit_message_text(
            welcome_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

        self.logger.debug("Returned to main menu from settings", user_id=user.id)

    async def _handle_time_window_help(self,
                                     query: CallbackQuery,
                                     translator: Translator) -> None:
        """Handle time window configuration help."""
        await query.edit_message_text(
            translator.translate('settings.time_window_help'),
            reply_markup=create_settings_menu(translator),
            parse_mode='Markdown'
        )

        self.logger.debug("Time window help displayed", user_id=query.from_user.id)

    async def _handle_frequency_help(self,
                                   query: CallbackQuery,
                                   translator: Translator) -> None:
        """Handle frequency configuration help."""
        await query.edit_message_text(
            translator.translate('settings.frequency_help'),
            reply_markup=create_settings_menu(translator),
            parse_mode='Markdown'
        )

        self.logger.debug("Frequency help displayed", user_id=query.from_user.id)

"""
Admin callback handlers.

Handles administrative functions including admin panel, broadcast, health checks, and statistics.
"""

from telegram import CallbackQuery
from telegram.ext import ContextTypes

from bot.handlers.base.base_handler import BaseCallbackHandler
from bot.i18n.translator import Translator
from bot.keyboards.keyboard_generators import KeyboardGenerator
from monitoring import get_logger


logger = get_logger(__name__)


class AdminCallbackHandler(BaseCallbackHandler):
    """
    Handles admin-related callback queries.

    Responsible for:
    - Admin panel access and display
    - Broadcast functionality initiation
    - System health checks
    - Statistics and monitoring
    - Admin-only access control
    """

    def can_handle(self, data: str) -> bool:
        """Check if this handler can process the callback data."""
        admin_callbacks = {
            'menu_admin',
            'admin_panel'
        }

        return (data in admin_callbacks
                or data.startswith('admin_'))

    async def handle_callback(self,
                            query: CallbackQuery,
                            data: str,
                            translator: Translator,
                            context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle admin callback queries."""

        if data in ["menu_admin", "admin_panel"]:
            await self._handle_admin_panel(query, translator)

        elif data.startswith("admin_"):
            await self._handle_admin_action(query, data, translator, context)

        else:
            self.logger.warning("Unhandled admin callback", callback_data=data)

    async def _handle_admin_panel(self,
                                query: CallbackQuery,
                                translator: Translator) -> None:
        """Handle admin panel access and display."""
        user = query.from_user

        # Check admin access
        if not await self._check_admin_access(user.id, query, translator):
            return

        # Generate admin menu keyboard
        keyboard = KeyboardGenerator.admin_menu(translator)

        # Get version information
        from bot.utils.version import format_version_string, get_version_info
        version_string = format_version_string()
        version_info = get_version_info()

        # Create admin panel message
        admin_text = f"{translator.translate('admin.title')}\n\n"
        admin_text += f"{translator.translate('admin.version', version=version_string)}\n"
        admin_text += f"{translator.translate('admin.environment', env=version_info['environment'])}\n\n"
        admin_text += f"{translator.translate('admin.choose_action')}"

        await query.edit_message_text(
            admin_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

        self.logger.info("Admin panel accessed", user_id=user.id)

    async def _handle_admin_action(self,
                                 query: CallbackQuery,
                                 data: str,
                                 translator: Translator,
                                 context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle specific admin actions."""
        user = query.from_user

        # Check admin access
        if not await self._check_admin_access(user.id, query, translator):
            return

        action = data.replace("admin_", "")

        self.logger.debug("Processing admin action",
                         user_id=user.id,
                         action=action)

        if action == "broadcast":
            await self._handle_broadcast_start(query, translator)

        elif action == "stats":
            await self._handle_stats(query, translator)

        elif action == "health":
            await self._handle_health_check(query, translator, context)

        elif action == "back":
            await self._handle_back_to_main(query, translator)

        else:
            self.logger.warning("Unknown admin action",
                              user_id=user.id,
                              action=action)
            # Fallback to main menu
            await self._handle_back_to_main(query, translator)

    async def _check_admin_access(self,
                                user_id: int,
                                query: CallbackQuery,
                                translator: Translator) -> bool:
        """Check if user has admin access."""
        try:
            from bot.admin.admin_operations import AdminOperations
            admin_ops = AdminOperations(None, self.config)  # db_client not needed for is_admin check

            if not admin_ops.is_admin(user_id):
                # Access denied
                await query.edit_message_text(
                    f"🔒 **{translator.translate('admin.access_denied')}**\n\n"
                    f"{translator.translate('admin.admin_only')}",
                    reply_markup=KeyboardGenerator.main_menu(False, translator),
                    parse_mode='Markdown'
                )

                self.logger.warning("Admin access denied", user_id=user_id)
                return False

            return True

        except Exception as e:
            self.logger.error("Error checking admin access",
                            user_id=user_id,
                            error=str(e))

            # Show error and deny access
            await query.edit_message_text(
                translator.translate('errors.general'),
                reply_markup=KeyboardGenerator.main_menu(False, translator),
                parse_mode='Markdown'
            )
            return False

    async def _handle_broadcast_start(self,
                                    query: CallbackQuery,
                                    translator: Translator) -> None:
        """Handle broadcast initiation."""
        # This will be handled by ConversationHandler entry point
        # Just show a temporary message since callback will be intercepted
        await query.edit_message_text(
            translator.translate('admin.broadcast_starting'),
            parse_mode='Markdown'
        )

        self.logger.info("Broadcast session starting", user_id=query.from_user.id)

    async def _handle_stats(self,
                          query: CallbackQuery,
                          translator: Translator) -> None:
        """Handle statistics display."""
        user = query.from_user
        
        try:
            # Get admin operations from context (should be available)
            from bot.admin.admin_operations import AdminOperations
            admin_ops = AdminOperations(self.db_client, self.config)
            
            # Show loading indicator
            await query.edit_message_text(
                translator.translate('admin.loading_stats'),
                parse_mode='Markdown'
            )
            
            # Get user statistics
            stats = await admin_ops.get_user_stats_optimized()
            
            if not stats:
                await query.edit_message_text(
                    translator.translate('admin.stats_error'),
                    reply_markup=KeyboardGenerator.admin_menu(translator),
                    parse_mode='Markdown'
                )
                return
            
            # Use percentage from stats (already calculated)
            active_percentage = stats.get('active_percentage', 0)
            
            # Determine activity level
            if active_percentage > 50:
                activity_level = translator.translate('admin.activity_levels.high')
            elif active_percentage > 25:
                activity_level = translator.translate('admin.activity_levels.medium')
            else:
                activity_level = translator.translate('admin.activity_levels.low')
            
            stats_text = f"{translator.translate('admin.user_stats')}\n\n" \
                f"{translator.translate('admin.total_users', total=stats['total'])}\n" \
                f"{translator.translate('admin.active_users', active=stats['active'], percentage=active_percentage)}\n" \
                f"{translator.translate('admin.new_users_week', count=stats['new_week'])}\n\n" \
                f"{translator.translate('admin.activity_level', level=activity_level)}"
            
            await query.edit_message_text(
                stats_text,
                reply_markup=KeyboardGenerator.admin_menu(translator),
                parse_mode='Markdown'
            )
            
            self.logger.info("User statistics displayed", user_id=user.id, total_users=stats['total'])
            
        except Exception as e:
            self.logger.error("Error getting user statistics", user_id=user.id, error=str(e))
            await query.edit_message_text(
                f"{translator.translate('errors.stats_load_error')}: {str(e)[:100]}",
                reply_markup=KeyboardGenerator.admin_menu(translator),
                parse_mode='Markdown'
            )

    async def _handle_health_check(self,
                                 query: CallbackQuery,
                                 translator: Translator,
                                 context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle system health check."""
        user = query.from_user

        try:
            # Import health service and version
            from bot.services.health_service import HealthService
            from bot.utils.version import get_bot_version

            # Create health service
            version = get_bot_version()
            health_service = HealthService(self.db_client, version)

            # Show loading indicator
            await query.edit_message_text(
                translator.translate('admin.health_checking'),
                parse_mode='Markdown'
            )

            # Get application from context
            application = context.application if context else None

            # Get system health status
            health_status = await health_service.get_system_health(application)

            # Format health check message
            message = await self._format_health_message(health_status, translator)

            # Create return keyboard
            keyboard = KeyboardGenerator.admin_menu(translator)

            # Use plain text for better readability
            await query.edit_message_text(
                message,
                reply_markup=keyboard
            )

            self.logger.info("Health check completed",
                           user_id=user.id,
                           system_status=health_status.status)

        except Exception as e:
            self.logger.error("Error in health check",
                            user_id=user.id,
                            error=str(e))

            # Show error message
            await query.edit_message_text(
                translator.translate('admin.health_error', error=str(e)[:100]),
                reply_markup=KeyboardGenerator.admin_menu(translator)
            )

    async def _format_health_message(self,
                                   health_status,
                                   translator: Translator) -> str:
        """Format health check message for display."""
        # Status emojis
        status_emoji = {
            "healthy": "✅",
            "degraded": "⚠️",
            "unhealthy": "❌"
        }

        # Main health information with better formatting
        message = f"🏥 {translator.translate('admin.health_check_title')}\n"
        message += "═" * 35 + "\n\n"
        
        # Overall status with clear formatting
        status_icon = status_emoji.get(health_status.status, '❓')
        message += f"{status_icon} СТАТУС: {health_status.status.upper()}\n\n"

        # Basic info section
        timestamp_safe = health_status.timestamp.split('T')[0] + ' ' + health_status.timestamp.split('T')[1][:8]
        message += f"📅 Время: {timestamp_safe}\n"
        message += f"🔖 Версия: {health_status.version}\n"
        message += f"⏱ Время работы: {health_status.uptime_seconds:.1f} сек\n\n"

        # Components section with clear separation
        message += "🔧 КОМПОНЕНТЫ:\n"
        message += "─" * 20 + "\n"
        
        for name, component in health_status.components.items():
            emoji = status_emoji.get(component.status, '❓')
            component_name = translator.translate(f'admin.component_{name}', default=f'{name.title()}')
            
            # Component header with status
            message += f"\n{emoji} {component_name}:"
            
            if component.latency_ms:
                message += f" ({component.latency_ms:.0f}ms)"
            
            message += f"\n   └ Статус: {component.status.upper()}\n"

            # Show error if exists
            if component.error:
                message += f"   └ ❌ Ошибка: {component.error}\n"

            # Show important details
            if component.details:
                important_details = {k: v for k, v in component.details.items()
                                   if k in ['connection', 'query_success', 'api_accessible', 'scheduler_running']}
                if important_details:
                    message += "   └ Детали: "
                    details_list = []
                    for k, v in important_details.items():
                        details_list.append(f"{k}={v}")
                    message += ", ".join(details_list) + "\n"

        # System metrics if available
        if hasattr(health_status, 'metrics') and health_status.metrics:
            message += "\n📊 СИСТЕМНЫЕ МЕТРИКИ:\n"
            message += "─" * 20 + "\n"
            for metric, value in health_status.metrics.items():
                message += f"• {metric}: {value}\n"

        return message

    async def _handle_back_to_main(self,
                                 query: CallbackQuery,
                                 translator: Translator) -> None:
        """Handle back to main menu."""
        user = query.from_user

        # Check if user is admin (they should be since they got here)
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

        self.logger.debug("Returned to main menu from admin", user_id=user.id)

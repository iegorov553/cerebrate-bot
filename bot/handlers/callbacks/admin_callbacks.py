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

        elif action == "friend_activities":
            await self._handle_friend_activities(query, translator, context)

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
                "📊 Загружаю статистику...",
                parse_mode='Markdown'
            )
            
            # Get user statistics
            stats = await admin_ops.get_user_stats_optimized()
            
            if not stats:
                await query.edit_message_text(
                    "❌ Не удалось получить статистику пользователей.",
                    reply_markup=KeyboardGenerator.admin_menu(translator),
                    parse_mode='Markdown'
                )
                return
            
            # Use percentage from stats (already calculated)
            active_percentage = stats.get('active_percentage', 0)
            
            stats_text = f"📊 **Статистика пользователей**\n\n" \
                f"👥 Всего пользователей: {stats['total']}\n" \
                f"✅ Активных: {stats['active']} ({active_percentage:.1f}%)\n" \
                f"🆕 Новых за неделю: {stats['new_week']}\n\n" \
                f"📈 Активность: {'Высокая' if active_percentage > 50 else 'Средняя' if active_percentage > 25 else 'Низкая'}"
            
            await query.edit_message_text(
                stats_text,
                reply_markup=KeyboardGenerator.admin_menu(translator),
                parse_mode='Markdown'
            )
            
            self.logger.info("User statistics displayed", user_id=user.id, total_users=stats['total'])
            
        except Exception as e:
            self.logger.error("Error getting user statistics", user_id=user.id, error=str(e))
            await query.edit_message_text(
                f"❌ Ошибка при загрузке статистики: {str(e)[:100]}",
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

            await query.edit_message_text(
                message,
                reply_markup=keyboard,
                parse_mode='Markdown'
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
                reply_markup=KeyboardGenerator.admin_menu(translator),
                parse_mode='Markdown'
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

        # Function for safe markdown escaping
        def escape_markdown(text):
            """Escape special characters for Markdown."""
            if not text:
                return ""
            special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
            escaped_text = str(text)
            for char in special_chars:
                escaped_text = escaped_text.replace(char, f'\\{char}')
            return escaped_text

        # Main health information
        message = f"{translator.translate('admin.health_check_title')}\n\n"
        message += f"{status_emoji.get(health_status.status, '❓')} {translator.translate('admin.health_status', status=health_status.status.upper())}\n"

        # Safe timestamp without escaping (date/time only)
        timestamp_safe = health_status.timestamp.split('T')[0] + ' ' + health_status.timestamp.split('T')[1][:8]
        message += f"{translator.translate('admin.health_timestamp', timestamp=timestamp_safe)}\n"
        message += f"{translator.translate('admin.health_version', version=health_status.version)}\n"
        message += f"{translator.translate('admin.health_uptime', uptime=f'{health_status.uptime_seconds:.1f}')}\n\n"

        # System components
        message += f"{translator.translate('admin.health_components')}\n"
        for name, component in health_status.components.items():
            emoji = status_emoji.get(component.status, '❓')
            component_name = translator.translate(f'admin.component_{name}', default=f'🔧 {name.title()}')

            message += f"{emoji} **{component_name}:** {component.status.upper()}"

            if component.latency_ms:
                message += f" ({component.latency_ms:.0f}ms)"

            message += "\n"

            if component.error:
                # Safely escape error message
                safe_error = escape_markdown(component.error)
                message += f"   {translator.translate('admin.error', error=safe_error)}\n"

            if component.details:
                # Show only important details with escaping
                important_details = {k: v for k, v in component.details.items()
                                   if k in ['connection', 'query_success', 'api_accessible', 'scheduler_running']}
                if important_details:
                    safe_details = []
                    for k, v in important_details.items():
                        safe_value = escape_markdown(str(v))
                        safe_details.append(f"{k}: {safe_value}")
                    if safe_details:
                        message += f"   {translator.translate('admin.details', details=', '.join(safe_details))}\n"

        # System metrics if available
        if hasattr(health_status, 'metrics') and health_status.metrics:
            message += f"\n{translator.translate('admin.system_metrics')}\n"
            for metric, value in health_status.metrics.items():
                safe_metric = escape_markdown(str(metric))
                safe_value = escape_markdown(str(value))
                message += f"• {safe_metric}: `{safe_value}`\n"

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

    async def _handle_friend_activities(self,
                                      query: CallbackQuery,
                                      translator: Translator,
                                      context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle friend activities display."""
        user = query.from_user
        
        try:
            # Show loading indicator
            await query.edit_message_text(
                "👥 Загружаю активность друзей...",
                parse_mode='Markdown'
            )
            
            # Get last 20 friend activities
            activities = await self._get_friend_activities(user.id)
            
            if not activities:
                await query.edit_message_text(
                    "👥 **Активность друзей**\n\n"
                    "📭 Активности друзей не найдено.\n"
                    "Возможно, у вас ещё нет друзей или они не проявляли активность.",
                    reply_markup=KeyboardGenerator.admin_menu(translator),
                    parse_mode='Markdown'
                )
                return
            
            # Format activities
            activities_text = "👥 **Последние активности друзей**\n\n"
            
            for i, activity in enumerate(activities[:20], 1):
                username = activity.get('username', 'Неизвестно')
                name = activity.get('name', '')
                activity_text = activity.get('activity', '')
                timestamp = activity.get('timestamp', '')
                
                # Format display name
                display_name = f"@{username}" if username != 'Неизвестно' else name
                if not display_name:
                    display_name = "Аноним"
                
                # Format timestamp (just time)
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime('%H:%M')
                except Exception:
                    time_str = "неизв."
                
                # Truncate long activities
                if len(activity_text) > 50:
                    activity_text = activity_text[:47] + "..."
                
                activities_text += f"`{time_str}` **{display_name}:** {activity_text}\n"
            
            # Add footer
            activities_text += f"\n_Показаны последние {len(activities)} активностей_"
            
            await query.edit_message_text(
                activities_text,
                reply_markup=KeyboardGenerator.admin_menu(translator),
                parse_mode='Markdown'
            )
            
            self.logger.info("Friend activities displayed", 
                           user_id=user.id, 
                           activities_count=len(activities))
                           
        except Exception as e:
            self.logger.error("Error getting friend activities",
                            user_id=user.id,
                            error=str(e))
            
            await query.edit_message_text(
                f"❌ Ошибка при загрузке активности друзей: {str(e)[:100]}",
                reply_markup=KeyboardGenerator.admin_menu(translator),
                parse_mode='Markdown'
            )

    async def _get_friend_activities(self, user_id: int) -> list:
        """Get last 20 activities of user's friends."""
        try:
            # Get user's friends first
            from bot.database.friend_operations import FriendOperations
            friend_ops = FriendOperations(self.db_client)
            friends = await friend_ops.get_friends_list_optimized(user_id)
            
            if not friends:
                return []
            
            # Get friend IDs
            friend_ids = [friend['tg_id'] for friend in friends]
            
            # Query last 20 activities from friends
            # SQL query to get activities with user info
            query = """
                SELECT 
                    tj.job_text,
                    tj.jobs_timestamp,
                    u.tg_username,
                    u.tg_first_name
                FROM tg_jobs tj
                JOIN users u ON tj.tg_id = u.tg_id
                WHERE tj.tg_id = ANY(%s)
                ORDER BY tj.jobs_timestamp DESC
                LIMIT 20
            """
            
            # Execute query directly (Supabase allows raw SQL)
            result = self.db_client.rpc('exec_sql', {
                'query': query,
                'params': [friend_ids]
            }).execute()
            
            if not result.data:
                # Fallback: try with table queries
                activities = []
                for friend_id in friend_ids[:5]:  # Limit to avoid too many queries
                    friend_activities = self.db_client.table('tg_jobs')\
                        .select('job_text, jobs_timestamp')\
                        .eq('tg_id', friend_id)\
                        .order('jobs_timestamp', desc=True)\
                        .limit(4)\
                        .execute()
                    
                    if friend_activities.data:
                        friend_info = next((f for f in friends if f['tg_id'] == friend_id), {})
                        for activity in friend_activities.data:
                            activities.append({
                                'activity': activity['job_text'],
                                'timestamp': activity['jobs_timestamp'],
                                'username': friend_info.get('tg_username', 'Неизвестно'),
                                'name': friend_info.get('tg_first_name', '')
                            })
                
                # Sort by timestamp
                activities.sort(key=lambda x: x['timestamp'], reverse=True)
                return activities[:20]
            
            # Process SQL results
            activities = []
            for row in result.data:
                activities.append({
                    'activity': row['job_text'],
                    'timestamp': row['jobs_timestamp'],
                    'username': row['tg_username'],
                    'name': row['tg_first_name']
                })
            
            return activities
            
        except Exception as e:
            self.logger.error("Error querying friend activities", error=str(e))
            return []

"""
Friends callback handlers.

Handles social features including friend management, discovery, and requests.
"""

from telegram import CallbackQuery
from telegram.ext import ContextTypes

from bot.handlers.base.base_handler import BaseCallbackHandler
from bot.i18n.translator import Translator
from bot.keyboards.keyboard_generators import (
    KeyboardGenerator,
    create_friends_menu
)
from monitoring import get_logger


logger = get_logger(__name__)


class FriendsCallbackHandler(BaseCallbackHandler):
    """
    Handles friends-related callback queries.

    Responsible for:
    - Friends menu display
    - Friends list management
    - Friend discovery ("friends of friends")
    - Friend requests handling
    - Add friend callbacks
    """

    def can_handle(self, data: str) -> bool:
        """Check if this handler can process the callback data."""
        friends_callbacks = {
            'menu_friends',
            'friends'
        }

        return (data in friends_callbacks
                or data.startswith('friends_')
                or data.startswith('add_friend:')
                or data.startswith('friend_accept:')
                or data.startswith('friend_decline:'))

    async def handle_callback(self,
                            query: CallbackQuery,
                            data: str,
                            translator: Translator,
                            context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle friends callback queries."""

        if data in ["menu_friends", "friends"]:
            await self._handle_friends_menu(query, translator)

        elif data.startswith("friends_"):
            await self._handle_friends_action(query, data, translator, context)

        elif data.startswith("add_friend:"):
            await self._handle_add_friend_callback(query, data, translator, context)

        elif data.startswith("friend_accept:"):
            await self._handle_friend_accept(query, data, translator, context)

        elif data.startswith("friend_decline:"):
            await self._handle_friend_decline(query, data, translator, context)

        else:
            self.logger.warning("Unhandled friends callback", callback_data=data)

    async def _handle_friends_menu(self,
                                 query: CallbackQuery,
                                 translator: Translator) -> None:
        """Handle friends menu display."""
        user = query.from_user

        # Create basic friends menu
        keyboard = create_friends_menu(0, 0, translator)

        await query.edit_message_text(
            f"**{translator.translate('menu.friends')}**\n\n"
            f"{translator.translate('friends.description')}",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

        self.logger.debug("Friends menu displayed", user_id=user.id)

    async def _handle_friends_action(self,
                                   query: CallbackQuery,
                                   data: str,
                                   translator: Translator,
                                   context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle friends action callbacks."""
        user = query.from_user
        action = data.replace("friends_", "")

        self.logger.debug("Processing friends action",
                         user_id=user.id,
                         action=action)

        if action == "add":
            await self._handle_add_instruction(query, translator)

        elif action == "list":
            await self._handle_friends_list(query, translator)

        elif action == "requests":
            await self._handle_requests_help(query, translator)

        elif action == "discover":
            await self._handle_friends_discovery(query, translator)

        elif action == "back":
            await self._handle_back_to_main(query, translator)

        else:
            self.logger.warning("Unknown friends action",
                              user_id=user.id,
                              action=action)

    async def _handle_add_instruction(self,
                                    query: CallbackQuery,
                                    translator: Translator) -> None:
        """Show add friend instruction."""
        await query.edit_message_text(
            translator.translate('friends.add_instruction'),
            reply_markup=create_friends_menu(0, 0, translator),
            parse_mode='Markdown'
        )

        self.logger.debug("Add friend instruction shown",
                         user_id=query.from_user.id)

    async def _handle_friends_list(self,
                                 query: CallbackQuery,
                                 translator: Translator) -> None:
        """Handle friends list display."""
        user = query.from_user

        try:
            # Get friends list from database
            from bot.database.friend_operations import FriendOperations
            friend_ops = FriendOperations(self.db_client)

            friends = await friend_ops.get_friends_list_optimized(user.id)

            if not friends:
                # No friends found
                await query.edit_message_text(
                    translator.translate('friends.list_empty'),
                    reply_markup=create_friends_menu(0, 0, translator),
                    parse_mode='Markdown'
                )

                self.logger.debug("Empty friends list shown", user_id=user.id)

            else:
                # Show friends list (max 10)
                friends_text = f"{translator.translate('friends.list_title')}\n\n"

                for friend in friends[:10]:
                    username = friend.get('tg_username', '')
                    name = friend.get('tg_first_name', 'Без имени')

                    # Escape markdown special characters
                    def escape_markdown(text):
                        if not text:
                            return ""
                        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
                        escaped_text = str(text)
                        for char in special_chars:
                            escaped_text = escaped_text.replace(char, f'\\{char}')
                        return escaped_text

                    safe_username = escape_markdown(username)
                    safe_name = escape_markdown(name)

                    if username:
                        friends_text += f"• @{safe_username} - {safe_name}\n"
                    else:
                        friends_text += f"• {safe_name}\n"

                # Show count if more than 10
                if len(friends) > 10:
                    friends_text += f"\n{translator.translate('friends.list_more', count=len(friends) - 10)}"

                await query.edit_message_text(
                    friends_text,
                    reply_markup=create_friends_menu(0, 0, translator),
                    parse_mode='Markdown'
                )

                self.logger.debug("Friends list shown",
                                user_id=user.id,
                                friends_count=len(friends))

        except Exception as e:
            self.logger.error("Error getting friends list",
                            user_id=user.id,
                            error=str(e))

            # Show error and fallback to menu
            await query.edit_message_text(
                "❌ Произошла ошибка при загрузке списка друзей. Попробуйте позже.",
                reply_markup=create_friends_menu(0, 0, translator),
                parse_mode='Markdown'
            )

    async def _handle_requests_help(self,
                                  query: CallbackQuery,
                                  translator: Translator) -> None:
        """Show friend requests list with inline buttons."""
        user = query.from_user
        
        try:
            # Get friend requests from database
            from bot.database.friend_operations import FriendOperations
            friend_ops = FriendOperations(self.db_client)
            
            # Show loading indicator
            await query.edit_message_text(
                "📥 Загружаю запросы в друзья...",
                parse_mode='Markdown'
            )
            
            # Get friend requests
            requests_data = await friend_ops.get_friend_requests_optimized(user.id)
            
            incoming = requests_data.get('incoming', [])
            outgoing = requests_data.get('outgoing', [])
            
            text = "📥 **Запросы в друзья**\n\n"
            
            # Create keyboard with request actions
            keyboard = []
            
            if incoming:
                text += "**Входящие запросы:**\n"
                for i, req in enumerate(incoming[:5]):  # Показываем только первые 5
                    requester = req.get('requester', {})
                    username = requester.get('tg_username', 'Неизвестно')
                    name = requester.get('tg_first_name', '')
                    requester_id = req.get('requester_id')
                    
                    # Escape markdown special characters
                    def escape_markdown(text):
                        if not text:
                            return ""
                        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
                        escaped_text = str(text)
                        for char in special_chars:
                            escaped_text = escaped_text.replace(char, f'\\{char}')
                        return escaped_text
                    
                    safe_username = escape_markdown(username)
                    safe_name = escape_markdown(name)
                    
                    display_name = f"@{safe_username}" if username != 'Неизвестно' else safe_name
                    text += f"• {display_name}\n"
                    
                    # Add accept/decline buttons for each request
                    if requester_id:
                        from telegram import InlineKeyboardButton
                        # Use simple names for buttons (no markdown escaping needed in button text)
                        button_name = f"@{username}" if username != 'Неизвестно' else name
                        keyboard.append([
                            InlineKeyboardButton(
                                f"✅ Принять {button_name}",
                                callback_data=f"friend_accept:{requester_id}"
                            ),
                            InlineKeyboardButton(
                                f"❌ Отклонить {button_name}",
                                callback_data=f"friend_decline:{requester_id}"
                            )
                        ])
                        
                text += "\n"
            else:
                text += "**Входящие запросы:** нет\n\n"
            
            if outgoing:
                text += "**Исходящие запросы:**\n"
                for req in outgoing[:5]:  # Показываем только первые 5
                    addressee = req.get('addressee', {})
                    username = addressee.get('tg_username', 'Неизвестно')
                    name = addressee.get('tg_first_name', '')
                    
                    # Escape markdown special characters
                    def escape_markdown(text):
                        if not text:
                            return ""
                        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
                        escaped_text = str(text)
                        for char in special_chars:
                            escaped_text = escaped_text.replace(char, f'\\{char}')
                        return escaped_text
                    
                    safe_username = escape_markdown(username)
                    safe_name = escape_markdown(name)
                    
                    display_name = f"@{safe_username}" if username != 'Неизвестно' else safe_name
                    text += f"• {display_name} - ожидает ответа\n"
            else:
                text += "**Исходящие запросы:** нет"
            
            # Add back button
            from telegram import InlineKeyboardButton
            keyboard.append([InlineKeyboardButton(
                "🔙 Назад к друзьям",
                callback_data="menu_friends"
            )])
            
            from telegram import InlineKeyboardMarkup
            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else create_friends_menu(0, 0, translator)
            
            await query.edit_message_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            self.logger.debug("Friend requests shown",
                             user_id=user.id,
                             incoming_count=len(incoming),
                             outgoing_count=len(outgoing))
                             
        except Exception as e:
            self.logger.error("Error getting friend requests",
                            user_id=user.id,
                            error=str(e))
            
            # Show error and fallback to menu
            await query.edit_message_text(
                "❌ Произошла ошибка при загрузке запросов в друзья. Попробуйте позже.",
                reply_markup=create_friends_menu(0, 0, translator),
                parse_mode='Markdown'
            )

    async def _handle_friends_discovery(self,
                                      query: CallbackQuery,
                                      translator: Translator) -> None:
        """Handle friends discovery (friends of friends)."""
        user = query.from_user

        try:
            # Get friend recommendations using optimized algorithm
            from bot.database.friend_operations import FriendOperations
            friend_ops = FriendOperations(self.db_client)

            raw_recommendations = await friend_ops.get_friends_of_friends_optimized(
                user.id,
                limit=10
            )

            if not raw_recommendations:
                # No recommendations found
                await query.edit_message_text(
                    f"**{translator.translate('friends.discover_title')}**\n\n"
                    f"{translator.translate('friends.no_recommendations')}",
                    reply_markup=create_friends_menu(0, 0, translator),
                    parse_mode='Markdown'
                )

                self.logger.debug("No friend recommendations found", user_id=user.id)
                return

            # Transform data for KeyboardGenerator
            recommendations = []
            for rec in raw_recommendations:
                user_info = rec.get('user_info', {})
                recommendations.append({
                    'tg_id': user_info.get('tg_id'),
                    'first_name': user_info.get('tg_first_name', 'Без имени'),
                    'username': user_info.get('tg_username', 'неизвестен'),
                    'mutual_friends_count': rec.get('mutual_count', 0),
                    'mutual_friends': rec.get('mutual_friends', [])
                })

            # Generate keyboard with recommendations
            keyboard = KeyboardGenerator.friend_discovery_list(recommendations, translator)

            # Create text with recommendations
            text = f"<b>{translator.translate('friends.discover_title')}</b>\n\n"
            text += translator.translate('friends.recommendations_found', count=len(recommendations)) + "\n\n"

            # Show first 3 recommendations in text
            for i, rec in enumerate(recommendations[:3]):
                username = rec.get('username', 'неизвестен')
                first_name = rec.get('first_name', 'Без имени')
                mutual_count = rec.get('mutual_friends_count', 0)
                mutual_friends = rec.get('mutual_friends', [])

                text += f"• <b>{first_name}</b> (@{username})\n"
                text += f"  💫 {translator.translate('friends.mutual_friends', count=mutual_count)}"

                # Show names of first 2-3 mutual friends
                if mutual_friends:
                    friend_names = []
                    for friend in mutual_friends[:3]:
                        if friend.startswith('@'):
                            friend_names.append(friend)
                        else:
                            friend_names.append(f"@{friend}")

                    if friend_names:
                        text += f" {translator.translate('friends.via_friends', friends=', '.join(friend_names))}"

                text += "\n\n"

            # Show count if more than 3
            if len(recommendations) > 3:
                text += f"<i>{translator.translate('friends.more_in_buttons', count=len(recommendations) - 3)}</i>"

            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )

            self.logger.info("Friend discovery shown",
                           user_id=user.id,
                           recommendations_count=len(recommendations))

        except Exception as e:
            self.logger.error("Error in friends discovery",
                            user_id=user.id,
                            error=str(e))

            # Show error and fallback to menu
            await query.edit_message_text(
                "❌ Произошла ошибка. Попробуйте позже.",
                reply_markup=create_friends_menu(0, 0, translator),
                parse_mode='Markdown'
            )

    async def _handle_add_friend_callback(self,
                                        query: CallbackQuery,
                                        data: str,
                                        translator: Translator,
                                        context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle add friend button callbacks from discovery recommendations."""
        user = query.from_user

        try:
            # Extract target user ID from callback data
            target_user_id = int(data.split(":")[1])

            # Check rate limiting for friend requests
            rate_limiter = context.bot_data.get('rate_limiter')
            if rate_limiter:
                friend_rate_limiter = rate_limiter.rate_limiters.get("friend_request")
                if friend_rate_limiter:
                    is_allowed, retry_after = await friend_rate_limiter.is_allowed(str(user.id))
                    if not is_allowed:
                        await query.answer(
                            translator.translate('friends.rate_limited'),
                            show_alert=True
                        )
                        self.logger.warning("Friend request rate limited",
                                          user_id=user.id,
                                          target_user_id=target_user_id)
                        return

            # Send friend request
            from bot.database.friend_operations import FriendOperations
            friend_ops = FriendOperations(self.db_client)

            success, message = await friend_ops.send_friend_request_by_id(
                user.id,
                target_user_id
            )

            if success:
                # Successfully sent request
                await query.answer(
                    translator.translate('friends.request_sent'),
                    show_alert=False
                )

                # Update recommendations list (excluding the added user)
                await self._refresh_discovery_list(query, translator, friend_ops, user.id)

                self.logger.info("Friend request sent",
                               user_id=user.id,
                               target_user_id=target_user_id)

            else:
                # Failed to send request
                await query.answer(
                    message or translator.translate('friends.request_failed'),
                    show_alert=True
                )

                self.logger.warning("Friend request failed",
                                  user_id=user.id,
                                  target_user_id=target_user_id,
                                  message=message)

        except (ValueError, IndexError) as e:
            self.logger.error("Invalid add friend callback data",
                            user_id=user.id,
                            callback_data=data,
                            error=str(e))

            await query.answer(
                "❌ Произошла ошибка. Попробуйте позже.",
                show_alert=True
            )

        except Exception as e:
            self.logger.error("Error in add friend callback",
                            user_id=user.id,
                            error=str(e))

            await query.answer(
                "❌ Произошла ошибка. Попробуйте позже.",
                show_alert=True
            )

    async def _refresh_discovery_list(self,
                                    query: CallbackQuery,
                                    translator: Translator,
                                    friend_ops,
                                    user_id: int) -> None:
        """Refresh the friend discovery list after adding a friend."""
        try:
            # Get updated recommendations
            raw_recommendations = await friend_ops.get_friends_of_friends_optimized(
                user_id,
                limit=10
            )

            if raw_recommendations:
                # Transform data for KeyboardGenerator
                recommendations = []
                for rec in raw_recommendations:
                    user_info = rec.get('user_info', {})
                    recommendations.append({
                        'tg_id': user_info.get('tg_id'),
                        'first_name': user_info.get('tg_first_name', 'Без имени'),
                        'username': user_info.get('tg_username', 'неизвестен'),
                        'mutual_friends_count': rec.get('mutual_count', 0),
                        'mutual_friends': rec.get('mutual_friends', [])
                    })

                keyboard = KeyboardGenerator.friend_discovery_list(recommendations, translator)
                text = f"<b>{translator.translate('friends.discover_title')}</b>\n\n"
                text += translator.translate('friends.recommendations_found', count=len(recommendations)) + "\n\n"

                # Show updated recommendations
                for i, rec in enumerate(recommendations[:3]):
                    username = rec.get('username', 'неизвестен')
                    first_name = rec.get('first_name', 'Без имени')
                    mutual_count = rec.get('mutual_friends_count', 0)
                    mutual_friends = rec.get('mutual_friends', [])

                    text += f"• <b>{first_name}</b> (@{username})\n"
                    text += f"  💫 {translator.translate('friends.mutual_friends', count=mutual_count)}"

                    # Show names of first 2-3 mutual friends
                    if mutual_friends:
                        friend_names = []
                        for friend in mutual_friends[:3]:
                            if friend.startswith('@'):
                                friend_names.append(friend)
                            else:
                                friend_names.append(f"@{friend}")
                        if friend_names:
                            text += f" {translator.translate('friends.via_friends', friends=', '.join(friend_names))}"

                    text += "\n\n"

                if len(recommendations) > 3:
                    text += f"<i>{translator.translate('friends.more_in_buttons', count=len(recommendations) - 3)}</i>"

            else:
                # No more recommendations
                text = f"<b>{translator.translate('friends.discover_title')}</b>\n\n"
                text += translator.translate('friends.no_more_recommendations') + "\n\n"
                text += translator.translate('friends.all_requests_sent')
                keyboard = create_friends_menu(0, 0, translator)

            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )

        except Exception as e:
            self.logger.error("Error refreshing discovery list",
                            user_id=user_id,
                            error=str(e))

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

        self.logger.debug("Returned to main menu from friends", user_id=user.id)

    async def _handle_friend_accept(self,
                                  query: CallbackQuery,
                                  data: str,
                                  translator: Translator,
                                  context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle accepting a friend request."""
        user = query.from_user
        
        try:
            # Extract requester ID from callback data
            requester_id = int(data.split(':')[1])
            
            # Show processing indicator
            await query.edit_message_text(
                "✅ Принимаю запрос в друзья...",
                parse_mode='Markdown'
            )
            
            # Accept friend request
            from bot.database.friend_operations import FriendOperations
            friend_ops = FriendOperations(self.db_client)
            
            success = await friend_ops.accept_friend_request(requester_id, user.id)
            
            if success:
                # Refresh friend requests list
                await self._handle_requests_help(query, translator)
                
                self.logger.info("Friend request accepted",
                               user_id=user.id,
                               requester_id=requester_id)
            else:
                await query.edit_message_text(
                    "❌ Не удалось принять запрос в друзья. Возможно, он уже был обработан.",
                    reply_markup=create_friends_menu(0, 0, translator),
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            self.logger.error("Error accepting friend request",
                            user_id=user.id,
                            requester_id=data.split(':')[1] if ':' in data else 'unknown',
                            error=str(e))
            
            await query.edit_message_text(
                "❌ Произошла ошибка при принятии запроса. Попробуйте позже.",
                reply_markup=create_friends_menu(0, 0, translator),
                parse_mode='Markdown'
            )

    async def _handle_friend_decline(self,
                                   query: CallbackQuery,
                                   data: str,
                                   translator: Translator,
                                   context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle declining a friend request."""
        user = query.from_user
        
        try:
            # Extract requester ID from callback data
            requester_id = int(data.split(':')[1])
            
            # Show processing indicator
            await query.edit_message_text(
                "❌ Отклоняю запрос в друзья...",
                parse_mode='Markdown'
            )
            
            # Decline friend request
            from bot.database.friend_operations import FriendOperations
            friend_ops = FriendOperations(self.db_client)
            
            success = await friend_ops.decline_friend_request(requester_id, user.id)
            
            if success:
                # Refresh friend requests list
                await self._handle_requests_help(query, translator)
                
                self.logger.info("Friend request declined",
                               user_id=user.id,
                               requester_id=requester_id)
            else:
                await query.edit_message_text(
                    "❌ Не удалось отклонить запрос в друзья. Возможно, он уже был обработан.",
                    reply_markup=create_friends_menu(0, 0, translator),
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            self.logger.error("Error declining friend request",
                            user_id=user.id,
                            requester_id=data.split(':')[1] if ':' in data else 'unknown',
                            error=str(e))
            
            await query.edit_message_text(
                "❌ Произошла ошибка при отклонении запроса. Попробуйте позже.",
                reply_markup=create_friends_menu(0, 0, translator),
                parse_mode='Markdown'
            )

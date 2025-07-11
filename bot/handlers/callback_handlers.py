"""
Callback query handlers for inline keyboards.

This module handles all callback queries from inline keyboard buttons.
"""

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from bot.cache.ttl_cache import TTLCache
from bot.config import Config
from bot.database.client import DatabaseClient
from bot.i18n import get_translator
from bot.keyboards.keyboard_generators import (
    KeyboardGenerator,
    create_friends_menu,
    create_language_menu,
    create_main_menu,
    create_settings_menu,
)
from bot.utils.rate_limiter import MultiTierRateLimiter, rate_limit
from monitoring import get_logger, set_user_context, track_errors_async

logger = get_logger(__name__)


async def get_user_language(user_id: int, db_client: DatabaseClient, user_cache: TTLCache, force_refresh: bool = False) -> str:
    """Get user language from database with fallback."""
    try:
        from bot.database.user_operations import UserOperations
        user_ops = UserOperations(db_client, user_cache)
        user_data = await user_ops.get_user_settings(user_id, force_refresh=force_refresh)
        
        if user_data and 'language' in user_data:
            return user_data['language']
    except Exception as e:
        logger.warning(f"Failed to get user language: {e}")
    
    return 'ru'  # Default fallback


async def get_user_translator(user_id: int, db_client: DatabaseClient, user_cache: TTLCache, force_refresh: bool = False):
    """Get translator configured for user's language."""
    user_language = await get_user_language(user_id, db_client, user_cache, force_refresh=force_refresh)
    # Create a copy to avoid modifying global translator
    from bot.i18n.translator import Translator
    user_translator = Translator()
    user_translator.set_language(user_language)
    return user_translator


@rate_limit("callback")
@track_errors_async("handle_callback_query")
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from inline keyboards."""
    query = update.callback_query
    user = update.effective_user
    
    if not query or not user:
        return
        
    await query.answer()  # Answer the callback query
    set_user_context(user.id, user.username, user.first_name)
    
    # Get dependencies
    config: Config = context.bot_data['config']
    db_client: DatabaseClient = context.bot_data['db_client']
    user_cache: TTLCache = context.bot_data['user_cache']
    
    # Get callback data first
    data = query.data
    
    # Setup translator with user's language
    # For language change callbacks, force refresh cache
    force_refresh = data.startswith("language_") or data == "menu_language"
    user_language = await get_user_language(user.id, db_client, user_cache, force_refresh=force_refresh)
    from bot.i18n.translator import Translator
    translator = Translator()
    translator.set_language(user_language)
    
    try:
        if data == "main_menu":
            await handle_main_menu(query, config, user, None, db_client, user_cache)
        elif data == "menu_questions" or data == "questions":
            await handle_questions_menu(query, db_client, user_cache, user)
        elif data == "menu_friends" or data == "friends":
            await handle_friends_menu(query, db_client, user_cache, user)
        elif data == "menu_history" or data == "history":
            await handle_history(query, config, db_client, user_cache, user)
        elif data == "menu_admin" or data == "admin_panel":
            await handle_admin_panel(query, config, user, db_client, user_cache)
        elif data == "menu_language":
            await handle_language_menu(query, user_language, translator)
        elif data.startswith("language_"):
            await handle_language_change(query, data, db_client, user_cache, user, config)
        elif data.startswith("settings_"):
            await handle_settings_action(query, data, db_client, user_cache, user, config, translator)
        elif data.startswith("friends_"):
            await handle_friends_action(query, data, db_client, user, config, translator, user_cache)
        elif data.startswith("admin_"):
            await handle_admin_action(query, data, db_client, user, config, translator, user_cache)
        elif data.startswith("feedback_") or data == "feedback_menu":
            if data.startswith("feedback_confirm_") or data.startswith("feedback_cancel_"):
                # Handle feedback confirmation
                from bot.handlers.feedback_handlers import handle_feedback_confirmation
                action = "confirm" if data.startswith("feedback_confirm_") else "cancel"
                target_user_id = int(data.split("_")[-1])
                await handle_feedback_confirmation(update, context, action, target_user_id)
            else:
                await handle_feedback_action(query, data, db_client, user_cache, user, config, translator)
        elif data.startswith("questions_") or data == "questions_noop":
            await handle_questions_action(query, data, db_client, user_cache, user, config, translator)
        elif data == "back_main":
            await handle_main_menu(query, config, user, None, db_client, user_cache)
        else:
            logger.warning(f"Unknown callback data: {data}")
            
    except Exception as e:
        logger.error(f"Error handling callback {data}: {e}")
        await query.edit_message_text(
            translator.translate('errors.general'),
            reply_markup=create_main_menu(config.is_admin_configured() and user.id == config.admin_user_id, translator)
        )


async def handle_main_menu(query, config: Config, user, translator=None, db_client=None, user_cache=None):
    """Handle main menu navigation."""
    if translator is None and db_client and user_cache:
        translator = await get_user_translator(user.id, db_client, user_cache)
    elif translator is None:
        from bot.i18n import get_translator
        translator = get_translator()
    
    keyboard = KeyboardGenerator.main_menu(config.is_admin_configured() and user.id == config.admin_user_id, translator)
    
    welcome_text = f"👋 {translator.translate('welcome.greeting', name=user.first_name)}\n\n"
    welcome_text += f"🤖 **Doyobi Diary**\n"
    welcome_text += translator.translate('welcome.choose_action')
    
    await query.edit_message_text(
        welcome_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_settings_menu(query, db_client: DatabaseClient, user_cache: TTLCache, user):
    """Handle settings menu display."""
    from bot.database.user_operations import UserOperations

    # Get user translator
    translator = await get_user_translator(user.id, db_client, user_cache)
    
    # Get user settings
    user_ops = UserOperations(db_client, user_cache)
    user_data = await user_ops.get_user_settings(user.id)
    
    if not user_data:
        await query.edit_message_text(
            translator.translate('errors.database'),
            reply_markup=KeyboardGenerator.main_menu(False, translator)
        )
        return
    
    keyboard = create_settings_menu(translator)
    
    # Localized settings display
    enabled_status = translator.translate('settings.notifications_enabled') if user_data['enabled'] else translator.translate('settings.notifications_disabled')
    
    settings_text = f"{translator.translate('settings.current_title')}\n\n"
    settings_text += f"{translator.translate('settings.notifications', status=enabled_status)}\n"
    settings_text += f"⏰ {translator.translate('settings.time_window')}: {user_data['window_start']} - {user_data['window_end']}\n"
    settings_text += f"📊 {translator.translate('settings.frequency')}: {translator.translate('settings.every_minutes', minutes=user_data['interval_min'])}"

    await query.edit_message_text(
        settings_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_friends_menu(query, db_client: DatabaseClient, user_cache: TTLCache, user):
    """Handle friends menu display."""
    # Get user translator
    translator = await get_user_translator(user.id, db_client, user_cache)
    
    keyboard = create_friends_menu(0, 0, translator)
    
    await query.edit_message_text(
        f"👥 **{translator.translate('menu.friends')}**\n\n"
        f"{translator.translate('friends.description', default='Управление друзьями и социальными связями:')}",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_history(query, config: Config, db_client: DatabaseClient, user_cache: TTLCache, user):
    """Handle direct web app opening."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

    # Get user translator
    translator = await get_user_translator(user.id, db_client, user_cache)
    
    # Сразу открываем веб-приложение без промежуточного меню
    web_app = WebAppInfo(url=config.webapp_url)  # Открываем главную страницу веб-приложения
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🌐 " + translator.translate('menu.history'), web_app=web_app)],
        [InlineKeyboardButton(translator.translate('menu.back'), callback_data="main_menu")]
    ])
    
    await query.edit_message_text(
        f"🌐 **{translator.translate('menu.history')}**\n\n"
        f"{translator.translate('history.webapp_description')}",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_admin_panel(query, config: Config, user, db_client: DatabaseClient, user_cache: TTLCache):
    """Handle admin panel access."""
    from bot.admin.admin_operations import AdminOperations

    # Get user translator
    translator = await get_user_translator(user.id, db_client, user_cache)
    
    # Create a temporary admin_ops instance for this check
    admin_ops = AdminOperations(None, config)  # db_client not needed for is_admin check
    
    if not admin_ops.is_admin(user.id):
        await query.edit_message_text(
            f"🔒 **{translator.translate('admin.access_denied')}**\n\n"
            f"{translator.translate('admin.admin_only')}",
            reply_markup=KeyboardGenerator.main_menu(False, translator)
        )
        return
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(translator.translate('admin.broadcast'), callback_data="admin_broadcast")],
        [InlineKeyboardButton(translator.translate('admin.stats'), callback_data="admin_stats")],
        [InlineKeyboardButton(translator.translate('menu.back'), callback_data="main_menu")]
    ])
    
    # Get version info
    from bot.utils.version import format_version_string, get_version_info
    version_string = format_version_string()
    version_info = get_version_info()
    
    admin_text = f"**{translator.translate('admin.title')}**\n\n"
    admin_text += f"🔧 **Версия:** `{version_string}`\n"
    admin_text += f"🌍 **Среда:** `{version_info['environment']}`\n\n"
    admin_text += f"{translator.translate('admin.choose_action')}"
    
    await query.edit_message_text(
        admin_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_language_menu(query, current_language: str, translator):
    """Handle language menu display."""
    keyboard = KeyboardGenerator.language_menu(current_language, translator)
    
    help_text = f"{translator.translate('language.title')}\n\n{translator.translate('language.subtitle')}"
    
    await query.edit_message_text(
        help_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_language_change(query, data: str, db_client: DatabaseClient, user_cache: TTLCache, user, config: Config):
    """Handle language change."""
    new_language = data.replace("language_", "")
    
    if new_language not in ['ru', 'en', 'es']:
        return
    
    # Update user language in database
    try:
        from bot.database.user_operations import UserOperations
        user_ops = UserOperations(db_client, user_cache)
        success = await user_ops.update_user_settings(user.id, {'language': new_language})
        
        # Force cache invalidation after language change
        if user_cache:
            await user_cache.invalidate(f"user_settings_{user.id}")
            await user_cache.invalidate(f"user_{user.id}")
        
        if success:
            # Create new translator with new language (don't modify global one)
            from bot.i18n.translator import Translator
            new_translator = Translator()
            new_translator.set_language(new_language)
            
            # Get language info
            lang_info = new_translator.get_language_info(new_language)
            
            await query.edit_message_text(
                new_translator.translate('language.changed', 
                                       language_name=lang_info['native'], 
                                       flag=lang_info['flag']),
                reply_markup=KeyboardGenerator.main_menu(config.is_admin_configured() and user.id == config.admin_user_id, new_translator),
                parse_mode='Markdown'
            )
        else:
            # If language column doesn't exist, just show success message anyway
            from bot.i18n.translator import Translator
            fallback_translator = Translator()
            fallback_translator.set_language(new_language)  # Set temporarily for this response
            
            # Get language info
            lang_info = fallback_translator.get_language_info(new_language)
            
            await query.edit_message_text(
                fallback_translator.translate('language.changed', 
                                           language_name=lang_info['native'], 
                                           flag=lang_info['flag']) + "\n\n"
                "📝 *Примечание: изменения будут применены после добавления поддержки в базу данных*",
                reply_markup=KeyboardGenerator.main_menu(config.is_admin_configured() and user.id == config.admin_user_id, fallback_translator),
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error changing language: {e}")
        from bot.i18n.translator import Translator
        translator = Translator()
        await query.edit_message_text(
            translator.translate('errors.general'),
            reply_markup=create_main_menu(config.is_admin_configured() and user.id == config.admin_user_id, translator),
            parse_mode='Markdown'
        )



async def handle_settings_action(query, data: str, db_client: DatabaseClient, user_cache: TTLCache, user, config: Config, translator=None):
    """Handle settings-related actions."""
    if translator is None:
        translator = await get_user_translator(user.id, db_client, user_cache)
    
    action = data.replace("settings_", "")
    
    if action == "toggle_notifications":
        # Toggle user notifications
        from bot.database.user_operations import UserOperations
        user_ops = UserOperations(db_client, user_cache)
        
        # Get current settings
        user_settings = await user_ops.get_user_settings(user.id)
        if not user_settings:
            await query.edit_message_text(
                translator.translate('settings.error_get'),
                reply_markup=KeyboardGenerator.main_menu(config.is_admin_configured() and user.id == config.admin_user_id, translator)
            )
            return
            
        # Toggle enabled status
        new_enabled = not user_settings.get('enabled', True)
        success = await user_ops.update_user_settings(user.id, {'enabled': new_enabled})
        
        if success:
            if new_enabled:
                message = translator.translate('settings.notifications_enabled_msg')
            else:
                message = translator.translate('settings.notifications_disabled_msg')
            
            await query.edit_message_text(
                message,
                reply_markup=create_settings_menu(translator)
            )
        else:
            await query.edit_message_text(
                translator.translate('settings.error_update'),
                reply_markup=create_settings_menu(translator)
            )
    elif action == "back":
        # Use config passed as parameter
        await handle_main_menu(query, config, user, translator, db_client, user_cache)
    elif action == "time_window":
        await query.edit_message_text(
            translator.translate('settings.time_window_help'),
            reply_markup=create_settings_menu(translator),
            parse_mode='Markdown'
        )
    elif action == "frequency":
        await query.edit_message_text(
            translator.translate('settings.frequency_help'),
            reply_markup=create_settings_menu(translator),
            parse_mode='Markdown'
        )
    elif action == "view":
        await handle_settings_menu(query, db_client, user_cache, user)


async def handle_friends_action(query, data: str, db_client: DatabaseClient, user, config: Config, translator=None, user_cache=None):
    """Handle friends-related actions."""
    if translator is None:
        if user_cache:
            translator = await get_user_translator(user.id, db_client, user_cache)
        else:
            from bot.i18n.translator import Translator
            translator = Translator()
    
    action = data.replace("friends_", "")
    
    if action == "add":
        await query.edit_message_text(
            translator.translate('friends.add_instruction'),
            reply_markup=create_friends_menu(0, 0, translator),
            parse_mode='Markdown'
        )
    elif action == "list":
        # Get friends list from database
        from bot.database.friend_operations import FriendOperations
        friend_ops = FriendOperations(db_client)
        
        friends = await friend_ops.get_friends_list_optimized(user.id)
        
        if not friends:
            await query.edit_message_text(
                translator.translate('friends.list_empty'),
                reply_markup=create_friends_menu(0, 0, translator),
                parse_mode='Markdown'
            )
        else:
            friends_text = f"{translator.translate('friends.list_title')}\n\n"
            for friend in friends[:10]:  # Показываем максимум 10 друзей
                username = friend.get('tg_username', '')
                name = friend.get('tg_first_name', 'Без имени')
                friends_text += f"• @{username} - {name}\n" if username else f"• {name}\n"
            
            if len(friends) > 10:
                friends_text += f"\n{translator.translate('friends.list_more', count=len(friends) - 10)}"
                
            await query.edit_message_text(
                friends_text,
                reply_markup=create_friends_menu(0, 0, translator),
                parse_mode='Markdown'
            )
    elif action == "back":
        # Use config passed as parameter
        await handle_main_menu(query, config, user, translator, db_client, user_cache)
    elif action == "requests":
        await query.edit_message_text(
            translator.translate('friends.requests_help'),
            reply_markup=create_friends_menu(0, 0, translator),
            parse_mode='Markdown'
        )
    elif action == "discover":
        await query.edit_message_text(
            translator.translate('friends.discover_help'),
            reply_markup=create_friends_menu(0, 0, translator),
            parse_mode='Markdown'
        )
    elif action == "activities":
        await query.edit_message_text(
            translator.translate('friends.activities_help'),
            reply_markup=create_friends_menu(0, 0, translator),
            parse_mode='Markdown'
        )


async def handle_admin_action(query, data: str, db_client: DatabaseClient, user, config: Config, translator=None, user_cache=None):
    """Handle admin-related actions."""
    if translator is None:
        if user_cache:
            translator = await get_user_translator(user.id, db_client, user_cache)
        else:
            from bot.i18n import get_translator
            translator = get_translator()
    
    from bot.admin.admin_operations import AdminOperations
    admin_ops = AdminOperations(db_client, config)
    
    if not admin_ops.is_admin(user.id):
        await query.edit_message_text(
            translator.translate('admin.access_denied_full'),
            reply_markup=KeyboardGenerator.main_menu(False, translator),
            parse_mode='Markdown'
        )
        return
    
    action = data.replace("admin_", "")
    
    if action == "broadcast":
        # This will be handled by ConversationHandler entry point
        # Just show a temp message since callback will be intercepted
        await query.edit_message_text(
            translator.translate('admin.broadcast_starting'),
            parse_mode='Markdown'
        )
    elif action == "stats":
        await query.edit_message_text(
            translator.translate('admin.stats_help'),
            reply_markup=KeyboardGenerator.main_menu(True, translator),
            parse_mode='Markdown'
        )
    else:
        await handle_main_menu(query, config, user, translator)


async def handle_feedback_action(query, data: str, db_client: DatabaseClient, user_cache: TTLCache, user, config: Config, translator=None):
    """Handle feedback-related actions."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    if translator is None:
        translator = await get_user_translator(user.id, db_client, user_cache)
    
    # Check if feedback is enabled
    if not config.is_feedback_enabled():
        await query.edit_message_text(
            translator.translate('feedback.disabled'),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(translator.translate("menu.back"), callback_data="main_menu")]
            ]),
            parse_mode='Markdown'
        )
        return
    
    if data == "feedback_menu":
        # Main feedback menu
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(translator.translate("feedback.bug_report"), callback_data="feedback_bug_report")],
            [InlineKeyboardButton(translator.translate("feedback.feature_request"), callback_data="feedback_feature_request")],
            [InlineKeyboardButton(translator.translate("feedback.general"), callback_data="feedback_general")],
            [InlineKeyboardButton(translator.translate("menu.back"), callback_data="main_menu")]
        ])
        
        await query.edit_message_text(
            f"**{translator.translate('feedback.title')}**\n\n"
            f"{translator.translate('feedback.description')}",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
    elif data in ["feedback_bug_report", "feedback_feature_request", "feedback_general"]:
        # Start feedback session
        feedback_type = data.replace("feedback_", "")
        
        # Initialize feedback manager
        from bot.feedback import FeedbackManager
        from bot.utils.rate_limiter import MultiTierRateLimiter
        
        rate_limiter = MultiTierRateLimiter(feedback_rate_limit=config.feedback_rate_limit)
        feedback_manager = FeedbackManager(config, rate_limiter, user_cache)
        
        # Check rate limit
        if not await feedback_manager.check_rate_limit(user.id):
            await query.edit_message_text(
                translator.translate('feedback.rate_limited'),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(translator.translate("menu.back"), callback_data="feedback_menu")]
                ]),
                parse_mode='Markdown'
            )
            return
        
        # Start feedback session
        user_language = await get_user_language(user.id, db_client, user_cache)
        success = await feedback_manager.start_feedback_session(user.id, feedback_type, user_language)
        
        if success:
            # Show description prompt
            description_key = f"feedback.{feedback_type}_description"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(translator.translate("menu.back"), callback_data="feedback_menu")]
            ])
            
            await query.edit_message_text(
                f"{translator.translate(description_key)}\n\n"
                f"{translator.translate('feedback.enter_description')}",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                translator.translate('feedback.rate_limited'),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(translator.translate("menu.back"), callback_data="feedback_menu")]
                ]),
                parse_mode='Markdown'
            )


async def handle_questions_menu(query, db_client: DatabaseClient, user_cache: TTLCache, user):
    """Handle questions menu display."""
    from bot.database.user_operations import UserOperations
    from bot.keyboards.keyboard_generators import create_questions_menu
    from bot.questions import QuestionManager

    # Get user translator
    translator = await get_user_translator(user.id, db_client, user_cache)
    
    # Initialize question manager
    question_manager = QuestionManager(db_client, user_cache)
    
    # Get user questions summary
    questions_summary = await question_manager.get_user_questions_summary(user.id)
    
    # Get notifications status from user settings
    user_ops = UserOperations(db_client, user_cache)
    user_data = await user_ops.get_user_settings(user.id)
    notifications_enabled = user_data.get('enabled', True) if user_data else True
    
    # Create keyboard
    keyboard = create_questions_menu(questions_summary, notifications_enabled, translator)
    
    # Create menu text
    menu_text = f"{translator.translate('questions.title')}\n\n"
    menu_text += translator.translate('questions.description')
    
    await query.edit_message_text(
        menu_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_questions_action(query, data: str, db_client: DatabaseClient, user_cache: TTLCache, user, config: Config, translator=None):
    """Handle questions-related actions."""
    from bot.database.user_operations import UserOperations
    from bot.keyboards.keyboard_generators import (
        create_question_delete_confirm,
        create_question_edit_menu,
        create_question_templates_menu,
        create_questions_menu,
    )
    from bot.questions import QuestionManager, QuestionTemplates
    
    if translator is None:
        translator = await get_user_translator(user.id, db_client, user_cache)
    
    # Initialize question manager
    question_manager = QuestionManager(db_client, user_cache)
    
    try:
        if data == "questions_noop":
            # No-op callback (for section headers)
            return
            
        elif data == "questions_toggle_notifications":
            # Toggle global notifications
            user_ops = UserOperations(db_client, user_cache)
            user_data = await user_ops.get_user_settings(user.id)
            
            if user_data:
                new_enabled = not user_data.get('enabled', True)
                success = await user_ops.update_user_settings(user.id, {'enabled': new_enabled})
                
                if success:
                    # Refresh questions menu
                    await handle_questions_menu(query, db_client, user_cache, user)
                else:
                    await query.edit_message_text(
                        translator.translate('errors.database'),
                        parse_mode='Markdown'
                    )
            
        elif data.startswith("questions_edit:"):
            # Edit specific question
            question_id = int(data.split(":")[1])
            question = await question_manager.question_ops.get_question_by_id(question_id)
            
            if question:
                keyboard = create_question_edit_menu(question, translator)
                
                # Create edit text
                edit_text = f"{translator.translate('questions.edit_title')}\n\n"
                edit_text += translator.translate('questions.current_text', text=question['question_text']) + "\n"
                edit_text += translator.translate('questions.current_schedule', 
                    start=question['window_start'], 
                    end=question['window_end'], 
                    interval=question['interval_minutes']) + "\n"
                
                status = translator.translate('questions.enable') if question['active'] else translator.translate('questions.disable')
                edit_text += translator.translate('questions.current_status', status=status) + "\n\n"
                edit_text += translator.translate('questions.edit_instructions')
                
                await query.edit_message_text(
                    edit_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    translator.translate('questions.error_not_found'),
                    parse_mode='Markdown'
                )
        
        elif data.startswith("questions_delete:"):
            # Show delete confirmation
            question_id = int(data.split(":")[1])
            keyboard = create_question_delete_confirm(question_id, translator)
            
            await query.edit_message_text(
                translator.translate('questions.delete_confirm_text'),
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        
        elif data.startswith("questions_delete_yes:"):
            # Confirm deletion
            question_id = int(data.split(":")[1])
            success = await question_manager.question_ops.delete_question(question_id)
            
            if success:
                await query.edit_message_text(
                    translator.translate('questions.success_deleted'),
                    parse_mode='Markdown'
                )
                # Return to questions menu after short delay
                await handle_questions_menu(query, db_client, user_cache, user)
            else:
                await query.edit_message_text(
                    translator.translate('questions.error_not_found'),
                    parse_mode='Markdown'
                )
        
        elif data.startswith("questions_toggle:"):
            # Toggle question status
            question_id = int(data.split(":")[1])
            success, new_status = await question_manager.toggle_question_status(question_id)
            
            if success:
                # Refresh the edit menu
                await handle_questions_action(query, f"questions_edit:{question_id}", db_client, user_cache, user, config, translator)
            else:
                await query.edit_message_text(
                    translator.translate('questions.error_not_found'),
                    parse_mode='Markdown'
                )
        
        elif data.startswith("questions_test:"):
            # Send test notification
            question_id = int(data.split(":")[1])
            question = await question_manager.question_ops.get_question_by_id(question_id)
            
            if question:
                # Send test message
                from telegram import Bot
                bot = Bot(token=config.bot_token)
                
                try:
                    test_message = await bot.send_message(
                        user.id,
                        f"🧪 {translator.translate('questions.success_test')}\n\n{question['question_text']}"
                    )
                    
                    # Save notification for reply tracking
                    await question_manager.save_notification_for_reply(
                        user.id, question_id, test_message.message_id
                    )
                    
                    await query.edit_message_text(
                        translator.translate('questions.success_test'),
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Error sending test notification: {e}")
                    await query.edit_message_text(
                        translator.translate('errors.general'),
                        parse_mode='Markdown'
                    )
            else:
                await query.edit_message_text(
                    translator.translate('questions.error_not_found'),
                    parse_mode='Markdown'
                )
        
        elif data == "questions_templates":
            # Show template categories
            keyboard = create_question_templates_menu(None, translator)
            
            await query.edit_message_text(
                f"{translator.translate('questions.templates')}\n\n"
                f"Выберите категорию шаблонов:",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        
        elif data.startswith("questions_templates_cat:"):
            # Show templates in category
            category = data.split(":")[1]
            keyboard = create_question_templates_menu(category, translator)
            
            category_names = QuestionTemplates.get_category_names()
            category_name = category_names.get(category, category)
            
            await query.edit_message_text(
                f"{translator.translate('questions.templates')}\n\n"
                f"**{category_name}**\n\n"
                f"Выберите шаблон:",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        
        elif data.startswith("questions_use_template:"):
            # Use specific template
            template_name = data.split(":", 1)[1]
            template = QuestionTemplates.get_template_by_name(template_name)
            
            if template:
                # Show template confirmation
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            translator.translate("questions.template_use"),
                            callback_data=f"questions_create_from_template:{template_name}"
                        ),
                        InlineKeyboardButton(
                            translator.translate("questions.template_cancel"),
                            callback_data="questions_templates"
                        )
                    ]
                ])
                
                template_text = translator.translate('questions.template_selected',
                    name=template['name'],
                    text=template['text'],
                    start=template['window_start'],
                    end=template['window_end'],
                    interval=template['interval_minutes']
                )
                
                await query.edit_message_text(
                    template_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    translator.translate('questions.error_not_found'),
                    parse_mode='Markdown'
                )
        
        elif data.startswith("questions_create_from_template:"):
            # Create question from template
            template_name = data.split(":", 1)[1]
            template = QuestionTemplates.get_template_by_name(template_name)
            
            if template:
                # Create question data
                question_data = {
                    'question_name': template['name'],
                    'question_text': template['text'],
                    'window_start': template['window_start'],
                    'window_end': template['window_end'],
                    'interval_minutes': template['interval_minutes']
                }
                
                created_question = await question_manager.create_custom_question(user.id, question_data)
                
                if created_question:
                    await query.edit_message_text(
                        translator.translate('questions.success_created'),
                        parse_mode='Markdown'
                    )
                    # Return to questions menu
                    await handle_questions_menu(query, db_client, user_cache, user)
                else:
                    await query.edit_message_text(
                        translator.translate('questions.error_limit'),
                        parse_mode='Markdown'
                    )
            else:
                await query.edit_message_text(
                    translator.translate('questions.error_not_found'),
                    parse_mode='Markdown'
                )
        
        elif data == "questions_show_all":
            # Show all settings summary
            questions_summary = await question_manager.get_user_questions_summary(user.id)
            user_ops = UserOperations(db_client, user_cache)
            user_data = await user_ops.get_user_settings(user.id)
            notifications_enabled = user_data.get('enabled', True) if user_data else True
            
            # Create summary text
            summary_text = f"{translator.translate('questions.all_settings_title')}\n\n"
            
            notif_status = "✅" if notifications_enabled else "❌"
            summary_text += translator.translate('questions.notifications_status', status=notif_status) + "\n"
            
            stats = questions_summary.get('stats', {})
            summary_text += translator.translate('questions.active_questions_count', 
                count=stats.get('active_questions', 0),
                max=stats.get('max_questions', 5)
            ) + "\n\n"
            
            summary_text += translator.translate('questions.questions_list') + "\n"
            
            # Default question
            default_q = questions_summary.get('default_question')
            if default_q:
                status = "✅" if default_q.get('active', True) else "❌"
                summary_text += f"{translator.translate('questions.default_marker')} {default_q['question_name']}: \"{default_q['question_text'][:30]}...\" {status}\n"
                summary_text += f"   {default_q['window_start']}-{default_q['window_end']}, каждые {default_q['interval_minutes']} мин\n"
            
            # Custom questions
            custom_questions = questions_summary.get('custom_questions', [])
            for question in custom_questions:
                status = "✅" if question.get('active', True) else "❌"
                summary_text += f"{translator.translate('questions.custom_marker')} {question['question_name']}: \"{question['question_text'][:30]}...\" {status}\n"
                summary_text += f"   {question['window_start']}-{question['window_end']}, каждые {question['interval_minutes']} мин\n"
            
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(translator.translate("questions.back"), callback_data="menu_questions")]
            ])
            
            await query.edit_message_text(
                summary_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        
        else:
            # Return to main questions menu for unknown actions
            await handle_questions_menu(query, db_client, user_cache, user)
            
    except Exception as e:
        logger.error(f"Error handling questions action {data}: {e}")
        await query.edit_message_text(
            translator.translate('errors.general'),
            parse_mode='Markdown'
        )


def setup_callback_handlers(
    application: Application,
    db_client: DatabaseClient,
    user_cache: TTLCache,
    rate_limiter: MultiTierRateLimiter,
    config: Config
) -> None:
    """Setup callback query handlers."""
    
    # Store dependencies in bot_data for access in handlers
    application.bot_data['db_client'] = db_client
    application.bot_data['user_cache'] = user_cache
    application.bot_data['rate_limiter'] = rate_limiter
    application.bot_data['config'] = config
    
    # Register callback query handler
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    logger.info("Callback handlers registered successfully")
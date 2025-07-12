"""
Keyboard generators for Doyobi Diary.

This module provides dynamic inline keyboard generation for the Telegram bot interface.
"""

from typing import Any, Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class KeyboardGenerator:
    """Dynamic inline keyboard generator."""
    
    @staticmethod
    def main_menu(is_admin: bool = False, translator=None) -> InlineKeyboardMarkup:
        """
        Generate main menu keyboard.
        
        Args:
            is_admin: Whether user is admin (shows admin panel)
            translator: Translator instance for localization
            
        Returns:
            InlineKeyboardMarkup for main menu
        """
        if translator is None:
            from bot.i18n.translator import Translator
            translator = Translator()
            
        keyboard = [
            [InlineKeyboardButton(translator.translate("menu.questions"), callback_data="menu_questions")],
            [InlineKeyboardButton(translator.translate("menu.friends"), callback_data="menu_friends")],
            [InlineKeyboardButton(translator.translate("menu.history"), callback_data="menu_history")],
        ]
        
        if is_admin:
            keyboard.append([InlineKeyboardButton(translator.translate("menu.admin"), callback_data="menu_admin")])
        
        keyboard.extend([
            [InlineKeyboardButton(translator.translate("menu.language"), callback_data="menu_language")],
            [InlineKeyboardButton(translator.translate("feedback.title"), callback_data="feedback_menu")]
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def settings_menu(translator=None) -> InlineKeyboardMarkup:
        """Generate settings menu keyboard."""
        if translator is None:
            from bot.i18n.translator import Translator
            translator = Translator()
            
        keyboard = [
            [InlineKeyboardButton(translator.translate("settings.toggle_notifications"), callback_data="settings_toggle_notifications")],
            [InlineKeyboardButton(translator.translate("settings.set_time_window"), callback_data="settings_time_window")],
            [InlineKeyboardButton(translator.translate("settings.set_frequency"), callback_data="settings_frequency")],
            [InlineKeyboardButton(translator.translate("menu.back_main"), callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def friends_menu(
        pending_requests: int = 0, 
        friends_count: int = 0,
        translator=None
    ) -> InlineKeyboardMarkup:
        """
        Generate friends menu keyboard.
        
        Args:
            pending_requests: Number of pending friend requests
            friends_count: Total number of friends
            translator: Translator instance for localization
            
        Returns:
            InlineKeyboardMarkup for friends menu
        """
        if translator is None:
            from bot.i18n.translator import Translator
            translator = Translator()
            
        keyboard = [
            [InlineKeyboardButton(translator.translate("friends.add"), callback_data="friends_add")],
        ]
        
        # Friend requests with count indicator
        requests_text = translator.translate("friends.requests")
        if pending_requests > 0:
            requests_text += f" ({pending_requests})"
        keyboard.append([InlineKeyboardButton(requests_text, callback_data="friends_requests")])
        
        # Friends list with count
        friends_text = translator.translate("friends.list")
        if friends_count > 0:
            friends_text += f" ({friends_count})"
        keyboard.append([InlineKeyboardButton(friends_text, callback_data="friends_list")])
        
        keyboard.extend([
            [InlineKeyboardButton(translator.translate("friends.discover"), callback_data="friends_discover")],
            [InlineKeyboardButton(translator.translate("friends.activities"), callback_data="friends_activities")],
            [InlineKeyboardButton(translator.translate("menu.back_main"), callback_data="back_main")]
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def friend_requests_menu(
        incoming_count: int = 0,
        outgoing_count: int = 0,
        translator = None
    ) -> InlineKeyboardMarkup:
        """
        Generate friend requests menu keyboard.
        
        Args:
            incoming_count: Number of incoming requests
            outgoing_count: Number of outgoing requests
            translator: Translator instance for localization
            
        Returns:
            InlineKeyboardMarkup for friend requests menu
        """
        keyboard = []
        
        # Incoming requests with count
        incoming_text = translator.translate('friends.incoming_requests') if translator else "📥 Incoming Requests"
        if incoming_count > 0:
            incoming_text += f" ({incoming_count})"
        keyboard.append([InlineKeyboardButton(incoming_text, callback_data="requests_incoming")])
        
        # Outgoing requests with count
        outgoing_text = translator.translate('friends.outgoing_requests') if translator else "📤 Outgoing Requests"
        if outgoing_count > 0:
            outgoing_text += f" ({outgoing_count})"
        keyboard.append([InlineKeyboardButton(outgoing_text, callback_data="requests_outgoing")])
        
        keyboard.append([InlineKeyboardButton(
            translator.translate('friends.back_to_friends') if translator else "🔙 Back to Friends", 
            callback_data="back_friends"
        )])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def friend_discovery_list(recommendations: List[Dict[str, Any]], translator = None) -> InlineKeyboardMarkup:
        """
        Generate friend discovery keyboard.
        
        Args:
            recommendations: List of friend recommendations
            translator: Translator instance for localization
            
        Returns:
            InlineKeyboardMarkup for friend discovery
        """
        if not recommendations:
            keyboard = [
                [InlineKeyboardButton(
                    translator.translate('friends.back_to_friends') if translator else "🔙 Back to Friends", 
                    callback_data="back_friends"
                )]
            ]
            return InlineKeyboardMarkup(keyboard)
        
        keyboard = []
        
        # Add buttons for each recommendation (max 10)
        for i, rec in enumerate(recommendations[:10]):
            user_name = rec.get('first_name', 'Unknown')
            mutual_count = rec.get('mutual_friends_count', 0)
            
            button_text = f"➕ {user_name}"
            if mutual_count > 0:
                button_text += f" ({mutual_count} mutual)"
            
            keyboard.append([
                InlineKeyboardButton(
                    button_text, 
                    callback_data=f"add_friend:{rec['tg_id']}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(
            translator.translate('friends.back_to_friends') if translator else "🔙 Back to Friends", 
            callback_data="back_friends"
        )])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def admin_menu(translator = None) -> InlineKeyboardMarkup:
        """Generate admin menu keyboard."""
        keyboard = [
            [InlineKeyboardButton(
                translator.translate('admin.broadcast') if translator else "📢 Send Broadcast", 
                callback_data="admin_broadcast"
            )],
            [InlineKeyboardButton(
                translator.translate('admin.user_statistics') if translator else "📊 User Statistics", 
                callback_data="admin_stats"
            )],
            [InlineKeyboardButton(
                translator.translate('admin.health_check') if translator else "🏥 Health Check", 
                callback_data="admin_health"
            )],
            [InlineKeyboardButton(
                translator.translate('admin.test_broadcast') if translator else "🧪 Test Broadcast", 
                callback_data="admin_test_broadcast"
            )],
            [InlineKeyboardButton(
                translator.translate('menu.back_main') if translator else "🔙 Back to Main Menu", 
                callback_data="back_main"
            )]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def broadcast_confirmation() -> InlineKeyboardMarkup:
        """Generate broadcast confirmation keyboard."""
        keyboard = [
            [
                InlineKeyboardButton("✅ Send", callback_data="broadcast_confirm"),
                InlineKeyboardButton("❌ Cancel", callback_data="broadcast_cancel")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def friend_request_actions(requester_id: int) -> InlineKeyboardMarkup:
        """
        Generate friend request action buttons.
        
        Args:
            requester_id: ID of user who sent the request
            
        Returns:
            InlineKeyboardMarkup with accept/decline options
        """
        keyboard = [
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"accept_friend:{requester_id}"),
                InlineKeyboardButton("❌ Decline", callback_data=f"decline_friend:{requester_id}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def notification_toggle(enabled: bool) -> InlineKeyboardMarkup:
        """
        Generate notification toggle keyboard.
        
        Args:
            enabled: Current notification status
            
        Returns:
            InlineKeyboardMarkup with toggle option
        """
        action = "disable" if enabled else "enable"
        icon = "🔕" if enabled else "🔔"
        text = f"{icon} Turn {'Off' if enabled else 'On'} Notifications"
        
        keyboard = [
            [InlineKeyboardButton(text, callback_data=f"notifications_{action}")],
            [InlineKeyboardButton("🔙 Back to Settings", callback_data="back_settings")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def pagination_keyboard(
        current_page: int,
        total_pages: int,
        callback_prefix: str,
        back_callback: str = "back_main"
    ) -> InlineKeyboardMarkup:
        """
        Generate pagination keyboard.
        
        Args:
            current_page: Current page number (0-based)
            total_pages: Total number of pages
            callback_prefix: Prefix for pagination callbacks
            back_callback: Callback for back button
            
        Returns:
            InlineKeyboardMarkup with pagination controls
        """
        keyboard = []
        
        if total_pages > 1:
            pagination_row = []
            
            # Previous page button
            if current_page > 0:
                pagination_row.append(
                    InlineKeyboardButton("◀️", callback_data=f"{callback_prefix}:{current_page - 1}")
                )
            
            # Page indicator
            pagination_row.append(
                InlineKeyboardButton(
                    f"{current_page + 1}/{total_pages}", 
                    callback_data="page_info"
                )
            )
            
            # Next page button
            if current_page < total_pages - 1:
                pagination_row.append(
                    InlineKeyboardButton("▶️", callback_data=f"{callback_prefix}:{current_page + 1}")
                )
            
            keyboard.append(pagination_row)
        
        # Back button
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=back_callback)])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def yes_no_keyboard(
        yes_callback: str,
        no_callback: str,
        yes_text: str = "✅ Yes",
        no_text: str = "❌ No"
    ) -> InlineKeyboardMarkup:
        """
        Generate yes/no confirmation keyboard.
        
        Args:
            yes_callback: Callback for yes button
            no_callback: Callback for no button
            yes_text: Text for yes button
            no_text: Text for no button
            
        Returns:
            InlineKeyboardMarkup with yes/no options
        """
        keyboard = [
            [
                InlineKeyboardButton(yes_text, callback_data=yes_callback),
                InlineKeyboardButton(no_text, callback_data=no_callback)
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def single_button_keyboard(text: str, callback_data: str) -> InlineKeyboardMarkup:
        """
        Generate keyboard with single button.
        
        Args:
            text: Button text
            callback_data: Button callback data
            
        Returns:
            InlineKeyboardMarkup with single button
        """
        keyboard = [[InlineKeyboardButton(text, callback_data=callback_data)]]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def web_app_keyboard(url: str, text: str = "📊 Open Web App") -> InlineKeyboardMarkup:
        """
        Generate keyboard with web app button.
        
        Args:
            url: Web app URL
            text: Button text
            
        Returns:
            InlineKeyboardMarkup with web app button
        """
        from telegram import WebApp
        
        keyboard = [
            [InlineKeyboardButton(text, web_app=WebApp(url=url))],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def language_menu(current_language: str = 'ru', translator=None) -> InlineKeyboardMarkup:
        """
        Generate language selection keyboard.
        
        Args:
            current_language: Currently selected language
            translator: Translator instance for localization
            
        Returns:
            InlineKeyboardMarkup for language selection
        """
        if translator is None:
            from bot.i18n.translator import Translator
            translator = Translator()
        
        keyboard = [
            [InlineKeyboardButton(
                "🇷🇺 Русский" + (" ✓" if current_language == 'ru' else ""), 
                callback_data="language_ru"
            )],
            [InlineKeyboardButton(
                "🇺🇸 English" + (" ✓" if current_language == 'en' else ""), 
                callback_data="language_en"
            )],
            [InlineKeyboardButton(
                "🇪🇸 Español" + (" ✓" if current_language == 'es' else ""), 
                callback_data="language_es"
            )],
            [InlineKeyboardButton(translator.translate("menu.back_main"), callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def questions_menu(
        questions_summary: Dict, 
        notifications_enabled: bool = True, 
        translator=None
    ) -> InlineKeyboardMarkup:
        """
        Generate questions menu keyboard.
        
        Args:
            questions_summary: Summary of user questions
            notifications_enabled: Whether notifications are globally enabled
            translator: Translator instance for localization
            
        Returns:
            InlineKeyboardMarkup for questions menu
        """
        if translator is None:
            from bot.i18n.translator import Translator
            translator = Translator()
        
        keyboard = []
        
        # Global notifications toggle
        notif_status = "✅" if notifications_enabled else "❌"
        notif_text = translator.translate("questions.notifications_toggle", status=notif_status)
        keyboard.append([InlineKeyboardButton(notif_text, callback_data="settings_toggle_notifications")])
        
        keyboard.append([])  # Empty row separator
        
        # Default question
        default_q = questions_summary.get('default_question')
        if default_q:
            status = "✅" if default_q.get('active', True) else "❌"
            text = f"🔸 {translator.translate('questions.default_question')} {status}"
            keyboard.append([InlineKeyboardButton(text, callback_data=f"questions_edit:{default_q['id']}")])
        
        # Custom questions
        custom_questions = questions_summary.get('custom_questions', [])
        if custom_questions:
            keyboard.append([])  # Separator
            keyboard.append([InlineKeyboardButton(
                translator.translate("questions.custom_section"), 
                callback_data="questions_noop"
            )])
            
            for question in custom_questions:
                status = "✅" if question.get('active', True) else "❌"
                name = question.get('question_name', 'Вопрос')[:15]  # Limit length
                text = f"• {name} {status}"
                keyboard.append([
                    InlineKeyboardButton(text, callback_data=f"questions_edit:{question['id']}"),
                    InlineKeyboardButton("🗑️", callback_data=f"questions_delete:{question['id']}")
                ])
        
        # Add new question button
        can_add = questions_summary.get('can_add_more', True)
        stats = questions_summary.get('stats', {})
        active_count = stats.get('active_questions', 0)
        max_count = stats.get('max_questions', 5)
        
        if can_add:
            keyboard.append([])  # Separator
            keyboard.append([InlineKeyboardButton(
                translator.translate("questions.add_new", count=f"{active_count}/{max_count}"),
                callback_data="questions_add"
            )])
        
        # Additional options
        keyboard.extend([
            [],  # Separator
            [InlineKeyboardButton(translator.translate("questions.templates"), callback_data="questions_templates")],
            [InlineKeyboardButton(translator.translate("questions.show_all_settings"), callback_data="questions_show_all")],
            [InlineKeyboardButton(translator.translate("menu.back_main"), callback_data="back_main")]
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def question_edit_menu(question: Dict, translator=None) -> InlineKeyboardMarkup:
        """
        Generate question edit menu keyboard.
        
        Args:
            question: Question data
            translator: Translator instance for localization
            
        Returns:
            InlineKeyboardMarkup for question editing
        """
        if translator is None:
            from bot.i18n.translator import Translator
            translator = Translator()
        
        keyboard = []
        
        # Edit options
        keyboard.extend([
            [InlineKeyboardButton(translator.translate("questions.edit_text"), callback_data=f"questions_edit_text:{question['id']}")],
            [InlineKeyboardButton(translator.translate("questions.edit_schedule"), callback_data=f"questions_edit_schedule:{question['id']}")],
        ])
        
        # Toggle status (only for non-default questions)
        if not question.get('is_default', False):
            status_text = translator.translate("questions.disable") if question.get('active') else translator.translate("questions.enable")
            keyboard.append([InlineKeyboardButton(status_text, callback_data=f"questions_toggle:{question['id']}")])
        
        # Test question
        keyboard.append([InlineKeyboardButton(translator.translate("questions.test"), callback_data=f"questions_test:{question['id']}")])
        
        # Delete (only for non-default questions)
        if not question.get('is_default', False):
            keyboard.append([InlineKeyboardButton(translator.translate("questions.delete"), callback_data=f"questions_delete_confirm:{question['id']}")])
        
        # Back button
        keyboard.append([InlineKeyboardButton(translator.translate("questions.back"), callback_data="menu_questions")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def question_templates_menu(category: str = None, translator=None) -> InlineKeyboardMarkup:
        """
        Generate question templates menu keyboard.
        
        Args:
            category: Template category to show
            translator: Translator instance for localization
            
        Returns:
            InlineKeyboardMarkup for templates
        """
        if translator is None:
            from bot.i18n.translator import Translator
            translator = Translator()
        
        keyboard = []
        
        if category is None:
            # Show categories
            from bot.questions.question_templates import QuestionTemplates
            categories = QuestionTemplates.get_category_names()
            
            for cat_key, cat_name in categories.items():
                keyboard.append([InlineKeyboardButton(
                    cat_name, 
                    callback_data=f"questions_templates_cat:{cat_key}"
                )])
            
            # Popular templates shortcut
            keyboard.append([InlineKeyboardButton(
                translator.translate("questions.popular_templates"),
                callback_data="questions_templates_cat:popular"
            )])
            
        else:
            # Show templates in category
            from bot.questions.question_templates import QuestionTemplates
            
            if category == "popular":
                templates = QuestionTemplates.get_popular_templates()
            else:
                all_templates = QuestionTemplates.get_templates()
                templates = all_templates.get(category, [])
            
            for template in templates:
                name = template['name'][:25]  # Limit length
                keyboard.append([InlineKeyboardButton(
                    f"➕ {name}",
                    callback_data=f"questions_use_template:{template['name']}"
                )])
            
            # Back to categories
            keyboard.append([InlineKeyboardButton(
                translator.translate("questions.back_to_categories"),
                callback_data="questions_templates"
            )])
        
        # Back to questions menu
        keyboard.append([InlineKeyboardButton(
            translator.translate("questions.back"),
            callback_data="menu_questions"
        )])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def question_delete_confirm(question_id: int, translator=None) -> InlineKeyboardMarkup:
        """
        Generate question deletion confirmation keyboard.
        
        Args:
            question_id: Question ID to delete
            translator: Translator instance for localization
            
        Returns:
            InlineKeyboardMarkup for deletion confirmation
        """
        if translator is None:
            from bot.i18n.translator import Translator
            translator = Translator()
        
        keyboard = [
            [
                InlineKeyboardButton(
                    translator.translate("questions.delete_confirm"),
                    callback_data=f"questions_delete_yes:{question_id}"
                ),
                InlineKeyboardButton(
                    translator.translate("questions.delete_cancel"),
                    callback_data=f"questions_edit:{question_id}"
                )
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)


# Convenience functions for common keyboards

def get_main_menu_keyboard(is_admin: bool = False, translator=None) -> InlineKeyboardMarkup:
    """Get main menu keyboard."""
    return KeyboardGenerator.main_menu(is_admin, translator)


def get_settings_keyboard(translator=None) -> InlineKeyboardMarkup:
    """Get settings menu keyboard."""
    return KeyboardGenerator.settings_menu(translator)


def get_friends_keyboard(pending_requests: int = 0, friends_count: int = 0, translator=None) -> InlineKeyboardMarkup:
    """Get friends menu keyboard."""
    return KeyboardGenerator.friends_menu(pending_requests, friends_count, translator)


def get_admin_keyboard(translator = None) -> InlineKeyboardMarkup:
    """Get admin menu keyboard."""
    return KeyboardGenerator.admin_menu(translator)


# Aliases for new modular architecture
create_main_menu = get_main_menu_keyboard
create_settings_menu = get_settings_keyboard
create_friends_menu = get_friends_keyboard
create_admin_menu = get_admin_keyboard
create_language_menu = KeyboardGenerator.language_menu

# New questions system keyboards
create_questions_menu = KeyboardGenerator.questions_menu
create_question_edit_menu = KeyboardGenerator.question_edit_menu
create_question_templates_menu = KeyboardGenerator.question_templates_menu
create_question_delete_confirm = KeyboardGenerator.question_delete_confirm
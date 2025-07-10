"""
Keyboard generators for Hour Watcher Bot.

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
            [InlineKeyboardButton(translator.translate("menu.settings"), callback_data="menu_settings")],
            [InlineKeyboardButton(translator.translate("menu.friends"), callback_data="menu_friends")],
            [InlineKeyboardButton(translator.translate("menu.history"), callback_data="menu_history")],
        ]
        
        if is_admin:
            keyboard.append([InlineKeyboardButton(translator.translate("menu.admin"), callback_data="menu_admin")])
        
        keyboard.extend([
            [InlineKeyboardButton(translator.translate("menu.language"), callback_data="menu_language")],
            [InlineKeyboardButton(translator.translate("menu.help"), callback_data="menu_help")]
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
        outgoing_count: int = 0
    ) -> InlineKeyboardMarkup:
        """
        Generate friend requests menu keyboard.
        
        Args:
            incoming_count: Number of incoming requests
            outgoing_count: Number of outgoing requests
            
        Returns:
            InlineKeyboardMarkup for friend requests menu
        """
        keyboard = []
        
        # Incoming requests with count
        incoming_text = "📥 Incoming Requests"
        if incoming_count > 0:
            incoming_text += f" ({incoming_count})"
        keyboard.append([InlineKeyboardButton(incoming_text, callback_data="requests_incoming")])
        
        # Outgoing requests with count
        outgoing_text = "📤 Outgoing Requests"
        if outgoing_count > 0:
            outgoing_text += f" ({outgoing_count})"
        keyboard.append([InlineKeyboardButton(outgoing_text, callback_data="requests_outgoing")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Friends", callback_data="back_friends")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def friend_discovery_list(recommendations: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
        """
        Generate friend discovery keyboard.
        
        Args:
            recommendations: List of friend recommendations
            
        Returns:
            InlineKeyboardMarkup for friend discovery
        """
        if not recommendations:
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Friends", callback_data="back_friends")]
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
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Friends", callback_data="back_friends")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def admin_menu() -> InlineKeyboardMarkup:
        """Generate admin menu keyboard."""
        keyboard = [
            [InlineKeyboardButton("📢 Send Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("📊 User Statistics", callback_data="admin_stats")],
            [InlineKeyboardButton("🧪 Test Broadcast", callback_data="admin_test_broadcast")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_main")]
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


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Get admin menu keyboard."""
    return KeyboardGenerator.admin_menu()


# Aliases for new modular architecture
create_main_menu = get_main_menu_keyboard
create_settings_menu = get_settings_keyboard
create_friends_menu = get_friends_keyboard
create_admin_menu = get_admin_keyboard
create_language_menu = KeyboardGenerator.language_menu
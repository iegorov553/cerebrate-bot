"""
Keyboard generators for Hour Watcher Bot.

This module provides dynamic inline keyboard generation for the Telegram bot interface.
"""

from typing import Any, Dict, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


class KeyboardGenerator:
    """Dynamic inline keyboard generator."""
    
    @staticmethod
    def main_menu(is_admin: bool = False) -> InlineKeyboardMarkup:
        """
        Generate main menu keyboard.
        
        Args:
            is_admin: Whether user is admin (shows admin panel)
            
        Returns:
            InlineKeyboardMarkup for main menu
        """
        keyboard = [
            [InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")],
            [InlineKeyboardButton("👥 Friends", callback_data="menu_friends")],
            [InlineKeyboardButton("📊 History", callback_data="menu_history")],
        ]
        
        if is_admin:
            keyboard.append([InlineKeyboardButton("📢 Admin Panel", callback_data="menu_admin")])
        
        keyboard.append([InlineKeyboardButton("❓ Help", callback_data="menu_help")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def settings_menu() -> InlineKeyboardMarkup:
        """Generate settings menu keyboard."""
        keyboard = [
            [InlineKeyboardButton("🔔 Toggle Notifications", callback_data="settings_toggle_notifications")],
            [InlineKeyboardButton("⏰ Set Time Window", callback_data="settings_time_window")],
            [InlineKeyboardButton("📊 Set Frequency", callback_data="settings_frequency")],
            [InlineKeyboardButton("📝 View Current Settings", callback_data="settings_view")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def friends_menu(
        pending_requests: int = 0, 
        friends_count: int = 0
    ) -> InlineKeyboardMarkup:
        """
        Generate friends menu keyboard.
        
        Args:
            pending_requests: Number of pending friend requests
            friends_count: Total number of friends
            
        Returns:
            InlineKeyboardMarkup for friends menu
        """
        keyboard = [
            [InlineKeyboardButton("➕ Add Friend", callback_data="friends_add")],
        ]
        
        # Friend requests with count indicator
        requests_text = "📥 Friend Requests"
        if pending_requests > 0:
            requests_text += f" ({pending_requests})"
        keyboard.append([InlineKeyboardButton(requests_text, callback_data="friends_requests")])
        
        # Friends list with count
        friends_text = "👥 My Friends"
        if friends_count > 0:
            friends_text += f" ({friends_count})"
        keyboard.append([InlineKeyboardButton(friends_text, callback_data="friends_list")])
        
        keyboard.extend([
            [InlineKeyboardButton("🔍 Find Friends", callback_data="friends_discover")],
            [InlineKeyboardButton("📊 Friend Activities", callback_data="friends_activities")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_main")]
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


# Convenience functions for common keyboards

def get_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Get main menu keyboard."""
    return KeyboardGenerator.main_menu(is_admin)


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Get settings menu keyboard."""
    return KeyboardGenerator.settings_menu()


def get_friends_keyboard(pending_requests: int = 0, friends_count: int = 0) -> InlineKeyboardMarkup:
    """Get friends menu keyboard."""
    return KeyboardGenerator.friends_menu(pending_requests, friends_count)


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Get admin menu keyboard."""
    return KeyboardGenerator.admin_menu()
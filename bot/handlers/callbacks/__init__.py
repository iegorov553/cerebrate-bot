"""
Specialized callback handlers package.

Contains handlers for different types of callback queries:
- NavigationCallbackHandler: Main menu, language changes, history
- SettingsCallbackHandler: User settings and preferences (TODO)
- FriendsCallbackHandler: Social features and friend management (TODO)
- AdminCallbackHandler: Administrative functions (TODO)
- QuestionsCallbackHandler: Custom questions management (TODO)
- FeedbackCallbackHandler: User feedback and bug reports (TODO)
"""

# Import completed handlers
from .navigation_callbacks import NavigationCallbackHandler
from .settings_callbacks import SettingsCallbackHandler
from .feedback_callbacks import FeedbackCallbackHandler
from .friends_callbacks import FriendsCallbackHandler
from .admin_callbacks import AdminCallbackHandler
from .questions_callbacks import QuestionsCallbackHandler

__all__ = [
    'NavigationCallbackHandler',
    'SettingsCallbackHandler',
    'FeedbackCallbackHandler',
    'FriendsCallbackHandler',
    'AdminCallbackHandler',
    'QuestionsCallbackHandler',
]
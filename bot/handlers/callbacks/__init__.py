"""
Specialized callback handlers package.

Contains handlers for different types of callback queries:
- NavigationCallbackHandler: Main menu, language changes, history
- FriendsCallbackHandler: Social features and friend management
- AdminCallbackHandler: Administrative functions
- QuestionsCallbackHandler: Custom questions management (includes notification settings)
- FeedbackCallbackHandler: User feedback and bug reports
"""

# Import completed handlers
from .admin_callbacks import AdminCallbackHandler
from .feedback_callbacks import FeedbackCallbackHandler
from .friends_callbacks import FriendsCallbackHandler
from .navigation_callbacks import NavigationCallbackHandler
from .questions_callbacks import QuestionsCallbackHandler

__all__ = [
    "NavigationCallbackHandler",
    "FeedbackCallbackHandler",
    "FriendsCallbackHandler",
    "AdminCallbackHandler",
    "QuestionsCallbackHandler",
]

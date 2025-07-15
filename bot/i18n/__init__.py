"""
Internationalization (i18n) package for Doyobi Diary.

Provides multi-language support with automatic language detection
and fallback mechanisms.
"""

from .language_detector import LanguageDetector, detect_user_language
from .translator import Translator, _, get_translator

__all__ = ["Translator", "get_translator", "_", "LanguageDetector", "detect_user_language"]

"""
Internationalization (i18n) package for Doyobi Diary.

Provides multi-language support with automatic language detection
and fallback mechanisms.
"""

from .translator import Translator, get_translator, _
from .language_detector import LanguageDetector, detect_user_language

__all__ = [
    'Translator',
    'get_translator', 
    '_',
    'LanguageDetector',
    'detect_user_language'
]
"""
Language detection utilities for automatic locale assignment.
"""
from typing import Optional

from telegram import User

from monitoring import get_logger

logger = get_logger(__name__)


class LanguageDetector:
    """Detects user language preferences."""

    SUPPORTED_LANGUAGES = {
        'ru': 'ru',  # Russian
        'en': 'en',  # English  
        'es': 'es',  # Spanish (Spain)
        'es-ES': 'es',
        'es-MX': 'es',  # Mexican Spanish
        'es-AR': 'es',  # Argentine Spanish
        'en-US': 'en',  # American English
        'en-GB': 'en',  # British English
        'en-AU': 'en',  # Australian English
        'ru-RU': 'ru',  # Russian (Russia)
    }

    DEFAULT_LANGUAGE = 'ru'

    @classmethod
    def detect_from_telegram_user(cls, user: User) -> str:
        """
        Detect language from Telegram user object.

        Args:
            user: Telegram user object

        Returns:
            Language code (ru/en/es)
        """
        if not user:
            return cls.DEFAULT_LANGUAGE

        # Try to get language from user.language_code
        user_lang = user.language_code
        if user_lang:
            # Check direct match
            if user_lang in cls.SUPPORTED_LANGUAGES:
                detected = cls.SUPPORTED_LANGUAGES[user_lang]
                logger.debug(f"Language detected from Telegram: {user_lang} -> {detected}")
                return detected

            # Check prefix match (e.g., 'en-US' -> 'en')
            lang_prefix = user_lang.split('-')[0].lower()
            if lang_prefix in cls.SUPPORTED_LANGUAGES:
                detected = cls.SUPPORTED_LANGUAGES[lang_prefix]
                logger.debug(f"Language detected from prefix: {user_lang} -> {detected}")
                return detected

        logger.debug(f"Language not detected, using default: {cls.DEFAULT_LANGUAGE}")
        return cls.DEFAULT_LANGUAGE

    @classmethod
    def detect_from_text(cls, text: str) -> str:
        """
        Detect language from text content (simple heuristic).

        Args:
            text: Text to analyze

        Returns:
            Language code (ru/en/es)
        """
        if not text:
            return cls.DEFAULT_LANGUAGE

        text_lower = text.lower()

        # Simple heuristics for language detection
        russian_indicators = ['привет', 'настройки', 'друзья', 'помощь', 'статистика']
        english_indicators = ['hello', 'settings', 'friends', 'help', 'statistics']
        spanish_indicators = ['hola', 'configuración', 'amigos', 'ayuda', 'estadísticas']

        # Count matches
        ru_score = sum(1 for word in russian_indicators if word in text_lower)
        en_score = sum(1 for word in english_indicators if word in text_lower)
        es_score = sum(1 for word in spanish_indicators if word in text_lower)

        # Return language with highest score
        scores = {'ru': ru_score, 'en': en_score, 'es': es_score}
        detected = max(scores, key=scores.get)

        if scores[detected] > 0:
            logger.debug(f"Language detected from text: {detected} (score: {scores[detected]})")
            return detected

        return cls.DEFAULT_LANGUAGE

    @classmethod
    def is_language_supported(cls, language_code: str) -> bool:
        """
        Check if language is supported.

        Args:
            language_code: Language code to check

        Returns:
            True if supported, False otherwise
        """
        return language_code in ['ru', 'en', 'es']


def detect_user_language(user: User, fallback_text: Optional[str] = None) -> str:
    """
    Convenience function to detect user language.

    Args:
        user: Telegram user object
        fallback_text: Text to analyze if user detection fails

    Returns:
        Language code (ru/en/es)
    """
    # Primary: Telegram user language
    lang = LanguageDetector.detect_from_telegram_user(user)

    # Fallback: Text analysis
    if lang == LanguageDetector.DEFAULT_LANGUAGE and fallback_text:
        lang = LanguageDetector.detect_from_text(fallback_text)

    return lang
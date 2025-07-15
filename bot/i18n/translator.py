"""
Main translation engine for Doyobi Diary.
"""
import json
import os
from typing import Any, Dict, Optional

from monitoring import get_logger

logger = get_logger(__name__)


class Translator:
    """Main translation class with template support and fallbacks."""

    def __init__(self, default_language: str = 'ru'):
        self.default_language = default_language
        self.current_language = default_language
        self._translations: Dict[str, Dict[str, Any]] = {}
        self._load_all_translations()

    def _load_all_translations(self) -> None:
        """Load all translation files."""
        locales_dir = os.path.join(os.path.dirname(__file__), 'locales')

        if not os.path.exists(locales_dir):
            logger.error(f"Locales directory not found: {locales_dir}")
            return

        for filename in os.listdir(locales_dir):
            if filename.endswith('.json'):
                lang_code = filename[:-5]  # Remove .json extension
                file_path = os.path.join(locales_dir, filename)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self._translations[lang_code] = json.load(f)
                    logger.info(f"Loaded translations for language: {lang_code}")
                except Exception as e:
                    logger.error(f"Failed to load translations for {lang_code}: {e}")

    def set_language(self, language_code: str) -> None:
        """
        Set current language.

        Args:
            language_code: Language code (ru/en/es)
        """
        if language_code in self._translations:
            self.current_language = language_code
            logger.debug(f"Language set to: {language_code}")
        else:
            logger.warning(f"Language {language_code} not available, using {self.default_language}")
            self.current_language = self.default_language

    def translate(self, key: str, language: Optional[str] = None, **kwargs) -> str:
        """
        Translate a key to the current or specified language.

        Args:
            key: Translation key (e.g., 'menu.settings')
            language: Override language (optional)
            **kwargs: Template variables for string formatting

        Returns:
            Translated string
        """
        target_lang = language or self.current_language

        # Get translation from target language
        translation = self._get_translation(key, target_lang)

        # Fallback to default language if not found
        if translation is None and target_lang != self.default_language:
            translation = self._get_translation(key, self.default_language)

        # Ultimate fallback to the key itself
        if translation is None:
            logger.warning(f"Translation not found for key: {key}")
            translation = key

        # Apply template variables if provided
        if kwargs and isinstance(translation, str):
            try:
                translation = translation.format(**kwargs)
            except KeyError as e:
                logger.error(f"Template variable missing for key {key}: {e}")
            except Exception as e:
                logger.error(f"Template formatting error for key {key}: {e}")

        return translation

    def _get_translation(self, key: str, language: str) -> Optional[str]:
        """
        Get translation for a specific key and language.

        Args:
            key: Translation key (supports dot notation)
            language: Language code

        Returns:
            Translation string or None if not found
        """
        if language not in self._translations:
            return None

        # Navigate through nested dictionary using dot notation
        current = self._translations[language]

        for part in key.split('.'):
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current if isinstance(current, str) else None

    def get_available_languages(self) -> list:
        """Get list of available language codes."""
        return list(self._translations.keys())

    def get_language_info(self, language_code: str) -> Dict[str, str]:
        """
        Get language information.

        Args:
            language_code: Language code

        Returns:
            Dictionary with language information
        """
        language_names = {
            'ru': {'name': self.translate("language.russian"), 'native': self.translate("language.russian"), 'flag': '🇷🇺'},
            'en': {'name': 'English', 'native': 'English', 'flag': '🇺🇸'},
            'es': {'name': 'Spanish', 'native': 'Español', 'flag': '🇪🇸'}
        }

        return language_names.get(language_code, {
            'name': language_code,
            'native': language_code,
            'flag': '🌐'
        })

    def pluralize(self, key: str, count: int, language: Optional[str] = None, **kwargs) -> str:
        """
        Get pluralized translation based on count.

        Args:
            key: Base translation key
            count: Number for pluralization
            language: Override language (optional)
            **kwargs: Template variables including 'count'

        Returns:
            Pluralized translation
        """
        kwargs['count'] = count
        target_lang = language or self.current_language

        # Try different pluralization keys
        if count == 0:
            plural_key = f"{key}.zero"
        elif count == 1:
            plural_key = f"{key}.one"
        elif count < 5:
            plural_key = f"{key}.few"
        else:
            plural_key = f"{key}.many"

        # Try to find specific plural form
        translation = self._get_translation(plural_key, target_lang)

        # Fallback to base key
        if translation is None:
            translation = self._get_translation(key, target_lang)

        # Apply fallback and formatting
        if translation is None and target_lang != self.default_language:
            return self.pluralize(key, count, self.default_language, **kwargs)

        if translation is None:
            translation = key

        # Apply template variables
        if kwargs and isinstance(translation, str):
            try:
                translation = translation.format(**kwargs)
            except Exception as e:
                logger.error(f"Pluralization formatting error for key {key}: {e}")

        return translation

    # Markdown formatting methods
    def _escape_markdown(self, text: str) -> str:
        """
        Escape special markdown characters.
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text safe for markdown
        """
        if not isinstance(text, str):
            text = str(text)
        return text.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
    
    def bold(self, key: str, language: Optional[str] = None, **kwargs) -> str:
        """
        Translate key and format as bold text.
        
        Args:
            key: Translation key
            language: Override language (optional)
            **kwargs: Template variables
            
        Returns:
            Bold formatted translated text
        """
        text = self.translate(key, language, **kwargs)
        escaped = self._escape_markdown(text)
        return f"**{escaped}**"
    
    def code(self, key: str, language: Optional[str] = None, **kwargs) -> str:
        """
        Translate key and format as code.
        
        Args:
            key: Translation key
            language: Override language (optional)
            **kwargs: Template variables
            
        Returns:
            Code formatted translated text
        """
        text = self.translate(key, language, **kwargs)
        escaped = self._escape_markdown(text)
        return f"`{escaped}`"
    
    def title(self, key: str, emoji: str = "", language: Optional[str] = None, **kwargs) -> str:
        """
        Translate key and format as title with optional emoji.
        
        Args:
            key: Translation key
            emoji: Optional emoji prefix
            language: Override language (optional)
            **kwargs: Template variables
            
        Returns:
            Title formatted translated text
        """
        text = self.translate(key, language, **kwargs)
        escaped = self._escape_markdown(text)
        formatted = f"**{escaped}**"
        if emoji:
            return f"{emoji} {formatted}\n\n"
        return f"{formatted}\n\n"
    
    def field(self, label_key: str, value: str, language: Optional[str] = None, **kwargs) -> str:
        """
        Translate label key and format as field with value.
        
        Args:
            label_key: Translation key for label
            value: Field value
            language: Override language (optional)
            **kwargs: Template variables
            
        Returns:
            Field formatted text
        """
        label = self.translate(label_key, language, **kwargs)
        escaped_label = self._escape_markdown(label)
        escaped_value = self._escape_markdown(str(value))
        return f"**{escaped_label}:** {escaped_value}"
    
    def error(self, key: str, emoji: str = "❌", language: Optional[str] = None, **kwargs) -> str:
        """
        Translate key and format as error message.
        
        Args:
            key: Translation key
            emoji: Error emoji (default: ❌)
            language: Override language (optional)
            **kwargs: Template variables
            
        Returns:
            Error formatted translated text
        """
        text = self.translate(key, language, **kwargs)
        escaped = self._escape_markdown(text)
        return f"{emoji} **{escaped}**"
    
    def success(self, key: str, emoji: str = "✅", language: Optional[str] = None, **kwargs) -> str:
        """
        Translate key and format as success message.
        
        Args:
            key: Translation key
            emoji: Success emoji (default: ✅)
            language: Override language (optional)
            **kwargs: Template variables
            
        Returns:
            Success formatted translated text
        """
        text = self.translate(key, language, **kwargs)
        escaped = self._escape_markdown(text)
        return f"{emoji} **{escaped}**"
    
    def warning(self, key: str, emoji: str = "⚠️", language: Optional[str] = None, **kwargs) -> str:
        """
        Translate key and format as warning message.
        
        Args:
            key: Translation key
            emoji: Warning emoji (default: ⚠️)
            language: Override language (optional)
            **kwargs: Template variables
            
        Returns:
            Warning formatted translated text
        """
        text = self.translate(key, language, **kwargs)
        escaped = self._escape_markdown(text)
        return f"{emoji} **{escaped}**"
    
    def info(self, key: str, emoji: str = "ℹ️", language: Optional[str] = None, **kwargs) -> str:
        """
        Translate key and format as info message.
        
        Args:
            key: Translation key
            emoji: Info emoji (default: ℹ️)
            language: Override language (optional)
            **kwargs: Template variables
            
        Returns:
            Info formatted translated text
        """
        text = self.translate(key, language, **kwargs)
        escaped = self._escape_markdown(text)
        return f"{emoji} **{escaped}**"
    
    def access_denied(self, key: str = 'admin.access_denied', language: Optional[str] = None, **kwargs) -> str:
        """
        Translate key and format as access denied message.
        
        Args:
            key: Translation key (default: admin.access_denied)
            language: Override language (optional)
            **kwargs: Template variables
            
        Returns:
            Access denied formatted translated text
        """
        text = self.translate(key, language, **kwargs)
        escaped = self._escape_markdown(text)
        return f"🔒 **{escaped}**\n\n"
    
    # Format methods for already translated text
    def format_bold(self, text: str) -> str:
        """Format text as bold."""
        escaped = self._escape_markdown(str(text))
        return f"**{escaped}**"
    
    def format_title(self, text: str, emoji: str = "") -> str:
        """Format text as title with optional emoji."""
        escaped = self._escape_markdown(str(text))
        formatted = f"**{escaped}**"
        if emoji:
            return f"{emoji} {formatted}\n\n"
        return f"{formatted}\n\n"
    
    def format_info(self, text: str, emoji: str = "ℹ️") -> str:
        """Format text as info message."""
        escaped = self._escape_markdown(str(text))
        return f"{emoji} {escaped}\n"
    
    def format_code(self, text: str) -> str:
        """Format text as code."""
        escaped = self._escape_markdown(str(text))
        return f"`{escaped}`"


# Global translator instance
_global_translator = Translator()


def get_translator() -> Translator:
    """Get the global translator instance."""
    return _global_translator


def _(key: str, language: Optional[str] = None, **kwargs) -> str:
    """
    Convenience function for translations.

    Args:
        key: Translation key
        language: Override language (optional)
        **kwargs: Template variables

    Returns:
        Translated string
    """
    return _global_translator.translate(key, language, **kwargs)

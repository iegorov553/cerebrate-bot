"""
Main translation engine for Doyobi Diary.
"""
import json
import os
from typing import Any, Dict, Optional, Union

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
            'ru': {'name': 'Русский', 'native': 'Русский', 'flag': '🇷🇺'},
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
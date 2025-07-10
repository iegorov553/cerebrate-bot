"""
Tests for internationalization (i18n) system.
"""
import pytest
from telegram import User

from bot.i18n import LanguageDetector, Translator, detect_user_language, get_translator


class TestLanguageDetector:
    """Test language detection functionality."""
    
    def test_detect_from_telegram_user_russian(self):
        """Test detection of Russian language."""
        user = User(id=123, is_bot=False, first_name="Test", language_code="ru")
        result = LanguageDetector.detect_from_telegram_user(user)
        assert result == "ru"
    
    def test_detect_from_telegram_user_english(self):
        """Test detection of English language."""
        user = User(id=123, is_bot=False, first_name="Test", language_code="en-US")
        result = LanguageDetector.detect_from_telegram_user(user)
        assert result == "en"
    
    def test_detect_from_telegram_user_spanish(self):
        """Test detection of Spanish language."""
        user = User(id=123, is_bot=False, first_name="Test", language_code="es-ES")
        result = LanguageDetector.detect_from_telegram_user(user)
        assert result == "es"
    
    def test_detect_unsupported_language_fallback(self):
        """Test fallback to default for unsupported language."""
        user = User(id=123, is_bot=False, first_name="Test", language_code="fr")
        result = LanguageDetector.detect_from_telegram_user(user)
        assert result == "ru"  # Default fallback
    
    def test_detect_no_language_code(self):
        """Test fallback when no language code provided."""
        user = User(id=123, is_bot=False, first_name="Test")
        result = LanguageDetector.detect_from_telegram_user(user)
        assert result == "ru"  # Default fallback
    
    def test_detect_from_text_russian(self):
        """Test language detection from Russian text."""
        text = "привет настройки"
        result = LanguageDetector.detect_from_text(text)
        assert result == "ru"
    
    def test_detect_from_text_english(self):
        """Test language detection from English text."""
        text = "hello settings"
        result = LanguageDetector.detect_from_text(text)
        assert result == "en"
    
    def test_detect_from_text_spanish(self):
        """Test language detection from Spanish text."""
        text = "hola configuración"
        result = LanguageDetector.detect_from_text(text)
        assert result == "es"
    
    def test_is_language_supported(self):
        """Test language support checking."""
        assert LanguageDetector.is_language_supported("ru") is True
        assert LanguageDetector.is_language_supported("en") is True
        assert LanguageDetector.is_language_supported("es") is True
        assert LanguageDetector.is_language_supported("fr") is False


class TestTranslator:
    """Test translation functionality."""
    
    def test_translator_initialization(self):
        """Test translator initializes correctly."""
        translator = Translator()
        assert translator.default_language == "ru"
        assert translator.current_language == "ru"
    
    def test_set_language(self):
        """Test setting language."""
        translator = Translator()
        translator.set_language("en")
        assert translator.current_language == "en"
    
    def test_translate_basic_key(self):
        """Test basic translation."""
        translator = Translator()
        
        # Test Russian (default)
        result_ru = translator.translate("menu.questions")
        assert "Вопросы" in result_ru
        
        # Test English
        translator.set_language("en")
        result_en = translator.translate("menu.questions")
        assert "Questions" in result_en
        
        # Test Spanish
        translator.set_language("es")
        result_es = translator.translate("menu.questions")
        assert "Preguntas" in result_es
    
    def test_translate_with_template_variables(self):
        """Test translation with template variables."""
        translator = Translator()
        
        result = translator.translate("welcome.greeting", name="John")
        assert "John" in result
        assert "Привет" in result
    
    def test_translate_fallback_to_default(self):
        """Test fallback to default language."""
        translator = Translator()
        translator.set_language("en")
        
        # Try to get a key that might not exist in English
        result = translator.translate("menu.settings")
        assert result is not None
        assert len(result) > 0
    
    def test_translate_nonexistent_key(self):
        """Test handling of non-existent keys."""
        translator = Translator()
        
        result = translator.translate("nonexistent.key")
        assert result == "nonexistent.key"  # Should return the key itself
    
    def test_get_available_languages(self):
        """Test getting available languages."""
        translator = Translator()
        languages = translator.get_available_languages()
        
        assert "ru" in languages
        assert "en" in languages
        assert "es" in languages
    
    def test_get_language_info(self):
        """Test getting language information."""
        translator = Translator()
        
        ru_info = translator.get_language_info("ru")
        assert ru_info["name"] == "Русский"
        assert ru_info["flag"] == "🇷🇺"
        
        en_info = translator.get_language_info("en")
        assert en_info["name"] == "English"
        assert en_info["flag"] == "🇺🇸"
        
        es_info = translator.get_language_info("es")
        assert es_info["name"] == "Spanish"
        assert es_info["flag"] == "🇪🇸"
    
    def test_pluralize_functionality(self):
        """Test pluralization support."""
        translator = Translator()
        
        # Test basic pluralization (fallback to base key)
        result = translator.pluralize("menu.friends", 1)
        assert result is not None
        assert len(result) > 0
        
        result = translator.pluralize("menu.friends", 5)
        assert result is not None
        assert len(result) > 0


class TestGlobalTranslator:
    """Test global translator functions."""
    
    def test_get_global_translator(self):
        """Test getting global translator instance."""
        translator = get_translator()
        assert isinstance(translator, Translator)
    
    def test_convenience_translation_function(self):
        """Test convenience _ function."""
        from bot.i18n import _
        
        result = _("menu.settings")
        assert result is not None
        assert len(result) > 0
    
    def test_detect_user_language_function(self):
        """Test user language detection function."""
        user = User(id=123, is_bot=False, first_name="Test", language_code="en")
        result = detect_user_language(user)
        assert result == "en"


class TestTranslationConsistency:
    """Test consistency across all translations."""
    
    def test_all_languages_have_basic_keys(self):
        """Test that all languages have basic required keys."""
        translator = Translator()
        languages = translator.get_available_languages()
        
        required_keys = [
            "menu.questions",
            "menu.friends", 
            "menu.history",
            "menu.language",
            "welcome.greeting",
            "errors.general"
        ]
        
        for lang in languages:
            translator.set_language(lang)
            for key in required_keys:
                result = translator.translate(key)
                assert result != key, f"Missing translation for {key} in {lang}"
                assert len(result) > 0, f"Empty translation for {key} in {lang}"
    
    def test_template_variables_work_in_all_languages(self):
        """Test that template variables work in all languages."""
        translator = Translator()
        languages = translator.get_available_languages()
        
        for lang in languages:
            translator.set_language(lang)
            result = translator.translate("welcome.greeting", name="Test")
            assert "Test" in result, f"Template variable not working in {lang}"
    
    def test_no_translation_contains_json_artifacts(self):
        """Test that translations don't contain JSON artifacts."""
        translator = Translator()
        languages = translator.get_available_languages()
        
        # Test a few important keys
        test_keys = ["menu.settings", "welcome.greeting", "help.title"]
        
        for lang in languages:
            translator.set_language(lang)
            for key in test_keys:
                result = translator.translate(key)
                assert "{" not in result or "}" not in result or "name" in result, \
                    f"Translation contains JSON artifacts: {key} in {lang} = {result}"
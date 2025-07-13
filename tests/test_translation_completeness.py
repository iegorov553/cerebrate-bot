"""
Test for translation completeness across all language files.

Ensures that all translation keys are present in all supported languages
and that no translations are missing.
"""

import json
import pytest
from pathlib import Path
from typing import Dict, Set, List, Any


class TestTranslationCompleteness:
    """Test translation completeness across all language files."""

    def setup_method(self):
        """Set up test data."""
        self.locales_dir = Path('bot/i18n/locales')
        self.supported_languages = ['ru', 'en', 'es']
        
    def _load_translation_file(self, language: str) -> Dict[str, Any]:
        """Load translation file for given language."""
        file_path = self.locales_dir / f"{language}.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _extract_all_keys(self, data: Dict[str, Any], prefix: str = "") -> Set[str]:
        """Recursively extract all translation keys from nested dictionary."""
        keys = set()
        
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                # Recursive case: nested object
                keys.update(self._extract_all_keys(value, full_key))
            else:
                # Base case: translation string
                keys.add(full_key)
                
        return keys
    
    def _find_missing_keys(self, reference_keys: Set[str], target_keys: Set[str]) -> Set[str]:
        """Find keys that are missing in target compared to reference."""
        return reference_keys - target_keys
    
    def _find_extra_keys(self, reference_keys: Set[str], target_keys: Set[str]) -> Set[str]:
        """Find keys that are extra in target compared to reference."""
        return target_keys - reference_keys

    def test_all_translation_files_exist(self):
        """Test that all required translation files exist."""
        for language in self.supported_languages:
            file_path = self.locales_dir / f"{language}.json"
            assert file_path.exists(), f"Translation file {file_path} does not exist"
            
    def test_all_translation_files_are_valid_json(self):
        """Test that all translation files contain valid JSON."""
        for language in self.supported_languages:
            file_path = self.locales_dir / f"{language}.json"
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"Translation file {file_path} contains invalid JSON: {e}")
    
    def test_translation_key_completeness(self):
        """Test that all languages have the same translation keys."""
        # Load all translation files
        translations = {}
        all_keys = {}
        
        for language in self.supported_languages:
            translations[language] = self._load_translation_file(language)
            all_keys[language] = self._extract_all_keys(translations[language])
        
        # Use Russian as reference (most complete)
        reference_language = 'ru'
        reference_keys = all_keys[reference_language]
        
        # Check each language against reference
        issues = []
        
        for language in self.supported_languages:
            if language == reference_language:
                continue
                
            target_keys = all_keys[language]
            
            # Find missing keys
            missing_keys = self._find_missing_keys(reference_keys, target_keys)
            if missing_keys:
                issues.append(f"\n{language.upper()} is missing {len(missing_keys)} translation keys:")
                for key in sorted(missing_keys):
                    issues.append(f"  - {key}")
            
            # Find extra keys (might indicate typos or inconsistencies)
            extra_keys = self._find_extra_keys(reference_keys, target_keys)
            if extra_keys:
                issues.append(f"\n{language.upper()} has {len(extra_keys)} extra keys not in reference:")
                for key in sorted(extra_keys):
                    issues.append(f"  + {key}")
        
        if issues:
            error_msg = "\n\nTranslation completeness issues found:\n"
            error_msg += "\n".join(issues)
            error_msg += f"\n\nReference language ({reference_language.upper()}) has {len(reference_keys)} keys total."
            error_msg += "\nAll languages should have the same translation keys for consistency."
            pytest.fail(error_msg)
    
    def test_no_empty_translations(self):
        """Test that no translation values are empty or None."""
        issues = []
        
        for language in self.supported_languages:
            translations = self._load_translation_file(language)
            empty_keys = self._find_empty_translations(translations)
            
            if empty_keys:
                issues.append(f"\n{language.upper()} has {len(empty_keys)} empty translations:")
                for key in sorted(empty_keys):
                    issues.append(f"  - {key}")
        
        if issues:
            error_msg = "\n\nEmpty translation values found:\n"
            error_msg += "\n".join(issues)
            error_msg += "\n\nAll translations should have meaningful text content."
            pytest.fail(error_msg)
    
    def _find_empty_translations(self, data: Dict[str, Any], prefix: str = "") -> List[str]:
        """Recursively find empty translation values."""
        empty_keys = []
        
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                # Recursive case: nested object
                empty_keys.extend(self._find_empty_translations(value, full_key))
            else:
                # Base case: check if translation is empty
                if not value or (isinstance(value, str) and not value.strip()):
                    empty_keys.append(full_key)
                    
        return empty_keys
    
    def test_translation_key_naming_consistency(self):
        """Test that translation keys follow naming conventions."""
        issues = []
        
        for language in self.supported_languages:
            translations = self._load_translation_file(language)
            all_keys = self._extract_all_keys(translations)
            
            inconsistent_keys = []
            
            for key in all_keys:
                # Check key naming conventions
                if not self._is_valid_key_name(key):
                    inconsistent_keys.append(key)
            
            if inconsistent_keys:
                issues.append(f"\n{language.upper()} has {len(inconsistent_keys)} keys with naming issues:")
                for key in sorted(inconsistent_keys):
                    issues.append(f"  - {key}")
        
        if issues:
            error_msg = "\n\nTranslation key naming issues found:\n"
            error_msg += "\n".join(issues)
            error_msg += "\n\nKeys should use snake_case and contain only lowercase letters, numbers, dots, and underscores."
            pytest.fail(error_msg)
    
    def _is_valid_key_name(self, key: str) -> bool:
        """Check if translation key follows naming conventions."""
        # Allow lowercase letters, numbers, dots, and underscores
        import re
        pattern = r'^[a-z0-9._]+$'
        return bool(re.match(pattern, key))
    
    def test_placeholder_consistency(self):
        """Test that placeholder variables are consistent across languages."""
        import re
        
        # Load all translations
        translations = {}
        for language in self.supported_languages:
            translations[language] = self._load_translation_file(language)
        
        # Extract all keys from reference language
        reference_keys = self._extract_all_keys(translations['ru'])
        
        issues = []
        
        for key in reference_keys:
            # Get translation values for this key in all languages
            values = {}
            for language in self.supported_languages:
                values[language] = self._get_nested_value(translations[language], key)
            
            # Extract placeholders from each translation
            placeholders = {}
            for language, value in values.items():
                if value and isinstance(value, str):
                    # Find {variable} placeholders
                    found_placeholders = set(re.findall(r'\{(\w+)\}', value))
                    placeholders[language] = found_placeholders
            
            # Check if all languages have the same placeholders
            if len(placeholders) > 1:
                reference_placeholders = placeholders.get('ru', set())
                
                for language, lang_placeholders in placeholders.items():
                    if language == 'ru':
                        continue
                        
                    if lang_placeholders != reference_placeholders:
                        missing = reference_placeholders - lang_placeholders
                        extra = lang_placeholders - reference_placeholders
                        
                        issue_parts = []
                        if missing:
                            issue_parts.append(f"missing: {missing}")
                        if extra:
                            issue_parts.append(f"extra: {extra}")
                            
                        if issue_parts:
                            issues.append(f"  {key} [{language.upper()}]: {', '.join(issue_parts)}")
        
        if issues:
            error_msg = "\n\nPlaceholder inconsistencies found:\n\n"
            error_msg += "\n".join(issues)
            error_msg += "\n\nAll translations of the same key should have identical placeholder variables."
            pytest.fail(error_msg)
    
    def _get_nested_value(self, data: Dict[str, Any], key_path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        keys = key_path.split('.')
        current = data
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return None
    
    def test_translation_quality_basic_checks(self):
        """Basic quality checks for translations."""
        issues = []
        
        for language in self.supported_languages:
            translations = self._load_translation_file(language)
            quality_issues = self._check_translation_quality(translations, language)
            
            if quality_issues:
                issues.extend(quality_issues)
        
        if issues:
            error_msg = "\n\nTranslation quality issues found:\n\n"
            error_msg += "\n".join(issues)
            pytest.fail(error_msg)
    
    def _check_translation_quality(self, data: Dict[str, Any], language: str, prefix: str = "") -> List[str]:
        """Check basic translation quality."""
        issues = []
        
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                # Recursive case
                issues.extend(self._check_translation_quality(value, language, full_key))
            elif isinstance(value, str):
                # Check for potential issues
                if language != 'ru' and self._contains_cyrillic(value):
                    issues.append(f"{language.upper()}: {full_key} contains Cyrillic characters (should be translated)")
                
                if language == 'ru' and self._contains_latin_text(value):
                    # Allow some Latin for commands, URLs, etc.
                    if not self._is_allowed_latin_in_russian(value):
                        issues.append(f"{language.upper()}: {full_key} contains unexpected Latin text")
        
        return issues
    
    def _contains_cyrillic(self, text: str) -> bool:
        """Check if text contains Cyrillic characters."""
        return any('\u0400' <= char <= '\u04FF' for char in text)
    
    def _contains_latin_text(self, text: str) -> bool:
        """Check if text contains significant Latin text."""
        import re
        # Look for Latin words (not just single characters or commands)
        latin_words = re.findall(r'[a-zA-Z]{3,}', text)
        return len(latin_words) > 0
    
    def _is_allowed_latin_in_russian(self, text: str) -> bool:
        """Check if Latin text in Russian translation is allowed."""
        # Allow commands, URLs, technical terms
        allowed_patterns = [
            r'/\w+',          # Commands like /start
            r'https?://',     # URLs
            r'@\w+',          # Usernames
            r'Doyobi',        # App name
            r'Telegram',      # Platform name
            r'Markdown',      # Format name
            r'GitHub',        # Service name
            r'Claude',        # AI name
            r'\{\w+\}',       # Template variables like {name}, {status}
            r'OK|ID|API',     # Common technical abbreviations
        ]
        
        import re
        for pattern in allowed_patterns:
            if re.search(pattern, text):
                return True
                
        # Allow if text is mostly Cyrillic with just small Latin parts
        cyrillic_chars = len(re.findall(r'[\u0400-\u04FF]', text))
        latin_chars = len(re.findall(r'[a-zA-Z]', text))
        
        # If the text has template variables, it's usually OK
        if '{' in text and '}' in text:
            return True
            
        # If Latin is less than 20% of alphabetic characters, it's probably OK
        total_alpha = cyrillic_chars + latin_chars
        if total_alpha > 0 and latin_chars / total_alpha < 0.2:
            return True
            
        return False

    def test_all_used_translation_keys_exist(self):
        """Test that all translation keys used in code actually exist in translation files."""
        import os
        import re
        from pathlib import Path
        
        # Find all translation keys used in code
        used_keys = self._extract_translation_keys_from_code()
        
        # Load all translation dictionaries
        translations = {}
        for language in self.supported_languages:
            translations[language] = self._load_translation_file(language)
        
        # Check each used key exists in all language files
        issues = []
        
        for key in sorted(used_keys):
            # Skip dynamic keys that cannot be validated
            if self._is_dynamic_key(key):
                continue
                
            for language in self.supported_languages:
                if not self._key_exists_in_translations(key, translations[language]):
                    issues.append(f"{language.upper()}: Missing key '{key}'")
        
        if issues:
            error_msg = f"\n\nTranslation keys used in code but missing from dictionaries:\n\n"
            error_msg += "\n".join(issues)
            error_msg += f"\n\nTotal missing keys: {len(issues)}"
            error_msg += f"\nTotal used keys found: {len(used_keys)}"
            error_msg += "\n\nAll keys used in code must exist in ALL language files."
            pytest.fail(error_msg)

    def test_show_all_used_translation_keys(self):
        """Debug test to show all translation keys found in code."""
        used_keys = self._extract_translation_keys_from_code()
        
        print(f"\n\nFound {len(used_keys)} translation keys in code:")
        print("=" * 50)
        
        # Group keys by prefix for better readability
        grouped_keys = {}
        for key in sorted(used_keys):
            if self._is_dynamic_key(key):
                continue
                
            prefix = key.split('.')[0] if '.' in key else 'root'
            if prefix not in grouped_keys:
                grouped_keys[prefix] = []
            grouped_keys[prefix].append(key)
        
        for prefix in sorted(grouped_keys.keys()):
            print(f"\n{prefix.upper()}:")
            for key in grouped_keys[prefix]:
                print(f"  - {key}")
        
        # This test always passes - it's just for debugging
        assert True

    def _extract_translation_keys_from_code(self) -> Set[str]:
        """Extract all translation keys used in Python code."""
        import os
        import re
        from pathlib import Path
        
        used_keys = set()
        bot_dir = Path('bot')
        
        # Patterns to match translation function calls
        patterns = [
            # translator.translate("key") or translator.translate('key')
            r'translator\.translate\(["\']([^"\']+)["\']',
            # get_text("key") or get_text('key') 
            r'get_text\(["\']([^"\']+)["\']',
            # t("key") or t('key')
            r'\bt\(["\']([^"\']+)["\']',
            # _("key") or _('key') - from i18n import
            r'\b_\(["\']([^"\']+)["\']',
        ]
        
        # Walk through all Python files in bot directory
        for file_path in bot_dir.rglob('*.py'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Extract keys from each pattern
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        # Clean up the key (remove any extra quotes or whitespace)
                        key = match.strip().strip('\'"')
                        if key and not self._is_excluded_key(key):
                            used_keys.add(key)
                            
            except Exception as e:
                # Log error but continue processing other files
                print(f"Warning: Could not process file {file_path}: {e}")
                continue
        
        return used_keys

    def _is_dynamic_key(self, key: str) -> bool:
        """Check if a key appears to be dynamically generated and cannot be validated."""
        # Keys with variables, f-strings, concatenations
        dynamic_indicators = [
            '{', '}',           # f-string variables
            '+',                # String concatenation
            'format(',          # String formatting
            '%s', '%d',         # String formatting
            '${',               # Template variables
        ]
        
        for indicator in dynamic_indicators:
            if indicator in key:
                return True
                
        # Very short keys are likely incomplete/dynamic
        if len(key) < 3:
            return True
            
        return False

    def _is_excluded_key(self, key: str) -> bool:
        """Check if a key should be excluded from validation."""
        # Exclude obviously non-translation keys
        excluded_patterns = [
            r'^https?://',      # URLs
            r'^/\w+',          # Commands
            r'^\w+\(\)',       # Function calls
            r'^\d+$',          # Numbers only
            r'^[A-Z_]+$',      # Constants
        ]
        
        import re
        for pattern in excluded_patterns:
            if re.match(pattern, key):
                return True
                
        return False

    def _key_exists_in_translations(self, key: str, translations: Dict[str, Any]) -> bool:
        """Check if a key exists in the translations dictionary using dot notation."""
        try:
            # Navigate through nested dictionary using dot notation
            current = translations
            
            for part in key.split('.'):
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return False
            
            # Key exists if we found a string value
            return isinstance(current, str) and current.strip() != ""
            
        except Exception:
            return False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
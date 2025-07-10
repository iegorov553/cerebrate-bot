# 🌍 Internationalization (i18n) Guide

## Overview

Doyobi Diary supports multiple languages through a comprehensive i18n system with automatic detection and user preferences.

## Supported Languages

- 🇷🇺 **Russian** (`ru`) - Default language, full coverage
- 🇺🇸 **English** (`en`) - Complete translations
- 🇪🇸 **Spanish** (`es`) - Complete translations

## Architecture

### Directory Structure
```
bot/i18n/
├── __init__.py                 # Public exports
├── translator.py               # Main translation engine
├── language_detector.py        # Auto language detection
└── locales/
    ├── ru.json                # Russian translations
    ├── en.json                # English translations
    └── es.json                # Spanish translations
```

### Key Classes

#### `Translator`
Main translation engine with template support and fallbacks.

#### `LanguageDetector`
Automatic language detection from Telegram user settings.

## Usage

### Basic Translation

```python
from bot.i18n import get_translator, _

# Get global translator instance
translator = get_translator()

# Set language
translator.set_language('en')

# Translate
text = translator.translate('menu.settings')  # "⚙️ Settings"

# Convenience function
text = _('menu.settings')  # Uses current language
```

### Template Variables

```python
# Translation with variables
greeting = translator.translate('welcome.greeting', name='John')
# Result: "👋 Hello, John!" (English)
# Result: "👋 Привет, John!" (Russian)
# Result: "👋 ¡Hola, John!" (Spanish)
```

### Language Detection

```python
from bot.i18n import detect_user_language

# Auto-detect from Telegram user
user_language = detect_user_language(user)  # en-US → en

# Setup translator with detected language
translator.set_language(user_language)
```

### In Handlers

```python
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Detect and set language
    user_language = detect_user_language(user)
    translator = get_translator()
    translator.set_language(user_language)
    
    # Use translations
    welcome_text = translator.translate('welcome.greeting', name=user.first_name)
    
    await update.message.reply_text(welcome_text)
```

## Translation Files

### Structure
Each language file is a JSON with nested keys:

```json
{
  "menu": {
    "settings": "⚙️ Settings",
    "friends": "👥 Friends"
  },
  "welcome": {
    "greeting": "👋 Hello, {name}!"
  },
  "errors": {
    "general": "❌ An error occurred. Please try again."
  }
}
```

### Key Naming Convention
- Use dot notation: `menu.settings`, `welcome.greeting`
- Categories: `menu`, `welcome`, `settings`, `friends`, `errors`, `help`
- Clear, descriptive names
- Consistent across all languages

### Template Variables
- Use `{variable_name}` format
- Common variables: `{name}`, `{username}`, `{count}`, `{status}`
- Document required variables in comments

## Adding New Language

### 1. Create Translation File
Create `bot/i18n/locales/[lang_code].json` with all required translations.

### 2. Update Language Detector
Add language code to `SUPPORTED_LANGUAGES` in `language_detector.py`:

```python
SUPPORTED_LANGUAGES = {
    'ru': 'ru',
    'en': 'en', 
    'es': 'es',
    'fr': 'fr',  # New language
    # ...
}
```

### 3. Update Language Info
Add language info in `translator.py`:

```python
language_names = {
    'ru': {'name': 'Русский', 'native': 'Русский', 'flag': '🇷🇺'},
    'en': {'name': 'English', 'native': 'English', 'flag': '🇺🇸'},
    'es': {'name': 'Spanish', 'native': 'Español', 'flag': '🇪🇸'},
    'fr': {'name': 'French', 'native': 'Français', 'flag': '🇫🇷'}  # New
}
```

### 4. Update Keyboard Generators
Add button to language menu in `keyboard_generators.py`:

```python
keyboard = [
    [InlineKeyboardButton("🇷🇺 Русский" + (" ✓" if current_language == 'ru' else ""), 
                         callback_data="language_ru")],
    [InlineKeyboardButton("🇺🇸 English" + (" ✓" if current_language == 'en' else ""), 
                         callback_data="language_en")],
    [InlineKeyboardButton("🇪🇸 Español" + (" ✓" if current_language == 'es' else ""), 
                         callback_data="language_es")],
    [InlineKeyboardButton("🇫🇷 Français" + (" ✓" if current_language == 'fr' else ""), 
                         callback_data="language_fr")]  # New
]
```

### 5. Update Database Schema
Add new language to CHECK constraint:

```sql
ALTER TABLE users 
ALTER COLUMN language 
SET CHECK (language IN ('ru', 'en', 'es', 'fr'));
```

### 6. Update Callback Handler
Add handling for new language in `callback_handlers.py`:

```python
if new_language not in ['ru', 'en', 'es', 'fr']:  # Add new language
    return
```

## Translation Guidelines

### 1. Consistency
- Use consistent terminology across all strings
- Maintain the same tone and style
- Keep formatting (emojis, markdown) consistent

### 2. Context
- Consider UI context when translating
- Button text should be concise
- Error messages should be helpful

### 3. Cultural Adaptation
- Use appropriate greetings for culture
- Consider cultural differences in communication style
- Use proper date/time formats for region

### 4. Technical Considerations
- Preserve placeholders: `{name}`, `{count}`
- Maintain markdown formatting: `**bold**`, `*italic*`
- Keep emoji usage appropriate for culture

## Testing

### Run i18n Tests
```bash
pytest tests/test_i18n.py -v
```

### Test Coverage
- Language detection logic
- Translation fallbacks
- Template variable substitution
- Consistency across languages
- Missing translation handling

### Manual Testing
1. Set different Telegram language codes
2. Test language switching via UI
3. Verify all menus show correctly
4. Check template variables work
5. Test fallback behavior

## Common Issues

### 1. Missing Translations
**Problem**: Key exists in one language but not others
**Solution**: Run consistency tests, ensure all keys exist in all files

### 2. Template Variable Errors
**Problem**: `KeyError` when using variables
**Solution**: Check variable names match exactly, including case

### 3. Fallback Not Working
**Problem**: Shows key instead of translation
**Solution**: Verify default language (ru) has the translation

### 4. Encoding Issues
**Problem**: Special characters display incorrectly
**Solution**: Ensure all JSON files use UTF-8 encoding

## Best Practices

### 1. Development
- Always test with multiple languages
- Use convenience function `_()` for simple translations
- Set language early in handlers
- Handle language detection gracefully

### 2. Maintenance
- Keep translation files in sync
- Use version control for translation changes
- Document any cultural-specific adaptations
- Regular consistency checks

### 3. Performance
- Translations are loaded once at startup
- Use caching for user language preferences
- Minimize database queries for language settings

### 4. User Experience
- Auto-detect language when possible
- Provide clear language switching interface
- Save user preference persistently
- Give immediate feedback on language change

## API Reference

### `get_translator()`
Returns the global translator instance.

### `detect_user_language(user, fallback_text=None)`
Detects user language from Telegram user object.

### `Translator.translate(key, language=None, **kwargs)`
Translates a key with optional template variables.

### `Translator.set_language(language_code)`
Sets the current language for the translator.

### `Translator.get_available_languages()`
Returns list of available language codes.

### `Translator.get_language_info(language_code)`
Returns language information (name, native name, flag).

## Future Enhancements

### Potential Additions
- Right-to-left (RTL) language support
- Pluralization rules for complex languages
- Context-aware translations
- Professional translation management
- Automated translation updates
- Regional dialect support

### Integration Ideas
- Translation management platforms
- Crowdsourced translations
- Professional translation services
- Automated translation validation
- Analytics on language usage
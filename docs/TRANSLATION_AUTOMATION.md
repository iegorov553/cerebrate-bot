# 🌍 Translation Automation System

Comprehensive automation system for managing multilingual translations in Doyobi Diary bot.

## 🎯 Overview

This system ensures:
- **Complete translations** across all supported languages (RU, EN, ES)
- **Quality control** with automated validation
- **Merge protection** to prevent incomplete translations reaching production
- **Automatic synchronization** when new translation keys are added

## 🏗️ Architecture

### Components

```
Translation Automation System
├── 🔍 Validation Tests
│   ├── test_translation_completeness.py  # Key completeness, placeholders, quality
│   └── test_markdown_validation.py       # Markdown syntax safety
├── 🔄 Synchronization
│   └── sync_translations.py              # Auto-sync structure across languages
├── 🚫 CI/CD Protection
│   ├── translation-validation.yml        # Comprehensive validation workflow
│   ├── auto-sync-translations.yml        # Auto-sync on reference changes
│   └── branch-protection.yml             # Merge blocking for incomplete translations
├── 🪝 Local Hooks
│   └── .pre-commit-config.yaml           # Pre-commit validation hooks
└── 🛠️ Setup Tools
    └── setup-translation-automation.sh   # One-click setup script
```

## 🚀 Quick Start

### 1. Initial Setup

```bash
# Run the setup script
./setup-translation-automation.sh

# Or manually:
pip install pre-commit
pre-commit install
python sync_translations.py
```

### 2. Daily Development Workflow

```bash
# 1. Make changes to code or translations
git add .

# 2. Commit (hooks run automatically)
git commit -m "Add new feature"

# 3. Push to staging
git push origin staging

# 4. Create PR to main (CI/CD validates)
gh pr create --title "New feature" --base main
```

## 📋 Translation Workflow

### Adding New Translation Keys

1. **Add to Russian file** (reference language):
   ```json
   // bot/i18n/locales/ru.json
   {
     "new_feature": {
       "title": "🎉 Новая функция",
       "description": "Описание новой функции"
     }
   }
   ```

2. **Auto-sync triggers** (on push to staging):
   - Detects new keys in Russian file
   - Adds placeholders to EN/ES files:
     ```json
     {
       "new_feature": {
         "title": "[TO_TRANSLATE] 🎉 Новая функция",
         "description": "[TO_TRANSLATE] Описание новой функции"
       }
     }
     ```

3. **Translate placeholders**:
   ```json
   // bot/i18n/locales/en.json
   {
     "new_feature": {
       "title": "🎉 New Feature",
       "description": "New feature description"
     }
   }
   ```

4. **Validation ensures quality**:
   - All languages have same keys
   - No `[TO_TRANSLATE]` placeholders remain
   - Markdown syntax is correct
   - Placeholder variables are consistent

## 🔍 Validation System

### Translation Completeness Test

```python
# tests/test_translation_completeness.py
class TestTranslationCompleteness:
    def test_translation_key_completeness(self):
        """Ensures all languages have identical key structure"""
        
    def test_no_empty_translations(self):
        """Prevents empty translation values"""
        
    def test_placeholder_consistency(self):
        """Validates {name}, {count} variables match across languages"""
        
    def test_translation_quality_basic_checks(self):
        """Detects language mixing and untranslated content"""
```

### Markdown Validation Test

```python
# tests/test_markdown_validation.py
class TestMarkdownValidation:
    def test_markdown_entities_in_translation_files(self):
        """Prevents unbalanced **, __, `` in translations"""
        
    def test_markdown_f_string_safety(self):
        """Ensures f-strings don't contain user-controlled markdown"""
        
    def test_telegram_markdown_v2_compatibility(self):
        """Validates special character escaping for Telegram"""
```

## 🚫 Branch Protection System

### Main Branch Protection

```yaml
# .github/workflows/branch-protection.yml
jobs:
  translation-quality-gate:
    steps:
      - name: 🚫 Block merge if [TO_TRANSLATE] placeholders exist
        # Scans all translation files
        # Blocks PR if any placeholders found
        # Provides clear instructions for resolution
```

### Quality Gates

1. **❌ BLOCKING**: `[TO_TRANSLATE]` placeholders exist
2. **❌ BLOCKING**: Translation keys missing between languages  
3. **❌ BLOCKING**: Critical Markdown syntax errors
4. **⚠️ WARNING**: Minor Markdown issues
5. **⚠️ WARNING**: Hardcoded text in code (refactoring in progress)

## 🔄 Auto-Sync System

### Trigger Conditions

- **Push to staging** with changes to `bot/i18n/locales/ru.json`
- **Manual dispatch** via GitHub Actions
- **Pre-commit hook** when Russian file is modified locally

### Sync Process

```python
# sync_translations.py
def sync_structure(reference: Dict, target: Dict) -> Dict:
    """
    1. Compare reference (RU) with target (EN/ES)
    2. Keep existing translations unchanged
    3. Add [TO_TRANSLATE] placeholders for missing keys
    4. Preserve nested structure and ordering
    """
```

### Auto-Issue Creation

When placeholders are added, system automatically:
- Creates GitHub issue with translation details
- Labels with `translations`, `auto-generated`, `help wanted`
- Provides clear instructions for contributors
- Links to affected files and example translations

## 🪝 Pre-Commit Hooks

### Local Validation Pipeline

```yaml
# .pre-commit-config.yaml
hooks:
  - id: sync-translations          # Auto-sync on RU file changes
  - id: check-translation-placeholders  # Block commit if placeholders exist
  - id: translation-completeness   # Validate structure completeness
  - id: translation-markdown       # Validate Markdown syntax
  - id: check-hardcoded-text       # Warn about hardcoded text
  - id: bandit-security-check      # Security scan
```

### Hook Behavior

- **🚫 BLOCKING**: Placeholders in translation files
- **🚫 BLOCKING**: Translation structure inconsistencies
- **🚫 BLOCKING**: Critical Markdown errors
- **⚠️ WARNING**: Code style, security, hardcoded text issues

## 📊 Monitoring & Reporting

### GitHub Actions Summary

Each workflow run provides:

```markdown
## 🌍 Translation Coverage Report

- ✅ **RU**: 163/163 (100.0%) completed
- ⚠️ **EN**: 92/163 (56.4%) - 71 translations pending  
- ⚠️ **ES**: 92/163 (56.4%) - 71 translations pending

❌ **Action required**: Complete translations before merging to main branch
```

### Quality Metrics

- **Translation completion rate** per language
- **Placeholder count** and specific locations
- **Markdown validation** results with specific issues
- **Code quality** metrics (linting, security, tests)

## 🛠️ Commands Reference

### Development Commands

```bash
# Sync translation structure
python sync_translations.py

# Run translation tests
pytest tests/test_translation_completeness.py -v
pytest tests/test_markdown_validation.py -v

# Check for placeholders
grep -r "\[TO_TRANSLATE\]" bot/i18n/locales/

# Run all pre-commit hooks
pre-commit run --all-files

# Setup automation (first time)
./setup-translation-automation.sh
```

### CI/CD Commands

```bash
# Trigger auto-sync manually
gh workflow run auto-sync-translations.yml

# Check workflow status
gh run list --workflow=translation-validation.yml

# View specific run details
gh run view <run-id>
```

## 📈 Benefits

### For Developers

- **No more crashes** from missing translation keys
- **Automatic synchronization** prevents manual errors
- **Clear feedback** on what needs translation
- **Pre-commit protection** catches issues early

### For Translators

- **Structured workflow** with clear placeholders
- **Quality validation** prevents syntax errors
- **Automatic issue creation** for new work
- **Progress tracking** via GitHub integration

### for DevOps

- **Merge protection** ensures production quality
- **Automated workflows** reduce manual oversight
- **Quality metrics** provide visibility
- **Security scanning** integrated into pipeline

## 🔧 Configuration

### Supported Languages

Currently configured for:
- **Russian (RU)**: Reference language, complete translations
- **English (EN)**: Primary international language
- **Spanish (ES)**: Secondary international language

### Adding New Languages

1. Create new locale file: `bot/i18n/locales/fr.json`
2. Update `sync_translations.py` supported languages list
3. Update test configurations
4. Run sync to populate placeholders

### Customizing Validation

Modify test parameters in:
- `tests/test_translation_completeness.py`
- `tests/test_markdown_validation.py`
- `.pre-commit-config.yaml`
- `.github/workflows/*.yml`

## 🚨 Troubleshooting

### Common Issues

**Issue**: Pre-commit hooks fail with import errors
```bash
# Solution: Install test dependencies
pip install -r requirements.txt
pip install pytest pytest-mock
```

**Issue**: Translation sync doesn't run automatically
```bash
# Solution: Check GitHub Actions permissions
# Ensure GITHUB_TOKEN has write permissions
```

**Issue**: Merge blocked despite complete translations
```bash
# Solution: Check for hidden placeholders
grep -r "\[TO_TRANSLATE\]" bot/i18n/locales/ --include="*.json"
```

### Debug Commands

```bash
# Validate individual language file
python -c "
import json
with open('bot/i18n/locales/en.json', 'r') as f:
    data = json.load(f)
    print('✅ Valid JSON')
"

# Count placeholders by file
for file in bot/i18n/locales/*.json; do
  count=$(grep -c "\[TO_TRANSLATE\]" "$file" 2>/dev/null || echo "0")
  echo "$file: $count placeholders"
done

# Test specific validation
pytest tests/test_translation_completeness.py::TestTranslationCompleteness::test_translation_key_completeness -v
```

## 📚 Related Documentation

- **[I18N_GUIDE.md](I18N_GUIDE.md)**: Translation system architecture
- **[TESTING.md](TESTING.md)**: Testing strategy and execution
- **[DEPLOYMENT.md](DEPLOYMENT.md)**: Production deployment process
- **[REFACTORING_PLAN.md](../REFACTORING_PLAN.md)**: Ongoing code improvements

---

**Maintained by**: Doyobi Diary Development Team  
**Last Updated**: 2025-07-14  
**Version**: 2.1.41
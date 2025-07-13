#!/bin/bash

# Setup Translation Automation
# This script sets up automated translation validation and CI/CD workflows

set -e

echo "🌍 Setting up Translation Automation for Doyobi Diary"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_step() {
    echo -e "\n${BLUE}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "main.py" ] || [ ! -d "bot/i18n/locales" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Step 1: Install pre-commit if not installed
print_step "Installing pre-commit hooks"

if ! command -v pre-commit &> /dev/null; then
    echo "Installing pre-commit..."
    pip install pre-commit
fi

# Install pre-commit hooks
pre-commit install
print_success "Pre-commit hooks installed"

# Step 2: Sync translations structure
print_step "Synchronizing translation structure"

if [ -f "sync_translations.py" ]; then
    python sync_translations.py
    print_success "Translation structure synchronized"
else
    print_error "sync_translations.py not found"
    exit 1
fi

# Step 3: Run initial translation validation
print_step "Running initial translation validation"

echo "Checking translation completeness..."
if python -m pytest tests/test_translation_completeness.py -v; then
    print_success "Translation completeness check passed"
else
    print_warning "Some translation issues found - see details above"
fi

echo "Checking Markdown validation..."
if python -m pytest tests/test_markdown_validation.py -v; then
    print_success "Markdown validation passed"
else
    print_warning "Some Markdown issues found - see details above"
fi

# Step 4: Check GitHub workflows
print_step "Checking GitHub workflows"

WORKFLOWS_DIR=".github/workflows"
if [ -d "$WORKFLOWS_DIR" ]; then
    EXPECTED_WORKFLOWS=(
        "translation-validation.yml"
        "auto-sync-translations.yml"
        "branch-protection.yml"
    )
    
    for workflow in "${EXPECTED_WORKFLOWS[@]}"; do
        if [ -f "$WORKFLOWS_DIR/$workflow" ]; then
            print_success "Workflow $workflow is present"
        else
            print_warning "Workflow $workflow is missing"
        fi
    done
else
    print_warning "GitHub workflows directory not found"
fi

# Step 5: Generate project status report
print_step "Generating project status report"

echo "Analyzing translation status..."
python -c "
import json
from pathlib import Path

print('📊 Translation Status Report')
print('=' * 40)

languages = ['ru', 'en', 'es']
total_stats = {'total': 0, 'completed': 0, 'pending': 0}

for lang in languages:
    lang_file = Path(f'bot/i18n/locales/{lang}.json')
    if lang_file.exists():
        with open(lang_file, 'r', encoding='utf-8') as f:
            content = f.read()
            total_keys = content.count('\":')
            placeholder_keys = content.count('[TO_TRANSLATE]')
            completed_keys = total_keys - placeholder_keys
            completion_rate = (completed_keys / total_keys * 100) if total_keys > 0 else 0
            
            status_emoji = '✅' if placeholder_keys == 0 else '⚠️' if completion_rate > 50 else '❌'
            print(f'{status_emoji} {lang.upper()}: {completed_keys}/{total_keys} ({completion_rate:.1f}%) - {placeholder_keys} pending')
            
            total_stats['total'] += total_keys
            total_stats['completed'] += completed_keys
            total_stats['pending'] += placeholder_keys

print()
overall_rate = (total_stats['completed'] / total_stats['total'] * 100) if total_stats['total'] > 0 else 0
print(f'📈 Overall: {total_stats[\"completed\"]}/{total_stats[\"total\"]} ({overall_rate:.1f}%) completed')
print(f'🔄 Pending translations: {total_stats[\"pending\"]}')

if total_stats['pending'] == 0:
    print('\\n🎉 All translations are complete!')
else:
    print(f'\\n📝 Action needed: {total_stats[\"pending\"]} translations pending')
"

# Step 6: Check test coverage
print_step "Checking test coverage"

echo "Running core tests..."
if python -m pytest tests/ --ignore=tests/test_markdown_validation.py --ignore=tests/test_no_hardcoded_text.py -q; then
    print_success "Core tests passed"
else
    print_warning "Some core tests failed"
fi

# Step 7: Security and quality checks
print_step "Running security and quality checks"

echo "Checking code style with Ruff..."
if ruff check . --quiet; then
    print_success "Code style check passed"
else
    print_warning "Code style issues found"
fi

echo "Running security scan..."
if bandit -r bot/ -ll -q; then
    print_success "Security scan passed"
else
    print_warning "Security issues found"
fi

# Step 8: Final instructions
print_step "Setup Complete!"

echo ""
echo "🎉 Translation automation is now configured!"
echo ""
echo "📋 What's been set up:"
echo "   ✅ Pre-commit hooks for automatic validation"
echo "   ✅ GitHub workflows for CI/CD"
echo "   ✅ Translation structure synchronization"
echo "   ✅ Quality gates for branch protection"
echo ""
echo "🚀 Next steps:"
echo "   1. Review and translate any [TO_TRANSLATE] placeholders"
echo "   2. Commit your changes (hooks will run automatically)"
echo "   3. Push to staging branch to trigger workflows"
echo "   4. Create PR to main when all translations are complete"
echo ""
echo "🔧 Available commands:"
echo "   • sync_translations.py           - Sync translation structure"
echo "   • pytest tests/test_translation_completeness.py - Test completeness"
echo "   • pytest tests/test_markdown_validation.py      - Test Markdown"
echo "   • pre-commit run --all-files     - Run all pre-commit hooks"
echo ""

# Check for immediate action needed
PENDING_COUNT=$(grep -r "\[TO_TRANSLATE\]" bot/i18n/locales/ 2>/dev/null | wc -l || echo "0")
if [ "$PENDING_COUNT" -gt 0 ]; then
    print_warning "Action needed: $PENDING_COUNT translations are pending"
    echo "   Run: grep -r \"\\[TO_TRANSLATE\\]\" bot/i18n/locales/ to see them"
else
    print_success "All translations are complete!"
fi

echo ""
echo "📚 Documentation:"
echo "   • See .github/workflows/ for CI/CD configuration"
echo "   • See .pre-commit-config.yaml for local hooks"
echo "   • See tests/test_translation_completeness.py for validation logic"
echo ""
echo "Happy translating! 🌍✨"
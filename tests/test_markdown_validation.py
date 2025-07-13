"""Tests for Markdown validation to prevent parsing errors."""

import re
import json
from pathlib import Path
from typing import List, Tuple, Dict, Any

import pytest


class TestMarkdownValidation:
    """Test suite for validating Markdown syntax in the project."""
    
    def test_markdown_entities_in_translation_files(self):
        """Test that translation files don't contain conflicting Markdown entities."""
        violations = []
        
        # Check all translation files
        locale_dir = Path('bot/i18n/locales')
        for locale_file in locale_dir.glob('*.json'):
            try:
                with open(locale_file, 'r', encoding='utf-8') as f:
                    translations = json.load(f)
                    
                violations.extend(self._check_translations_recursive(
                    translations, locale_file.name, ""
                ))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                violations.append({
                    'file': str(locale_file),
                    'error': f"Failed to parse JSON: {e}",
                    'type': 'parse_error'
                })
        
        if violations:
            self._report_markdown_violations(violations)
    
    def test_markdown_entities_in_code_files(self):
        """Test that code files don't contain problematic Markdown patterns."""
        violations = []
        
        # Patterns to check in code files
        code_patterns = [
            'bot/handlers/**/*.py',
            'bot/keyboards/**/*.py',
            'bot/admin/**/*.py',
            'bot/feedback/**/*.py'
        ]
        
        for pattern in code_patterns:
            for file_path in Path('.').glob(pattern):
                if file_path.is_file():
                    violations.extend(self._check_markdown_in_code_file(file_path))
        
        if violations:
            self._report_code_markdown_violations(violations)
    
    def test_markdown_f_string_safety(self):
        """Test that f-strings with Markdown don't have unsafe variable interpolation."""
        violations = []
        
        code_patterns = [
            'bot/handlers/**/*.py',
            'bot/keyboards/**/*.py'
        ]
        
        for pattern in code_patterns:
            for file_path in Path('.').glob(pattern):
                if file_path.is_file():
                    violations.extend(self._check_f_string_markdown_safety(file_path))
        
        if violations:
            self._report_f_string_violations(violations)
    
    def _check_translations_recursive(self, data: Any, filename: str, path: str) -> List[Dict]:
        """Recursively check translations for Markdown issues."""
        violations = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                violations.extend(self._check_translations_recursive(
                    value, filename, current_path
                ))
        elif isinstance(data, str):
            violations.extend(self._validate_markdown_string(data, filename, path))
            
        return violations
    
    def _validate_markdown_string(self, text: str, filename: str, path: str) -> List[Dict]:
        """Validate a single string for Markdown issues."""
        violations = []
        
        # Check for unbalanced markdown entities
        markdown_patterns = [
            (r'\*\*', 'bold'),  # **bold**
            (r'__', 'bold_underscore'),  # __bold__
            (r'(?<!\*)\*(?!\*)', 'italic'),  # *italic* (not part of **)
            (r'(?<!_)_(?!_)', 'italic_underscore'),  # _italic_ (not part of __)
            (r'`', 'code'),  # `code`
            (r'```', 'code_block'),  # ```code block```
            (r'\[.*?\]\(.*?\)', 'link'),  # [text](url)
        ]
        
        for pattern, entity_type in markdown_patterns:
            matches = re.findall(pattern, text)
            
            # For paired entities, check if count is even
            if entity_type in ['bold', 'bold_underscore', 'italic', 'italic_underscore', 'code']:
                if len(matches) % 2 != 0:
                    violations.append({
                        'file': filename,
                        'path': path,
                        'text': text,
                        'issue': f"Unbalanced {entity_type} markdown entities",
                        'pattern': pattern,
                        'count': len(matches)
                    })
            
            # Special check for code blocks (should be even number of ```)
            elif entity_type == 'code_block':
                if len(matches) % 2 != 0:
                    violations.append({
                        'file': filename,
                        'path': path,
                        'text': text,
                        'issue': "Unbalanced code block markdown entities",
                        'pattern': pattern,
                        'count': len(matches)
                    })
        
        # Check for problematic patterns that can break Telegram parsing
        problematic_patterns = [
            (r'\*\*.*?\{.*?\}.*?\*\*', 'Variable inside bold markdown'),
            (r'__.*?\{.*?\}.*?__', 'Variable inside bold underscore markdown'),
            (r'\*.*?\{.*?\}.*?\*', 'Variable inside italic markdown'),
            (r'_.*?\{.*?\}_', 'Variable inside italic underscore markdown'),
            (r'`.*?\{.*?\}.*?`', 'Variable inside code markdown'),
            (r'\[.*?\{.*?\}.*?\]', 'Variable inside link text'),
        ]
        
        for pattern, description in problematic_patterns:
            if re.search(pattern, text):
                violations.append({
                    'file': filename,
                    'path': path,
                    'text': text,
                    'issue': description,
                    'pattern': pattern,
                    'recommendation': 'Move Markdown formatting to code, not translations'
                })
        
        return violations
    
    def _check_markdown_in_code_file(self, file_path: Path) -> List[Dict]:
        """Check code files for problematic Markdown patterns."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    # Skip comments and docstrings
                    if line.strip().startswith('#') or '"""' in line or "'''" in line:
                        continue
                    
                    # Check for hardcoded Markdown with variables
                    problematic_patterns = [
                        (r'f".*?\*\*.*?\{.*?\}.*?\*\*.*?"', 'f-string with bold markdown around variables'),
                        (r"f'.*?\*\*.*?\{.*?\}.*?\*\*.*?'", 'f-string with bold markdown around variables'),
                        (r'f".*?`.*?\{.*?\}.*?`.*?"', 'f-string with code markdown around variables'),
                        (r"f'.*?`.*?\{.*?\}.*?`.*?'", 'f-string with code markdown around variables'),
                        (r'".*?\*\*.*?\*\*.*?".*?\.format', 'String format with bold markdown'),
                        (r"'.*?\*\*.*?\*\*.*?'.*?\.format", 'String format with bold markdown'),
                    ]
                    
                    for pattern, description in problematic_patterns:
                        if re.search(pattern, line):
                            violations.append({
                                'file': str(file_path),
                                'line': line_num,
                                'content': line.strip(),
                                'issue': description,
                                'pattern': pattern,
                                'recommendation': 'Use separate Markdown formatting in code'
                            })
        
        except UnicodeDecodeError:
            # Skip binary files
            pass
        
        return violations
    
    def _check_f_string_markdown_safety(self, file_path: Path) -> List[Dict]:
        """Check f-strings for safe Markdown usage."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Find f-strings with Markdown
                f_string_patterns = [
                    r'f"[^"]*?\*\*[^"]*?"',  # f"...**..."
                    r"f'[^']*?\*\*[^']*?'",  # f'...**...'
                    r'f"[^"]*?`[^"]*?"',     # f"...`..."
                    r"f'[^']*?`[^']*?'",     # f'...`...'
                ]
                
                for pattern in f_string_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        # Count line number
                        line_num = content[:match.start()].count('\n') + 1
                        
                        # Check if the f-string looks problematic
                        f_string = match.group()
                        if '{' in f_string and ('**' in f_string or '`' in f_string):
                            violations.append({
                                'file': str(file_path),
                                'line': line_num,
                                'content': f_string,
                                'issue': 'Potentially unsafe Markdown in f-string',
                                'recommendation': 'Consider using separate formatting or escaping'
                            })
        
        except UnicodeDecodeError:
            pass
        
        return violations
    
    def _report_markdown_violations(self, violations: List[Dict]):
        """Report translation file Markdown violations."""
        error_msg = "\n\nMarkdown validation errors in translation files:\n\n"
        
        for violation in violations:
            error_msg += f"File: {violation['file']}\n"
            error_msg += f"Path: {violation['path']}\n"
            error_msg += f"Issue: {violation['issue']}\n"
            error_msg += f"Text: {violation['text']}\n"
            if 'recommendation' in violation:
                error_msg += f"Recommendation: {violation['recommendation']}\n"
            error_msg += "\n"
        
        error_msg += "Fix these Markdown syntax issues to prevent Telegram parsing errors.\n"
        pytest.fail(error_msg)
    
    def _report_code_markdown_violations(self, violations: List[Dict]):
        """Report code file Markdown violations."""
        error_msg = "\n\nProblematic Markdown patterns in code files:\n\n"
        
        for violation in violations:
            error_msg += f"File: {violation['file']}\n"
            error_msg += f"Line {violation['line']}: {violation['content']}\n"
            error_msg += f"Issue: {violation['issue']}\n"
            error_msg += f"Recommendation: {violation['recommendation']}\n\n"
        
        error_msg += "Fix these patterns to prevent Markdown parsing errors.\n"
        pytest.fail(error_msg)
    
    def _report_f_string_violations(self, violations: List[Dict]):
        """Report f-string Markdown violations."""
        error_msg = "\n\nPotentially unsafe f-string Markdown usage:\n\n"
        
        for violation in violations:
            error_msg += f"File: {violation['file']}\n"
            error_msg += f"Line {violation['line']}: {violation['content']}\n"
            error_msg += f"Issue: {violation['issue']}\n"
            error_msg += f"Recommendation: {violation['recommendation']}\n\n"
        
        error_msg += "Review these f-strings for safe Markdown usage.\n"
        pytest.fail(error_msg)
    
    def test_telegram_markdown_v2_compatibility(self):
        """Test for Telegram MarkdownV2 specific requirements."""
        violations = []
        
        # Characters that need escaping in MarkdownV2
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        # Check translation files for unescaped special characters
        locale_dir = Path('bot/i18n/locales')
        for locale_file in locale_dir.glob('*.json'):
            try:
                with open(locale_file, 'r', encoding='utf-8') as f:
                    translations = json.load(f)
                    violations.extend(self._check_markdownv2_compatibility(
                        translations, locale_file.name, "", special_chars
                    ))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
        
        if violations:
            error_msg = "\n\nTelegram MarkdownV2 compatibility issues:\n\n"
            for violation in violations:
                error_msg += f"File: {violation['file']}\n"
                error_msg += f"Path: {violation['path']}\n"
                error_msg += f"Issue: {violation['issue']}\n"
                error_msg += f"Text: {violation['text']}\n\n"
            
            error_msg += "Note: If using Markdown parse_mode, ensure special characters are properly escaped.\n"
            pytest.fail(error_msg)
    
    def _check_markdownv2_compatibility(self, data: Any, filename: str, path: str, special_chars: List[str]) -> List[Dict]:
        """Check for MarkdownV2 compatibility issues."""
        violations = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                violations.extend(self._check_markdownv2_compatibility(
                    value, filename, current_path, special_chars
                ))
        elif isinstance(data, str):
            # Check for unescaped special characters in text that might be used with MarkdownV2
            for char in special_chars:
                if char in data and f'\\{char}' not in data:
                    # Only flag if the character appears to be in a context where it might cause issues
                    if self._is_problematic_context(data, char):
                        violations.append({
                            'file': filename,
                            'path': path,
                            'text': data,
                            'issue': f"Unescaped special character '{char}' that might cause MarkdownV2 parsing issues",
                            'char': char
                        })
        
        return violations
    
    def _is_problematic_context(self, text: str, char: str) -> bool:
        """Check if a special character appears in a problematic context."""
        # Only flag certain characters in certain contexts to avoid false positives
        problematic_contexts = {
            '_': lambda t, c: t.count(c) > 1,  # Multiple underscores
            '*': lambda t, c: t.count(c) > 1,  # Multiple asterisks
            '[': lambda t, c: ']' in t,        # Bracket pairs
            '(': lambda t, c: ')' in t,        # Parenthesis pairs
            '`': lambda t, c: t.count(c) > 1,  # Multiple backticks
        }
        
        if char in problematic_contexts:
            return problematic_contexts[char](text, char)
        
        return False
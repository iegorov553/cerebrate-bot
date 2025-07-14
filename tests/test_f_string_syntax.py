"""
Test to find all f-string syntax errors in the codebase.
"""

import os
import re
import pytest
from pathlib import Path
from typing import List, Tuple


class TestFStringSyntax:
    """Test for f-string syntax errors throughout the codebase."""

    def setup_method(self):
        """Set up test data."""
        self.bot_dir = Path('bot')
        self.test_dir = Path('tests')
        
    def _find_f_string_syntax_errors(self, directory: Path) -> List[Tuple[str, int, str]]:
        """Find f-string syntax errors in Python files."""
        errors = []
        
        # Pattern to find f-strings with double quotes inside translator.translate calls
        # This pattern looks for f"...{translator.translate("...")}" which causes syntax errors
        pattern = r'f["\'].*?\{[^}]*translator\.translate\(["\'][^"\']*["\'][^}]*\}'
        
        for file_path in directory.rglob('*.py'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for line_num, line in enumerate(lines, 1):
                    # Look for problematic f-string patterns
                    if self._has_f_string_syntax_error(line):
                        relative_path = str(file_path.relative_to(Path.cwd()))
                        errors.append((relative_path, line_num, line.strip()))
                        
            except Exception as e:
                # Skip files that can't be read
                continue
                
        return errors
    
    def _has_f_string_syntax_error(self, line: str) -> bool:
        """Check if line has f-string syntax error."""
        # Remove comments and strings to avoid false positives
        line = line.strip()
        
        # Skip comments and empty lines
        if not line or line.startswith('#'):
            return False
            
        # Look for f-strings with double quotes inside translator.translate calls
        patterns = [
            # f"{translator.translate("key")}" - double quotes inside f-string with double quotes
            r'f"[^"]*\{[^}]*translator\.translate\(".*?"\)[^}]*\}[^"]*"',
            # f'{translator.translate("key")}' - double quotes inside f-string with single quotes  
            r"f'[^']*\{[^}]*translator\.translate\(\".*?\"\)[^}]*\}[^']*'",
            # Also catch the reverse case
            r"f'[^']*\{[^}]*translator\.translate\('.*?'\)[^}]*\}[^']*'",
        ]
        
        for pattern in patterns:
            if re.search(pattern, line):
                return True
                
        return False
    
    def test_no_f_string_syntax_errors_in_bot(self):
        """Test that there are no f-string syntax errors in bot directory."""
        errors = self._find_f_string_syntax_errors(self.bot_dir)
        
        if errors:
            error_msg = "\n\nF-string syntax errors found:\n\n"
            for file_path, line_num, line in errors:
                error_msg += f"{file_path}:{line_num}: {line}\n"
            
            error_msg += "\n\nThese errors occur when using double quotes inside f-strings that also use double quotes."
            error_msg += "\nFix by changing inner quotes to single quotes, e.g.:"
            error_msg += '\nf"{translator.translate("key")}" → f"{translator.translate(\'key\')}"'
            
            pytest.fail(error_msg)
    
    def test_find_all_translator_calls_in_f_strings(self):
        """Find all translator calls inside f-strings for manual review."""
        translator_in_f_strings = []
        
        for file_path in self.bot_dir.rglob('*.py'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                        
                    # Find any f-string containing translator.translate
                    if ('f"' in line or "f'" in line) and 'translator.translate' in line:
                        relative_path = str(file_path.relative_to(Path.cwd()))
                        translator_in_f_strings.append((relative_path, line_num, line))
                        
            except Exception:
                continue
        
        if translator_in_f_strings:
            print(f"\n\nFound {len(translator_in_f_strings)} f-strings with translator calls:")
            print("=" * 60)
            for file_path, line_num, line in translator_in_f_strings:
                print(f"{file_path}:{line_num}: {line}")
            
        # This test always passes - it's just for information
        assert True
    
    def test_compile_syntax_check(self):
        """Try to compile each Python file to catch syntax errors."""
        syntax_errors = []
        
        for file_path in self.bot_dir.rglob('*.py'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    source = f.read()
                
                # Try to compile the source
                compile(source, str(file_path), 'exec')
                
            except SyntaxError as e:
                relative_path = str(file_path.relative_to(Path.cwd()))
                syntax_errors.append((relative_path, e.lineno, str(e)))
            except Exception:
                # Other errors are not syntax errors
                continue
        
        if syntax_errors:
            error_msg = "\n\nSyntax errors found:\n\n"
            for file_path, line_num, error in syntax_errors:
                error_msg += f"{file_path}:{line_num}: {error}\n"
            
            pytest.fail(error_msg)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
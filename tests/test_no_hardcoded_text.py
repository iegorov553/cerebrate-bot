"""
Test for preventing hardcoded Russian text in user interface.

This test ensures that all user-facing text is externalized to translation files.
"""

import os
import re
from pathlib import Path

import pytest


class TestNoHardcodedText:
    """Test suite to prevent hardcoded Russian text in user interface."""

    def get_python_files(self):
        """Get all Python files in the bot directory."""
        bot_dir = Path(__file__).parent.parent / "bot"
        python_files = []

        for root, dirs, files in os.walk(bot_dir):
            # Skip test directories and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith(("__pycache__", "test"))]

            for file in files:
                if file.endswith(".py"):
                    python_files.append(Path(root) / file)

        return python_files

    def is_hardcoded_text_violation(self, line, file_path):
        """
        Check if a line contains hardcoded Russian text that should be externalized.

        Args:
            line: Line of code to check
            file_path: Path to the file being checked

        Returns:
            tuple: (is_violation, violation_description)
        """
        # Skip comments and docstrings
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
            return False, None

        # Skip test files completely
        if "test_" in str(file_path) or "/tests/" in str(file_path):
            return False, None

        # Skip specific files that are allowed to have hardcoded text
        allowed_hardcode_files = {
            "config.py",  # Default values
            "version.py",  # Version strings
        }

        if file_path.name in allowed_hardcode_files:
            return False, None

        # Pattern for Russian text in strings
        russian_text_pattern = r'["\'][^"\']*[А-Яа-я][^"\']*["\']'

        # Find all Russian text strings
        matches = re.findall(russian_text_pattern, line)

        if not matches:
            return False, None

        # Allowed patterns (exceptions)
        allowed_patterns = [
            # Default values for missing data
            r'["\']Без имени["\']',
            r'["\']Неизвестно["\']',
            r'["\']неизвестен["\']',
            r'["\']Аноним["\']',
            r'["\']неизв\.["\']',
            r'["\']Вопрос["\']',
            # Technical/internal strings (not user-facing)
            r'["\'][а-я]+["\']',  # Single lowercase words (likely internal)
            # Placeholder/template strings that are not user-facing
            r'["\'].*\{.*\}.*["\']',  # Strings with placeholders might be internal
        ]

        for match in matches:
            is_allowed = False
            for pattern in allowed_patterns:
                if re.search(pattern, match):
                    is_allowed = True
                    break

            if not is_allowed:
                # Additional checks for context

                # Skip if it's in a translation key context
                if "translator.translate" in line or ".translate(" in line:
                    continue

                # Skip if it's a variable assignment for translation lookup
                if "=" in line and any(word in line for word in ["key", "translation", "message_key"]):
                    continue

                # Skip logging messages (internal, not user-facing)
                if any(log_func in line for log_func in ["logger.", "log.", "print("]):
                    continue

                # This is likely a hardcoded user-facing text
                return True, f"Hardcoded Russian text found: {match}"

        return False, None

    def test_no_hardcoded_russian_text_in_handlers(self):
        """Test that handler files don't contain hardcoded Russian text."""
        violations = []

        # Focus on handler files where user-facing text is most common
        handler_patterns = ["bot/handlers/**/*.py", "bot/keyboards/**/*.py"]

        checked_files = []

        for pattern in handler_patterns:
            for file_path in Path(".").glob(pattern):
                if file_path.is_file():
                    checked_files.append(file_path)

                    try:
                        with open(file_path, encoding="utf-8") as f:
                            for line_num, line in enumerate(f, 1):
                                is_violation, description = self.is_hardcoded_text_violation(line, file_path)
                                if is_violation:
                                    violations.append(
                                        {
                                            "file": str(file_path),
                                            "line": line_num,
                                            "content": line.strip(),
                                            "violation": description,
                                        }
                                    )
                    except UnicodeDecodeError:
                        # Skip binary files
                        continue

        # Generate detailed error message
        if violations:
            error_msg = "\n\nHardcoded Russian text found in user interface:\n\n"

            for violation in violations:
                error_msg += f"File: {violation['file']}\n"
                error_msg += f"Line {violation['line']}: {violation['content']}\n"
                error_msg += f"Issue: {violation['violation']}\n\n"

            error_msg += "\nAll user-facing text should be moved to translation files (bot/i18n/locales/).\n"
            error_msg += "Use translator.translate('key') instead of hardcoded strings.\n"

            pytest.fail(error_msg)

        # Ensure we actually checked some files
        assert len(checked_files) > 0, "No handler files were checked"

    def test_specific_known_violations(self):
        """Test specific files that are known to have violations."""
        known_violation_files = [
            "bot/handlers/callbacks/admin_callbacks.py",
            "bot/handlers/callbacks/friends_callbacks.py",
            "bot/handlers/command_handlers.py",
            "bot/handlers/admin_conversations.py",
            "bot/handlers/error_handler.py",
            "bot/handlers/rate_limit_handler.py",
        ]

        violations = []

        for file_path_str in known_violation_files:
            file_path = Path(file_path_str)

            if not file_path.exists():
                continue

            try:
                with open(file_path, encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        # More strict checking for known problematic files
                        if re.search(r'["\'][^"\']*[А-Яа-я][^"\']*["\']', line):
                            # Skip lines that properly use translator
                            if "translator.translate" in line or ".translate(" in line:
                                continue
                            if "logger." in line or "log." in line:
                                continue

                            # Look for await message sending functions with Russian text
                            if any(func in line for func in ["edit_message_text", "reply_text", "send_message"]):
                                violations.append({"file": str(file_path), "line": line_num, "content": line.strip()})
            except UnicodeDecodeError:
                continue

        if violations:
            error_msg = "\n\nKnown hardcoded text violations found:\n\n"
            for violation in violations:
                error_msg += f"{violation['file']}:{violation['line']}\n"
                error_msg += f"  {violation['content']}\n\n"

            pytest.fail(error_msg)

    def test_translation_keys_exist(self):
        """Test that commonly needed translation keys exist."""
        # Read Russian translation file
        ru_file = Path("bot/i18n/locales/ru.json")

        if not ru_file.exists():
            pytest.skip("Russian translation file not found")

        import json

        with open(ru_file, encoding="utf-8") as f:
            translations = json.load(f)

        # Required keys for common hardcoded text
        required_keys = [
            "common.unknown",
            "common.anonymous",
            "common.no_name",
            "common.loading",
            "admin.no_friend_activity",
            "admin.activity_levels.high",
            "admin.activity_levels.medium",
            "admin.activity_levels.low",
            "errors.rate_limit",
            "broadcast.enter_message",
            "broadcast.confirm_send",
        ]

        missing_keys = []

        def check_nested_key(translations, key_path):
            keys = key_path.split(".")
            current = translations
            for key in keys:
                if key not in current:
                    return False
                current = current[key]
            return True

        for key in required_keys:
            if not check_nested_key(translations, key):
                missing_keys.append(key)

        if missing_keys:
            error_msg = f"\nMissing translation keys: {missing_keys}\n"
            error_msg += "Add these keys to bot/i18n/locales/ru.json to replace hardcoded text."
            pytest.fail(error_msg)

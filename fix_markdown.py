#!/usr/bin/env python3
"""
Автоматическое исправление проблем с Markdown в переводах.
Экранирует специальные символы для корректного отображения.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any

class MarkdownFixer:
    def __init__(self):
        # Символы, которые нужно экранировать для MarkdownV2
        self.escape_chars = {
            '_': '\\_',
            '*': '\\*',
            '[': '\\[',
            ']': '\\]',
            '(': '\\(',
            ')': '\\)',
            '~': '\\~',
            '`': '\\`',
            '>': '\\>',
            '#': '\\#',
            '+': '\\+',
            '-': '\\-',
            '=': '\\=',
            '|': '\\|',
            '{': '\\{',
            '}': '\\}',
            '.': '\\.',
            '!': '\\!'
        }
    
    def escape_markdown(self, text: str) -> str:
        """Экранирует специальные символы Markdown."""
        if not text:
            return text
        
        # Не экранируем, если это уже экранированный текст
        if '\\' in text:
            return text
        
        # Не экранируем код в обратных кавычках
        if '`' in text and text.count('`') >= 2:
            return text
        
        # Не экранируем жирный текст в **
        if text.startswith('**') and text.endswith('**'):
            return text
        
        # Не экранируем курсив в *
        if text.startswith('*') and text.endswith('*') and not text.startswith('**'):
            return text
        
        # Экранируем только проблематичные символы
        result = text
        for char, escaped in self.escape_chars.items():
            # Пропускаем символы, которые уже экранированы
            if f'\\{char}' not in result:
                result = result.replace(char, escaped)
        
        return result
    
    def fix_translation_object(self, obj: Any) -> Any:
        """Рекурсивно исправляет объект перевода."""
        if isinstance(obj, dict):
            return {key: self.fix_translation_object(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self.fix_translation_object(item) for item in obj]
        elif isinstance(obj, str):
            return self.escape_markdown(obj)
        else:
            return obj
    
    def fix_translation_file(self, file_path: Path) -> int:
        """Исправляет файл переводов."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Исправляем переводы
            fixed_data = self.fix_translation_object(data)
            
            # Сохраняем файл
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(fixed_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Исправлен файл: {file_path}")
            return 1
            
        except Exception as e:
            print(f"❌ Ошибка при исправлении {file_path}: {e}")
            return 0
    
    def fix_all_translations(self) -> int:
        """Исправляет все файлы переводов."""
        locale_dir = Path('bot/i18n/locales')
        fixed_count = 0
        
        if not locale_dir.exists():
            print(f"❌ Папка переводов не найдена: {locale_dir}")
            return 0
        
        for file_path in locale_dir.glob('*.json'):
            if file_path.is_file():
                fixed_count += self.fix_translation_file(file_path)
        
        return fixed_count
    
    def remove_conflicting_markdown(self, text: str) -> str:
        """Удаляет конфликтующие символы Markdown."""
        # Удаляем неправильные комбинации
        text = re.sub(r'\*\*([^*]+)\*\*', r'\\*\\*\1\\*\\*', text)  # Экранируем жирный текст
        text = re.sub(r'\*([^*]+)\*', r'\\*\1\\*', text)  # Экранируем курсив
        text = re.sub(r'_([^_]+)_', r'\\_\1\\_', text)  # Экранируем подчеркивание
        
        return text
    
    def fix_code_strings(self) -> int:
        """Исправляет строки в коде Python."""
        fixed_count = 0
        
        # Паттерны файлов для исправления
        patterns = [
            'bot/handlers/**/*.py',
            'bot/keyboards/**/*.py',
        ]
        
        for pattern in patterns:
            for file_path in Path('.').glob(pattern):
                if file_path.is_file():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        original_content = content
                        
                        # Исправляем строки с parse_mode='Markdown'
                        # Ищем f-строки и обычные строки с проблемными символами
                        lines = content.split('\n')
                        fixed_lines = []
                        
                        for line in lines:
                            # Проверяем, содержит ли строка Markdown
                            if 'parse_mode=' in line and ('Markdown' in line or 'MarkdownV2' in line):
                                # Ищем строки с неэкранированными символами
                                if re.search(r'[*_`\[\]()~>#+=|{}.!-]', line):
                                    # Заменяем на более безопасный вариант
                                    line = re.sub(r'parse_mode=[\'"]Markdown[\'"]', 'parse_mode=\'Markdown\'', line)
                            
                            fixed_lines.append(line)
                        
                        content = '\n'.join(fixed_lines)
                        
                        if content != original_content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                            
                            print(f"✅ Исправлены строки в: {file_path}")
                            fixed_count += 1
                    
                    except Exception as e:
                        print(f"❌ Ошибка при исправлении {file_path}: {e}")
        
        return fixed_count

def main():
    """Главная функция."""
    fixer = MarkdownFixer()
    
    print("🔧 Исправление проблем с Markdown...")
    
    # Исправляем файлы переводов
    translation_fixes = fixer.fix_all_translations()
    print(f"📄 Исправлено файлов переводов: {translation_fixes}")
    
    # Исправляем код Python
    code_fixes = fixer.fix_code_strings()
    print(f"🐍 Исправлено файлов кода: {code_fixes}")
    
    total_fixes = translation_fixes + code_fixes
    print(f"\n✅ Всего исправлено: {total_fixes} файлов")
    
    if total_fixes > 0:
        print("\n📝 Рекомендации:")
        print("1. Проверьте что приложение работает корректно")
        print("2. Запустите тесты: python3 -m pytest tests/test_markdown_validation.py")
        print("3. Протестируйте отображение сообщений в Telegram")

if __name__ == "__main__":
    main()
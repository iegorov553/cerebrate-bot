#!/usr/bin/env python3
"""
Автоматический анализатор хардкода русского текста.
Находит все проблемы и создает полный список для исправления.
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Tuple, Set

class HardcodeAnalyzer:
    def __init__(self):
        self.russian_patterns = [
            r'[а-яё]',  # Русские буквы
            r'[А-ЯЁ]',  # Русские заглавные буквы
        ]
        
        # Исключения - не русский текст
        self.exclusions = [
            r'import.*from.*',
            r'#.*',  # Комментарии
            r'""".*"""',  # Docstrings
            r'logger\.',
            r'self\.',
            r'def\s+',
            r'class\s+',
            r'async\s+def',
            r'await\s+',
            r'return\s+',
            r'raise\s+',
            r'except\s+',
            r'try:',
            r'if\s+',
            r'elif\s+',
            r'else:',
            r'for\s+',
            r'while\s+',
            r'with\s+',
            r'assert\s+',
            r'print\(',
            r'\.format\(',
            r'\.translate\(',
            r'translator\.translate\(',
            r'f".*{.*}.*"',  # f-строки с переменными
            r"f'.*{.*}.*'",  # f-строки с переменными
            r'callback_data=',
            r'parse_mode=',
            r'encoding=',
            r'utf-8',
            r'markdown',
            r'html',
            r'json',
            r'\.py$',
            r'\.md$',
            r'\.txt$',
            r'\.json$',
            r'bot/',
            r'tests/',
            r'\.log',
            r'__pycache__',
            r'\.pyc',
            r'\.git',
            r'error=str\(e\)',
            r'user_id=',
            r'username=',
            r'callback_data=',
            r'file_path=',
            r'pattern=',
            r'path=',
            r'name=',
            r'text=',
            r'description=',
            r'content=',
            r'message=',
            r'data=',
            r'query=',
            r'context=',
            r'translator=',
            r'config=',
            r'client=',
            r'cache=',
            r'logger=',
            r'result=',
            r'response=',
            r'request=',
            r'session=',
            r'token=',
            r'key=',
            r'value=',
            r'status=',
            r'code=',
            r'url=',
            r'api=',
            r'db=',
            r'sql=',
            r'table=',
            r'column=',
            r'row=',
            r'field=',
            r'param=',
            r'arg=',
            r'kwargs=',
            r'args=',
            r'self\.',
            r'cls\.',
            r'super\(\)',
            r'__init__',
            r'__str__',
            r'__repr__',
            r'__len__',
            r'__iter__',
            r'__next__',
            r'__enter__',
            r'__exit__',
            r'__call__',
            r'__getitem__',
            r'__setitem__',
            r'__delitem__',
            r'__contains__',
            r'__eq__',
            r'__ne__',
            r'__lt__',
            r'__le__',
            r'__gt__',
            r'__ge__',
            r'__bool__',
            r'__hash__',
            r'__dict__',
            r'__class__',
            r'__name__',
            r'__file__',
            r'__path__',
            r'__package__',
            r'__version__',
            r'__author__',
            r'__email__',
            r'__license__',
            r'__copyright__',
            r'__credits__',
            r'__status__',
            r'__doc__',
            r'__annotations__',
            r'__module__',
            r'__qualname__',
            r'__slots__',
            r'__weakref__',
            r'__dict__',
            r'__getattribute__',
            r'__setattr__',
            r'__delattr__',
            r'__dir__',
            r'__sizeof__',
            r'__format__',
            r'__reduce__',
            r'__reduce_ex__',
            r'__getnewargs__',
            r'__getnewargs_ex__',
            r'__getstate__',
            r'__setstate__',
            r'__copy__',
            r'__deepcopy__',
            r'__pickle__',
            r'__unpickle__',
            r'True',
            r'False',
            r'None',
            r'NotImplemented',
            r'Ellipsis',
            r'__debug__',
            r'quit',
            r'exit',
            r'copyright',
            r'credits',
            r'license',
            r'help',
        ]
    
    def is_russian_text(self, text: str) -> bool:
        """Проверяет, содержит ли текст русские буквы."""
        for pattern in self.russian_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def is_excluded(self, line: str) -> bool:
        """Проверяет, должна ли строка быть исключена из анализа."""
        for pattern in self.exclusions:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def extract_hardcoded_strings(self, line: str) -> List[str]:
        """Извлекает хардкодированные строки из строки кода."""
        strings = []
        
        # Паттерны для поиска строк
        patterns = [
            r'"([^"]*[а-яёА-ЯЁ][^"]*)"',  # Двойные кавычки
            r"'([^']*[а-яёА-ЯЁ][^']*)'",  # Одинарные кавычки
            r'f"([^"]*[а-яёА-ЯЁ][^"]*)"',  # f-строки с двойными кавычками
            r"f'([^']*[а-яёА-ЯЁ][^']*)'",  # f-строки с одинарными кавычками
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, line)
            for match in matches:
                if self.is_russian_text(match) and not self.is_excluded(match):
                    strings.append(match)
        
        return strings
    
    def analyze_file(self, file_path: Path) -> List[Dict]:
        """Анализирует файл на предмет хардкодированного русского текста."""
        violations = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if self.is_excluded(line):
                        continue
                    
                    hardcoded_strings = self.extract_hardcoded_strings(line)
                    for string in hardcoded_strings:
                        violations.append({
                            'file': str(file_path),
                            'line': line_num,
                            'text': string,
                            'full_line': line.strip(),
                            'severity': 'high' if len(string) > 10 else 'medium'
                        })
        
        except (UnicodeDecodeError, PermissionError):
            pass
        
        return violations
    
    def analyze_project(self) -> Dict:
        """Анализирует весь проект."""
        result = {
            'total_violations': 0,
            'files_with_violations': 0,
            'violations_by_file': {},
            'unique_strings': set(),
            'severity_counts': {'high': 0, 'medium': 0, 'low': 0}
        }
        
        # Паттерны файлов для анализа
        patterns = [
            'bot/handlers/**/*.py',
            'bot/keyboards/**/*.py',
            'bot/utils/**/*.py',
            'bot/services/**/*.py',
            'bot/database/**/*.py',
            'bot/admin/**/*.py',
            'bot/cache/**/*.py',
            'bot/questions/**/*.py',
            'bot/feedback/**/*.py',
            'bot/i18n/**/*.py',
        ]
        
        for pattern in patterns:
            for file_path in Path('.').glob(pattern):
                if file_path.is_file():
                    violations = self.analyze_file(file_path)
                    if violations:
                        result['files_with_violations'] += 1
                        result['violations_by_file'][str(file_path)] = violations
                        result['total_violations'] += len(violations)
                        
                        for violation in violations:
                            result['unique_strings'].add(violation['text'])
                            result['severity_counts'][violation['severity']] += 1
        
        return result
    
    def generate_mapping(self, violations: Dict) -> Dict[str, str]:
        """Генерирует mapping для автоматического исправления."""
        mapping = {}
        
        # Группируем строки по типам
        for file_path, file_violations in violations['violations_by_file'].items():
            for violation in file_violations:
                text = violation['text']
                if text not in mapping:
                    # Генерируем ключ на основе содержимого
                    key = self.generate_translation_key(text, file_path)
                    mapping[text] = key
        
        return mapping
    
    def generate_translation_key(self, text: str, file_path: str) -> str:
        """Генерирует ключ перевода на основе текста и файла."""
        # Определяем категорию по файлу
        if 'admin' in file_path:
            category = 'admin'
        elif 'friend' in file_path:
            category = 'friends'
        elif 'config' in file_path:
            category = 'config'
        elif 'error' in file_path:
            category = 'errors'
        elif 'broadcast' in file_path:
            category = 'broadcast'
        elif 'question' in file_path:
            category = 'questions'
        else:
            category = 'common'
        
        # Генерируем ключ на основе содержимого
        key_part = text.lower()
        key_part = re.sub(r'[^а-яёa-z0-9\s]', '', key_part)
        key_part = re.sub(r'\s+', '_', key_part)
        key_part = key_part[:30]  # Ограничиваем длину
        
        # Определяем тип сообщения
        if text.startswith('❌'):
            type_prefix = 'error'
        elif text.startswith('✅'):
            type_prefix = 'success'
        elif text.startswith('⚠️'):
            type_prefix = 'warning'
        elif text.startswith('📢'):
            type_prefix = 'broadcast'
        elif text.startswith('📥'):
            type_prefix = 'loading'
        elif text.startswith('⏰'):
            type_prefix = 'time'
        elif text.startswith('🔒'):
            type_prefix = 'access'
        elif text.startswith('📊'):
            type_prefix = 'stats'
        elif '**' in text:
            type_prefix = 'title'
        elif 'Пример:' in text:
            type_prefix = 'example'
        elif 'Использование:' in text:
            type_prefix = 'usage'
        else:
            type_prefix = 'message'
        
        return f"{category}.{type_prefix}_{key_part}"
    
    def save_results(self, violations: Dict, output_file: str = "hardcode_analysis.json"):
        """Сохраняет результаты анализа."""
        # Конвертируем set в list для JSON
        violations_copy = violations.copy()
        violations_copy['unique_strings'] = list(violations['unique_strings'])
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(violations_copy, f, ensure_ascii=False, indent=2)
    
    def print_summary(self, violations: Dict):
        """Выводит краткую сводку."""
        print(f"📊 Анализ хардкода завершен!")
        print(f"📁 Файлов с проблемами: {violations['files_with_violations']}")
        print(f"🔍 Всего нарушений: {violations['total_violations']}")
        print(f"📝 Уникальных строк: {len(violations['unique_strings'])}")
        print(f"🔴 Высокая важность: {violations['severity_counts']['high']}")
        print(f"🟡 Средняя важность: {violations['severity_counts']['medium']}")
        print(f"🟢 Низкая важность: {violations['severity_counts']['low']}")
        
        print("\n📋 Топ проблемных файлов:")
        sorted_files = sorted(violations['violations_by_file'].items(), 
                            key=lambda x: len(x[1]), reverse=True)
        for file_path, file_violations in sorted_files[:10]:
            print(f"  {file_path}: {len(file_violations)} нарушений")
        
        print("\n🎯 Примеры найденных строк:")
        for i, string in enumerate(list(violations['unique_strings'])[:10]):
            print(f"  {i+1}. \"{string}\"")

def main():
    """Главная функция."""
    analyzer = HardcodeAnalyzer()
    
    print("🔍 Анализирую хардкод русского текста...")
    violations = analyzer.analyze_project()
    
    analyzer.print_summary(violations)
    analyzer.save_results(violations)
    
    print(f"\n📄 Результаты сохранены в hardcode_analysis.json")
    
    # Генерируем mapping
    mapping = analyzer.generate_mapping(violations)
    with open('hardcode_mapping.json', 'w', encoding='utf-8') as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    
    print(f"📄 Mapping сохранен в hardcode_mapping.json")

if __name__ == "__main__":
    main()
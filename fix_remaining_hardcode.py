#!/usr/bin/env python3
"""
Исправление оставшихся 10 проблем с хардкодом.
"""

import re
from pathlib import Path
from typing import Dict, List

class RemainingHardcodeFixer:
    def __init__(self):
        # Оставшиеся проблемы из тестов
        self.remaining_fixes = [
            {
                'file': 'bot/handlers/admin_conversations.py',
                'line': 211,
                'old': 'text="⏰ **Время создания рассылки истекло**\\n\\nСессия завершена. Используйте /broadcast для начала заново."',
                'new': 'text=translator.translate("broadcast.timeout_message")',
                'key': 'broadcast.timeout_message'
            },
            {
                'file': 'bot/handlers/rate_limit_handler.py',
                'line': 49,
                'old': 'f"📊 Использовано: {stats[\'current_count\']}/{stats[\'max_requests\']}\\n"',
                'new': 'f"{translator.translate(\'rate_limit.usage_count\', current=stats[\'current_count\'], max=stats[\'max_requests\'])}\\n"',
                'key': 'rate_limit.usage_count'
            },
            {
                'file': 'bot/handlers/rate_limit_handler.py',
                'line': 51,
                'old': 'f"🔄 Окно сброса: {stats[\'window_seconds\']} сек.\\n\\n"',
                'new': 'f"{translator.translate(\'rate_limit.reset_window\', seconds=stats[\'window_seconds\'])}\\n\\n"',
                'key': 'rate_limit.reset_window'
            },
            {
                'file': 'bot/handlers/rate_limit_handler.py',
                'line': 56,
                'old': 'InlineKeyboardButton("🏠 Главное меню", callback_data="menu_main")',
                'new': 'InlineKeyboardButton(translator.translate("menu.back_main"), callback_data="menu_main")',
                'key': None  # Already exists
            },
            {
                'file': 'bot/handlers/rate_limit_handler.py',
                'line': 57,
                'old': 'InlineKeyboardButton("❓ Помощь", callback_data="menu_help")',
                'new': 'InlineKeyboardButton(translator.translate("menu.help"), callback_data="menu_help")',
                'key': None  # Already exists
            },
            {
                'file': 'bot/handlers/rate_limit_handler.py',
                'line': 71,
                'old': 'await update.callback_query.answer("Превышен лимит запросов!")',
                'new': 'await update.callback_query.answer(translator.translate("rate_limit.exceeded_alert"))',
                'key': 'rate_limit.exceeded_alert'
            },
            {
                'file': 'bot/handlers/admin_handlers.py',
                'line': 60,
                'old': 'f"👥 Всего пользователей: {stats[\'total\']}\\n"',
                'new': 'f"{translator.translate(\'admin.total_users\', total=stats[\'total\'])}\\n"',
                'key': None  # Already exists
            },
            {
                'file': 'bot/handlers/admin_handlers.py',
                'line': 61,
                'old': 'f"✅ Активных: {stats[\'active\']} ({active_percentage:.1f}%)\\n"',
                'new': 'f"{translator.translate(\'admin.active_users\', active=stats[\'active\'], percentage=active_percentage)}\\n"',
                'key': None  # Already exists
            },
            {
                'file': 'bot/handlers/admin_handlers.py',
                'line': 62,
                'old': 'f"🆕 Новых за неделю: {stats[\'new_week\']}\\n\\n"',
                'new': 'f"{translator.translate(\'admin.new_users_week\', count=stats[\'new_week\'])}\\n\\n"',
                'key': None  # Already exists
            },
            {
                'file': 'bot/handlers/admin_handlers.py',
                'line': 63,
                'old': 'f"📈 Активность: {\'Высокая\' if active_percentage > 50 else \'Средняя\' if active_percentage > 25 else \'Низкая\'}"',
                'new': 'f"{translator.translate(\'admin.activity_level\', level=translator.translate(\'common.high\' if active_percentage > 50 else \'common.medium\' if active_percentage > 25 else \'common.low\'))}"',
                'key': None  # Already exists
            },
            {
                'file': 'bot/handlers/error_handler.py',
                'line': 55,
                'old': 'text="❌ Произошла ошибка. Попробуйте позже или обратитесь к администратору."',
                'new': 'text=translator.translate("errors.general_with_admin")',
                'key': 'errors.general_with_admin'
            }
        ]
        
        # Новые ключи переводов
        self.new_translation_keys = {
            'broadcast.timeout_message': {
                'ru': '⏰ **Время создания рассылки истекло**\n\nСессия завершена. Используйте /broadcast для начала заново.',
                'en': '⏰ **Broadcast creation time expired**\n\nSession ended. Use /broadcast to start over.',
                'es': '⏰ **Tiempo de creación de difusión expirado**\n\nSesión terminada. Use /broadcast para comenzar de nuevo.'
            },
            'rate_limit.usage_count': {
                'ru': '📊 Использовано: {current}/{max}',
                'en': '📊 Used: {current}/{max}',
                'es': '📊 Usado: {current}/{max}'
            },
            'rate_limit.reset_window': {
                'ru': '🔄 Окно сброса: {seconds} сек.',
                'en': '🔄 Reset window: {seconds} sec.',
                'es': '🔄 Ventana de reinicio: {seconds} seg.'
            },
            'rate_limit.exceeded_alert': {
                'ru': 'Превышен лимит запросов!',
                'en': 'Rate limit exceeded!',
                'es': '¡Límite de solicitudes excedido!'
            },
            'errors.general_with_admin': {
                'ru': '❌ Произошла ошибка. Попробуйте позже или обратитесь к администратору.',
                'en': '❌ An error occurred. Try later or contact administrator.',
                'es': '❌ Ocurrió un error. Inténtalo más tarde o contacta al administrador.'
            }
        }
    
    def add_translations(self):
        """Добавляет новые переводы в файлы."""
        import json
        
        locale_dir = Path('bot/i18n/locales')
        
        for lang in ['ru', 'en', 'es']:
            locale_file = locale_dir / f'{lang}.json'
            
            if not locale_file.exists():
                continue
                
            with open(locale_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Добавляем новые ключи
            for key, translations in self.new_translation_keys.items():
                if lang in translations:
                    # Разбиваем ключ на части для nested структуры
                    parts = key.split('.')
                    current = data
                    
                    # Создаем nested структуру если нужно
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    
                    # Добавляем значение
                    current[parts[-1]] = translations[lang]
            
            # Сохраняем файл
            with open(locale_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Добавлено {len(self.new_translation_keys)} новых ключей")
    
    def fix_file(self, file_path: str) -> int:
        """Исправляет файл."""
        path = Path(file_path)
        if not path.exists():
            return 0
            
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixes_count = 0
        
        # Применяем исправления для этого файла
        for fix in self.remaining_fixes:
            if fix['file'] == file_path:
                # Ищем и заменяем
                old_pattern = fix['old']
                new_replacement = fix['new']
                
                # Экранируем специальные символы regex
                old_escaped = re.escape(old_pattern)
                
                if re.search(old_escaped, content):
                    content = re.sub(old_escaped, new_replacement, content)
                    fixes_count += 1
                    print(f"✅ Исправлено: {old_pattern[:50]}...")
        
        # Сохраняем файл если были изменения
        if content != original_content:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Файл обновлен: {file_path}")
        
        return fixes_count
    
    def fix_all_remaining(self):
        """Исправляет все оставшиеся проблемы."""
        total_fixes = 0
        
        # Получаем уникальные файлы для исправления
        files_to_fix = set(fix['file'] for fix in self.remaining_fixes)
        
        for file_path in files_to_fix:
            fixes = self.fix_file(file_path)
            total_fixes += fixes
        
        return total_fixes

def main():
    """Главная функция."""
    fixer = RemainingHardcodeFixer()
    
    print("🔧 Исправление оставшихся проблем с хардкодом...")
    
    # Добавляем переводы
    fixer.add_translations()
    
    # Исправляем файлы
    total_fixes = fixer.fix_all_remaining()
    
    print(f"\n✅ Исправлено оставшихся проблем: {total_fixes}")
    
    # Проверяем результат
    print("\n🧪 Проверяю результат...")
    import os
    result = os.system("python3 -m pytest tests/test_no_hardcoded_text.py::TestNoHardcodedText::test_no_hardcoded_russian_text_in_handlers -v")
    
    if result == 0:
        print("\n🎉 ВСЕ ПРОБЛЕМЫ С ХАРДКОДОМ ИСПРАВЛЕНЫ!")
    else:
        print("\n❌ Остались проблемы...")

if __name__ == "__main__":
    main()
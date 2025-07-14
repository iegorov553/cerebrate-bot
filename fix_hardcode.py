#!/usr/bin/env python3
"""
Автоматическое исправление хардкода русского текста в handler файлах.
Заменяет хардкодированные строки на translator.translate() вызовы.
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class HardcodeFixer:
    def __init__(self):
        self.hardcode_mapping = {
            # Admin conversations
            "🔒 Эта команда доступна только администраторам.": "admin.access_denied",
            "📢 **Создание рассылки**\\n\\n": "broadcast.create_title", 
            "Отправьте текст сообщения для рассылки всем пользователям.\\n\\n": "broadcast.enter_message",
            "💡 Поддерживается форматирование Markdown.\\n": "broadcast.markdown_support",
            "📝 Для отмены используйте /cancel": "broadcast.cancel_info",
            "✅ Да, отправить": "broadcast.confirm_yes",
            "❌ Нет, отменить": "broadcast.confirm_no",
            "📢 **Предпросмотр рассылки:**\\n\\n": "broadcast.preview_title",
            "Отправить это сообщение всем пользователям?": "broadcast.confirm_question",
            "📤 **Отправка рассылки...**\\n\\nПожалуйста, подождите...": "broadcast.sending_message",
            "✅ **Рассылка завершена!**\\n\\n": "broadcast.completed_title",
            "📊 **Результаты:**\\n": "broadcast.results_title",
            "❌ **Рассылка отменена**\\n\\nНичего не было отправлено.": "broadcast.cancelled_message",
            "❌ **Создание рассылки отменено**\\n\\nВсе данные очищены.": "broadcast.creation_cancelled",
            
            # Config commands
            "❌ Неверный формат числа\\n\\n": "errors.invalid_number_format",
            "Использование: `/freq N`\\n": "config.freq_usage",
            "Пример: `/freq 60`": "config.freq_example",
            "Пример: `/freq 120`": "config.freq_example_120",
            "1 час": "common.one_hour",
            "✅ **Частота уведомлений обновлена!**\\n\\n": "config.frequency_updated",
            "⏰ **Установить временное окно**\\n\\n": "config.window_title",
            "Использование: `/window HH:MM-HH:MM`\\n\\n": "config.window_usage",
            "Примеры:\\n": "config.examples_title",
            "• `/window 09:00-18:00` - с 9 утра до 6 вечера\\n": "config.window_example1",
            "• `/window 22:00-06:00` - с 10 вечера до 6 утра": "config.window_example2",
            "Формат: `HH:MM-HH:MM`\\n": "config.window_format",
            "Пример: `/window 09:00-22:00`": "config.window_format_example",
            "✅ **Временное окно обновлено!**\\n\\n": "config.window_updated",
            "Теперь уведомления будут приходить только в это время.": "config.window_updated_note",
            "📊 **Установить частоту уведомлений**\\n\\n": "config.frequency_title",
            "Где N - интервал в минутах между уведомлениями.\\n\\n": "config.frequency_description",
            "• `/freq 60` - каждый час\\n": "config.freq_example_60",
            "• `/freq 120` - каждые 2 часа\\n": "config.freq_example_120_long",
            "• `/freq 30` - каждые 30 минут": "config.freq_example_30",
            "❌ Минимальный интервал: 5 минут\\n\\n": "config.freq_min_error",
            "Пример: `/freq 30`": "config.freq_min_example",
            "❌ Максимальный интервал: 1440 минут (24 часа)\\n\\n": "config.freq_max_error",
            
            # Error handler
            "🔒 **Доступ запрещен**\\n\\nЭта команда доступна только администраторам.": "errors.admin_access_denied",
            "⚠️ **Лимит запросов превышен**\\n\\nВы отправляете команды слишком часто.\\n": "errors.rate_limit_exceeded",
            
            # Friends callbacks
            "❌ Произошла ошибка при загрузке списка друзей. Попробуйте позже.": "errors.friends_list_load_error",
            "📥 Загружаю запросы в друзья...": "friends.loading_requests",
            "📥 **Запросы в друзья**\\n\\n": "friends.requests_title",
            "**Входящие запросы:**\\n": "friends.requests_incoming_title",
            "**Входящие запросы:** нет\\n\\n": "friends.requests_incoming_none",
            "**Исходящие запросы:**\\n": "friends.requests_outgoing_title", 
            "**Исходящие запросы:** нет": "friends.requests_outgoing_none",
            "🔙 Назад к друзьям": "friends.back_to_friends",
            "❌ Произошла ошибка при загрузке запросов в друзья. Попробуйте позже.": "errors.requests_load_error",
            "❌ Произошла ошибка. Попробуйте позже.": "errors.generic_error",
            "✅ Принимаю запрос в друзья...": "friends.accept_processing",
            "❌ Не удалось принять запрос в друзья. Возможно, он уже был обработан.": "friends.accept_failed",
            "❌ Произошла ошибка при принятии запроса. Попробуйте позже.": "friends.accept_error",
            "Неизвестно": "common.unknown",
            "ожидает ответа": "friends.awaiting_response",
            "❌ Отклонить": "friends.decline_button",
            "✅ Принять": "friends.accept_button",
        }
        
        self.translation_keys = {
            "admin.access_denied": {
                "ru": "🔒 Эта команда доступна только администраторам.",
                "en": "🔒 This command is available only to administrators.",
                "es": "🔒 Este comando está disponible solo para administradores."
            },
            "broadcast.create_title": {
                "ru": "📢 **Создание рассылки**\n\n",
                "en": "📢 **Creating Broadcast**\n\n", 
                "es": "📢 **Creando Difusión**\n\n"
            },
            "broadcast.enter_message": {
                "ru": "Отправьте текст сообщения для рассылки всем пользователям.\n\n",
                "en": "Send message text for broadcast to all users.\n\n",
                "es": "Envía el texto del mensaje para difundir a todos los usuarios.\n\n"
            },
            "broadcast.markdown_support": {
                "ru": "💡 Поддерживается форматирование Markdown.\n",
                "en": "💡 Markdown formatting is supported.\n",
                "es": "💡 Se admite el formato Markdown.\n"
            },
            "broadcast.cancel_info": {
                "ru": "📝 Для отмены используйте /cancel",
                "en": "📝 Use /cancel to cancel",
                "es": "📝 Usa /cancel para cancelar"
            },
            "errors.invalid_number_format": {
                "ru": "❌ Неверный формат числа\n\n",
                "en": "❌ Invalid number format\n\n",
                "es": "❌ Formato de número inválido\n\n"
            },
            "config.freq_usage": {
                "ru": "Использование: `/freq N`\n",
                "en": "Usage: `/freq N`\n",
                "es": "Uso: `/freq N`\n"
            },
            "config.freq_example": {
                "ru": "Пример: `/freq 60`",
                "en": "Example: `/freq 60`",
                "es": "Ejemplo: `/freq 60`"
            },
            "config.freq_example_120": {
                "ru": "Пример: `/freq 120`",
                "en": "Example: `/freq 120`",
                "es": "Ejemplo: `/freq 120`"
            },
            "common.one_hour": {
                "ru": "1 час",
                "en": "1 hour",
                "es": "1 hora"
            },
            "config.frequency_updated": {
                "ru": "✅ **Частота уведомлений обновлена!**\n\n",
                "en": "✅ **Notification frequency updated!**\n\n",
                "es": "✅ **¡Frecuencia de notificaciones actualizada!**\n\n"
            },
            "errors.friends_list_load_error": {
                "ru": "❌ Произошла ошибка при загрузке списка друзей. Попробуйте позже.",
                "en": "❌ Error loading friends list. Try again later.",
                "es": "❌ Error al cargar la lista de amigos. Inténtalo más tarde."
            },
            "friends.loading_requests": {
                "ru": "📥 Загружаю запросы в друзья...",
                "en": "📥 Loading friend requests...",
                "es": "📥 Cargando solicitudes de amistad..."
            },
            "friends.requests_title": {
                "ru": "📥 **Запросы в друзья**\n\n",
                "en": "📥 **Friend Requests**\n\n",
                "es": "📥 **Solicitudes de Amistad**\n\n"
            },
            "friends.requests_incoming_title": {
                "ru": "**Входящие запросы:**\n",
                "en": "**Incoming requests:**\n",
                "es": "**Solicitudes entrantes:**\n"
            },
            "friends.requests_incoming_none": {
                "ru": "**Входящие запросы:** нет\n\n",
                "en": "**Incoming requests:** none\n\n",
                "es": "**Solicitudes entrantes:** ninguna\n\n"
            },
            "friends.requests_outgoing_title": {
                "ru": "**Исходящие запросы:**\n",
                "en": "**Outgoing requests:**\n",
                "es": "**Solicitudes salientes:**\n"
            },
            "friends.requests_outgoing_none": {
                "ru": "**Исходящие запросы:** нет",
                "en": "**Outgoing requests:** none",
                "es": "**Solicitudes salientes:** ninguna"
            },
            "errors.requests_load_error": {
                "ru": "❌ Произошла ошибка при загрузке запросов в друзья. Попробуйте позже.",
                "en": "❌ Error loading friend requests. Try again later.",
                "es": "❌ Error al cargar solicitudes de amistad. Inténtalo más tarde."
            },
            "errors.generic_error": {
                "ru": "❌ Произошла ошибка. Попробуйте позже.",
                "en": "❌ An error occurred. Try again later.",
                "es": "❌ Ocurrió un error. Inténtalo más tarde."
            }
        }
    
    def add_translations_to_files(self):
        """Добавляет новые ключи переводов в файлы локализации."""
        locale_dir = Path('bot/i18n/locales')
        
        for lang in ['ru', 'en', 'es']:
            locale_file = locale_dir / f'{lang}.json'
            
            if not locale_file.exists():
                continue
                
            with open(locale_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Добавляем новые ключи
            for key, translations in self.translation_keys.items():
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
        
        print(f"✅ Добавлено {len(self.translation_keys)} новых ключей переводов")
    
    def fix_file(self, file_path: Path) -> int:
        """Исправляет хардкод в одном файле."""
        if not file_path.exists():
            return 0
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        fixes_count = 0
        
        # Применяем замены
        for hardcode, translation_key in self.hardcode_mapping.items():
            # Экранируем специальные символы regex
            escaped_hardcode = re.escape(hardcode)
            
            # Ищем различные варианты кавычек и f-строк
            patterns = [
                f'"{hardcode}"',
                f"'{hardcode}'",
                f'f"{hardcode}"',
                f"f'{hardcode}'",
                hardcode  # Без кавычек
            ]
            
            for pattern in patterns:
                escaped_pattern = re.escape(pattern)
                replacement = f'translator.translate("{translation_key}")'
                
                if re.search(escaped_pattern, content):
                    content = re.sub(escaped_pattern, replacement, content)
                    fixes_count += 1
        
        # Сохраняем файл если были изменения
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Исправлено {fixes_count} проблем в {file_path}")
        
        return fixes_count
    
    def fix_all_handlers(self):
        """Исправляет все handler файлы."""
        handler_patterns = [
            'bot/handlers/**/*.py',
            'bot/keyboards/**/*.py'
        ]
        
        total_fixes = 0
        
        for pattern in handler_patterns:
            for file_path in Path('.').glob(pattern):
                if file_path.is_file():
                    fixes = self.fix_file(file_path)
                    total_fixes += fixes
        
        return total_fixes

def main():
    """Главная функция."""
    fixer = HardcodeFixer()
    
    print("🔧 Начинаю исправление хардкода...")
    
    # Добавляем переводы
    fixer.add_translations_to_files()
    
    # Исправляем файлы
    total_fixes = fixer.fix_all_handlers()
    
    print(f"\n✅ Исправление завершено! Всего исправлено: {total_fixes} проблем")
    
    if total_fixes > 0:
        print("\n📝 Не забудьте:")
        print("1. Проверить что все файлы корректно импортируют translator")
        print("2. Запустить тесты: python3 -m pytest tests/test_no_hardcoded_text.py")
        print("3. Проверить что приложение работает корректно")

if __name__ == "__main__":
    main()
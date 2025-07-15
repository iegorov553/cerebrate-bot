# Решения проблем безопасности Markdown в Telegram боте

## Проблема

Текущий код содержит множество небезопасных конструкций с markdown форматированием:
- f-строки с жирным текстом: `f"**{translator.translate('key')}**"`
- f-строки с кодом: `f"Command: \`{command}\`"`
- f-строки с комбинированным форматированием: `f"**Status:** {status}"`

Это приводит к:
- Ошибкам парсинга markdown в Telegram API
- Проблемам с непредсказуемым отображением текста
- Провалу тестов валидации markdown

## Варианты решений

### 1. Утилитарный класс для форматирования (Простой)

#### Описание
Создание класса `MarkdownFormatter` с безопасными методами форматирования.

#### Реализация
```python
# bot/utils/markdown_formatter.py
class MarkdownFormatter:
    @staticmethod
    def escape(text: str) -> str:
        """Экранирование специальных символов markdown"""
        return text.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
    
    @staticmethod
    def bold(text: str) -> str:
        """Безопасное выделение жирным шрифтом"""
        return f"**{MarkdownFormatter.escape(text)}**"
    
    @staticmethod
    def code(text: str) -> str:
        """Безопасное выделение кодом"""
        return f"`{MarkdownFormatter.escape(text)}`"
    
    @staticmethod
    def title(text: str, emoji: str = "") -> str:
        """Форматирование заголовка"""
        formatted = MarkdownFormatter.bold(text)
        return f"{emoji} {formatted}\n\n" if emoji else f"{formatted}\n\n"
    
    @staticmethod
    def field(label: str, value: str) -> str:
        """Форматирование поля"""
        return f"{MarkdownFormatter.bold(label)} {value}\n"
    
    @staticmethod
    def error(message: str) -> str:
        """Форматирование ошибки"""
        return f"❌ {MarkdownFormatter.bold(message)}"
```

#### Использование
```python
# Было:
f"**{translator.translate('menu.friends')}**\n\n"

# Стало:
MarkdownFormatter.title(translator.translate('menu.friends'))
```

#### Преимущества
- ✅ Простота внедрения
- ✅ Не требует изменения архитектуры
- ✅ Автоматическое экранирование
- ✅ Можно внедрять постепенно

#### Недостатки
- ❌ Не предотвращает использование старых небезопасных методов
- ❌ Требует дисциплины от разработчиков
- ❌ Нет проверки на этапе компиляции

### 2. Расширение Translator (Средний)

#### Описание
Добавление методов форматирования непосредственно в класс `Translator`.

#### Реализация
```python
class Translator:
    # ... существующие методы ...
    
    def format_title(self, key: str, **kwargs) -> str:
        """Форматирование заголовка с переводом"""
        text = self.translate(key, **kwargs)
        return f"**{self._escape_markdown(text)}**\n\n"
    
    def format_field(self, label_key: str, value: str, **kwargs) -> str:
        """Форматирование поля с переводом"""
        label = self.translate(label_key, **kwargs)
        return f"**{self._escape_markdown(label)}:** {value}\n"
    
    def format_error(self, key: str, **kwargs) -> str:
        """Форматирование ошибки"""
        text = self.translate(key, **kwargs)
        return f"❌ **{self._escape_markdown(text)}**"
    
    def format_code(self, text: str) -> str:
        """Форматирование кода"""
        return f"`{self._escape_markdown(text)}`"
    
    def _escape_markdown(self, text: str) -> str:
        """Экранирование markdown символов"""
        return text.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
```

#### Использование
```python
# Было:
f"**{translator.translate('feedback.title')}**\n\n"

# Стало:
translator.format_title('feedback.title')
```

#### Преимущества
- ✅ Интеграция с переводами
- ✅ Удобный API
- ✅ Централизованное управление

#### Недостатки
- ❌ Перегружает класс Translator
- ❌ Не предотвращает использование f-строк
- ❌ Смешивает ответственности

### 3. Шаблонизатор сообщений (Средний)

#### Описание
Система шаблонов для создания сообщений с автоматическим форматированием.

#### Реализация
```python
# bot/utils/message_templates.py
class MessageTemplate:
    def __init__(self, translator: Translator):
        self.translator = translator
    
    def render(self, template_name: str, **kwargs) -> str:
        """Рендеринг шаблона сообщения"""
        template = self._get_template(template_name)
        
        # Обогащаем kwargs функциями форматирования
        format_context = {
            'bold': self._bold,
            'code': self._code,
            'tr': self.translator.translate,
            **kwargs
        }
        
        return template.format(**format_context)
    
    def _get_template(self, name: str) -> str:
        templates = {
            'title_message': "{emoji} {bold(tr(title_key))}\n\n{content}",
            'field_list': "{bold(tr(title_key))}\n{fields}",
            'error_message': "❌ {bold(tr('errors.general'))}\n\n{details}",
            'user_info': "{bold(tr('user.info'))}\n{bold(tr('user.name'))}: {name}\n{bold(tr('user.status'))}: {status}",
            'command_help': "{code(command)} - {tr(description_key)}"
        }
        return templates.get(name, "{content}")
    
    def _bold(self, text: str) -> str:
        escaped = text.replace('*', '\\*').replace('_', '\\_')
        return f"**{escaped}**"
    
    def _code(self, text: str) -> str:
        escaped = text.replace('`', '\\`')
        return f"`{escaped}`"
```

#### Использование
```python
template = MessageTemplate(translator)

# Простое сообщение
message = template.render('title_message', 
                         emoji='📝',
                         title_key='menu.friends',
                         content='Friend list here')

# Сложное сообщение
message = template.render('user_info',
                         name='John Doe',
                         status='active')
```

#### Преимущества
- ✅ Декларативный подход
- ✅ Переиспользуемые шаблоны
- ✅ Автоматическое экранирование
- ✅ Легко тестировать

#### Недостатки
- ❌ Сложность для простых случаев
- ❌ Требует изучения синтаксиса шаблонов
- ❌ Может быть избыточным

### 4. Декоратор для безопасного форматирования (Средний)

#### Описание
Декоратор, который автоматически обрабатывает результат функции для безопасного markdown.

#### Реализация
```python
# bot/utils/markdown_decorators.py
import functools
from typing import Callable, Any

def safe_markdown(func: Callable) -> Callable:
    """Декоратор для безопасного форматирования markdown"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> str:
        result = func(*args, **kwargs)
        return escape_markdown_unsafe(result)
    return wrapper

def escape_markdown_unsafe(text: str) -> str:
    """Поиск и экранирование небезопасных markdown конструкций"""
    import re
    
    # Находим **{...}** и экранируем содержимое
    pattern = r'\*\*([^*]+)\*\*'
    def escape_bold(match):
        content = match.group(1)
        escaped = content.replace('*', '\\*').replace('_', '\\_')
        return f"**{escaped}**"
    
    text = re.sub(pattern, escape_bold, text)
    
    # Находим `{...}` и экранируем содержимое
    pattern = r'`([^`]+)`'
    def escape_code(match):
        content = match.group(1)
        escaped = content.replace('`', '\\`')
        return f"`{escaped}`"
    
    text = re.sub(pattern, escape_code, text)
    
    return text

# Использование:
@safe_markdown
def format_user_message(user_name: str, message: str) -> str:
    return f"**{user_name}**: {message}"

@safe_markdown
def format_command_help(command: str, description: str) -> str:
    return f"`{command}` - {description}"
```

#### Преимущества
- ✅ Автоматическое исправление
- ✅ Не требует изменения существующего кода
- ✅ Прозрачность для разработчика

#### Недостатки
- ❌ Может скрыть реальные проблемы
- ❌ Производительность (regex на каждый вызов)
- ❌ Сложность отладки

### 5. Конфигурационный подход (Средний)

#### Описание
Вынесение форматирования в конфигурационные файлы.

#### Реализация
```python
# bot/i18n/formats.json
{
  "patterns": {
    "title": "**{text}**\n\n",
    "title_with_emoji": "{emoji} **{text}**\n\n",
    "field": "**{label}:** {value}\n",
    "code": "`{text}`",
    "error": "❌ **{title}**\n\n{details}",
    "success": "✅ **{title}**\n\n{details}",
    "warning": "⚠️ **{title}**\n\n{details}",
    "info": "ℹ️ **{title}**\n\n{details}",
    "list_item": "• {text}\n",
    "numbered_item": "{number}. {text}\n"
  }
}

# bot/utils/message_formatter.py
import json
from pathlib import Path
from typing import Dict, Any

class ConfigurableFormatter:
    def __init__(self, config_path: str = "bot/i18n/formats.json"):
        self.config_path = Path(config_path)
        self._patterns = self._load_patterns()
    
    def _load_patterns(self) -> Dict[str, str]:
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('patterns', {})
    
    def format(self, pattern_name: str, **kwargs) -> str:
        """Форматирование с использованием паттерна"""
        pattern = self._patterns.get(pattern_name, "{text}")
        
        # Экранируем все переменные
        escaped_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                escaped_kwargs[key] = self._escape_markdown(value)
            else:
                escaped_kwargs[key] = value
        
        return pattern.format(**escaped_kwargs)
    
    def _escape_markdown(self, text: str) -> str:
        return text.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
```

#### Использование
```python
formatter = ConfigurableFormatter()

# Заголовок
title = formatter.format('title', text=translator.translate('menu.friends'))

# Поле
field = formatter.format('field', 
                        label=translator.translate('user.name'),
                        value='John Doe')

# Ошибка
error = formatter.format('error',
                        title=translator.translate('errors.general'),
                        details='Connection failed')
```

#### Преимущества
- ✅ Легко изменять стили
- ✅ Консистентность оформления
- ✅ Переиспользование паттернов
- ✅ Возможность A/B тестирования стилей

#### Недостатки
- ❌ Дополнительная сложность
- ❌ Файл конфигурации нужно поддерживать
- ❌ Менее гибко для сложных случаев

### 6. Строгая типизация + Линтер (Строгий)

#### Описание
Использование системы типов для принуждения к безопасному использованию markdown.

#### Реализация
```python
# bot/utils/safe_types.py
from typing import NewType, Union, TypeVar, Generic

# Создаем специальные типы
SafeMarkdown = NewType('SafeMarkdown', str)
UnsafeText = NewType('UnsafeText', str)
PlainText = NewType('PlainText', str)

class MarkdownFormatter:
    @staticmethod
    def bold(text: Union[UnsafeText, PlainText]) -> SafeMarkdown:
        """Безопасное выделение жирным"""
        escaped = str(text).replace('*', '\\*').replace('_', '\\_')
        return SafeMarkdown(f"**{escaped}**")
    
    @staticmethod
    def code(text: Union[UnsafeText, PlainText]) -> SafeMarkdown:
        """Безопасное выделение кодом"""
        escaped = str(text).replace('`', '\\`')
        return SafeMarkdown(f"`{escaped}`")
    
    @staticmethod
    def combine(*parts: SafeMarkdown) -> SafeMarkdown:
        """Комбинирование безопасных частей"""
        return SafeMarkdown("".join(parts))
    
    @staticmethod
    def plain(text: str) -> PlainText:
        """Маркировка обычного текста"""
        return PlainText(text)

# Функции отправки принимают только безопасный markdown
async def send_message(chat_id: int, text: SafeMarkdown) -> None:
    # Здесь мы уверены, что text безопасен
    await bot.send_message(chat_id, text, parse_mode='Markdown')

# Кастомный mypy плагин для проверки
# mypy_plugin.py
def check_f_string_safety(node):
    """Проверка f-строк на безопасность"""
    if has_markdown_in_fstring(node):
        return "Use MarkdownFormatter instead of f-strings with markdown"
    return None
```

#### Использование
```python
# Безопасное использование
user_name = MarkdownFormatter.plain("John Doe")
title = MarkdownFormatter.bold(translator.translate('menu.friends'))
message = MarkdownFormatter.combine(title, user_name)

await send_message(chat_id, message)

# Это не скомпилируется с mypy:
# await send_message(chat_id, f"**{user_name}**")  # Ошибка типов!
```

#### Преимущества
- ✅ Гарантии на уровне типов
- ✅ Проверка на этапе компиляции
- ✅ Невозможно использовать небезопасные методы
- ✅ Самодокументирующийся код

#### Недостатки
- ❌ Сложность внедрения
- ❌ Требует изучения системы типов
- ❌ Может быть избыточным для простых случаев
- ❌ Нужны дополнительные инструменты (mypy плагин)

### 7. Builder Pattern для сообщений (Строгий)

#### Описание
Использование паттерна Builder для пошагового создания безопасных сообщений.

#### Реализация
```python
# bot/utils/message_builder.py
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

@dataclass
class MessagePart:
    content: str
    is_safe: bool = True

class MessageBuilder:
    def __init__(self, translator: Translator):
        self.translator = translator
        self._parts: List[MessagePart] = []
    
    def add_title(self, key: str, emoji: str = "", **kwargs) -> 'MessageBuilder':
        """Добавить заголовок"""
        text = self.translator.translate(key, **kwargs)
        escaped = self._escape(text)
        content = f"{emoji} **{escaped}**\n\n" if emoji else f"**{escaped}**\n\n"
        self._parts.append(MessagePart(content, True))
        return self
    
    def add_field(self, label_key: str, value: str, **kwargs) -> 'MessageBuilder':
        """Добавить поле"""
        label = self.translator.translate(label_key, **kwargs)
        escaped_label = self._escape(label)
        escaped_value = self._escape(value)
        content = f"**{escaped_label}:** {escaped_value}\n"
        self._parts.append(MessagePart(content, True))
        return self
    
    def add_code(self, text: str) -> 'MessageBuilder':
        """Добавить код"""
        escaped = self._escape_code(text)
        content = f"`{escaped}`"
        self._parts.append(MessagePart(content, True))
        return self
    
    def add_list_item(self, text: str, bullet: str = "•") -> 'MessageBuilder':
        """Добавить элемент списка"""
        escaped = self._escape(text)
        content = f"{bullet} {escaped}\n"
        self._parts.append(MessagePart(content, True))
        return self
    
    def add_separator(self) -> 'MessageBuilder':
        """Добавить разделитель"""
        self._parts.append(MessagePart("\n", True))
        return self
    
    def add_raw(self, text: str, safe: bool = False) -> 'MessageBuilder':
        """Добавить сырой текст (используйте осторожно)"""
        if not safe:
            text = self._escape(text)
        self._parts.append(MessagePart(text, safe))
        return self
    
    def build(self) -> str:
        """Собрать финальное сообщение"""
        if not all(part.is_safe for part in self._parts):
            raise ValueError("Message contains unsafe parts")
        
        result = "".join(part.content for part in self._parts)
        
        # Финальная валидация
        self._validate_markdown(result)
        
        return result
    
    def _escape(self, text: str) -> str:
        """Экранирование markdown символов"""
        return text.replace('*', '\\*').replace('_', '\\_').replace('`', '\\`')
    
    def _escape_code(self, text: str) -> str:
        """Экранирование для кода"""
        return text.replace('`', '\\`')
    
    def _validate_markdown(self, text: str) -> None:
        """Валидация markdown перед отправкой"""
        # Проверка на сбалансированность **
        if text.count('**') % 2 != 0:
            raise ValueError("Unbalanced ** in markdown")
        
        # Проверка на сбалансированность `
        if text.count('`') % 2 != 0:
            raise ValueError("Unbalanced ` in markdown")
        
        # Дополнительные проверки...
```

#### Использование
```python
# Создание сложного сообщения
message = (MessageBuilder(translator)
          .add_title('menu.friends', emoji='👥')
          .add_separator()
          .add_field('user.name', 'John Doe')
          .add_field('user.status', 'active')
          .add_separator()
          .add_code('/add_friend @username')
          .add_list_item('Accept friend request')
          .add_list_item('Decline friend request')
          .build())

await send_message(chat_id, message)
```

#### Преимущества
- ✅ Пошаговое создание сообщений
- ✅ Валидация на каждом этапе
- ✅ Читаемый код
- ✅ Переиспользование логики
- ✅ Автоматическое экранирование

#### Недостатки
- ❌ Более verbose код
- ❌ Может быть избыточным для простых сообщений
- ❌ Требует изучения API

### 8. Wrapper для Telegram API (Строгий)

#### Описание
Обертка над Telegram API с автоматической валидацией и исправлением markdown.

#### Реализация
```python
# bot/utils/safe_telegram_bot.py
import re
from typing import Optional, Dict, Any
from telegram import Bot
from telegram.error import BadRequest
import logging

logger = logging.getLogger(__name__)

class SafeTelegramBot:
    def __init__(self, bot: Bot):
        self.bot = bot
        self._stats = {
            'messages_sent': 0,
            'markdown_errors_fixed': 0,
            'fallback_to_plain': 0
        }
    
    async def send_message(self, 
                          chat_id: int, 
                          text: str, 
                          parse_mode: str = 'Markdown',
                          **kwargs) -> Any:
        """Безопасная отправка сообщения с автоматическим исправлением"""
        
        if parse_mode == 'Markdown':
            # Попытка автоматического исправления
            safe_text, was_fixed = self._sanitize_markdown(text)
            
            if was_fixed:
                self._stats['markdown_errors_fixed'] += 1
                logger.info(f"Fixed markdown in message to {chat_id}")
            
            try:
                result = await self.bot.send_message(
                    chat_id, safe_text, parse_mode=parse_mode, **kwargs
                )
                self._stats['messages_sent'] += 1
                return result
                
            except BadRequest as e:
                if "can't parse" in str(e).lower():
                    # Fallback на plain text
                    logger.warning(f"Markdown parsing failed for {chat_id}, falling back to plain text")
                    self._stats['fallback_to_plain'] += 1
                    return await self.bot.send_message(
                        chat_id, self._strip_markdown(text), parse_mode=None, **kwargs
                    )
                raise
        else:
            # Для не-markdown сообщений просто отправляем как есть
            return await self.bot.send_message(chat_id, text, parse_mode=parse_mode, **kwargs)
    
    def _sanitize_markdown(self, text: str) -> tuple[str, bool]:
        """Автоматическое исправление markdown"""
        original = text
        was_fixed = False
        
        # Исправление несбалансированных **
        while True:
            bold_count = text.count('**')
            if bold_count % 2 == 0:
                break
            
            # Находим последний ** и удаляем его
            last_pos = text.rfind('**')
            if last_pos != -1:
                text = text[:last_pos] + text[last_pos + 2:]
                was_fixed = True
            else:
                break
        
        # Исправление несбалансированных `
        while True:
            code_count = text.count('`')
            if code_count % 2 == 0:
                break
            
            # Находим последний ` и удаляем его
            last_pos = text.rfind('`')
            if last_pos != -1:
                text = text[:last_pos] + text[last_pos + 1:]
                was_fixed = True
            else:
                break
        
        # Экранирование опасных символов внутри markdown
        text = self._escape_dangerous_chars(text)
        
        return text, was_fixed or (text != original)
    
    def _escape_dangerous_chars(self, text: str) -> str:
        """Экранирование опасных символов"""
        # Находим содержимое ** и экранируем в нем _ и *
        def escape_in_bold(match):
            content = match.group(1)
            escaped = content.replace('*', '\\*').replace('_', '\\_')
            return f"**{escaped}**"
        
        text = re.sub(r'\*\*([^*]+)\*\*', escape_in_bold, text)
        
        # Находим содержимое ` и экранируем в нем `
        def escape_in_code(match):
            content = match.group(1)
            escaped = content.replace('`', '\\`')
            return f"`{escaped}`"
        
        text = re.sub(r'`([^`]+)`', escape_in_code, text)
        
        return text
    
    def _strip_markdown(self, text: str) -> str:
        """Удаление всех markdown символов"""
        # Удаляем ** но оставляем содержимое
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        
        # Удаляем ` но оставляем содержимое
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        return text
    
    def get_stats(self) -> Dict[str, int]:
        """Получить статистику работы"""
        return self._stats.copy()
    
    def reset_stats(self) -> None:
        """Сбросить статистику"""
        self._stats = {
            'messages_sent': 0,
            'markdown_errors_fixed': 0,
            'fallback_to_plain': 0
        }
```

#### Использование
```python
# Инициализация
safe_bot = SafeTelegramBot(bot)

# Отправка сообщения (автоматически исправляется)
await safe_bot.send_message(chat_id, f"**{user_name}** is online")

# Получение статистики
stats = safe_bot.get_stats()
print(f"Fixed {stats['markdown_errors_fixed']} markdown errors")
```

#### Преимущества
- ✅ Полностью прозрачно для существующего кода
- ✅ Автоматическое исправление ошибок
- ✅ Fallback механизм
- ✅ Статистика и мониторинг
- ✅ Логирование проблем

#### Недостатки
- ❌ Может скрыть реальные проблемы в коде
- ❌ Производительность (regex обработка)
- ❌ Может изменить интенцию автора

### 9. Pre-commit хуки для проверки (Строгий)

#### Описание
Автоматическая проверка кода на этапе коммита для предотвращения небезопасных конструкций.

#### Реализация
```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: check-unsafe-markdown
        name: Check for unsafe markdown in f-strings
        entry: python scripts/check_markdown_safety.py
        language: python
        files: \.py$
        args: ['--fix']
      
      - id: validate-markdown-in-translations
        name: Validate markdown in translation files
        entry: python scripts/validate_translation_markdown.py
        language: python
        files: bot/i18n/locales/.*\.json$
```

```python
# scripts/check_markdown_safety.py
import re
import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Optional

class MarkdownSafetyChecker:
    def __init__(self, fix_mode: bool = False):
        self.fix_mode = fix_mode
        self.issues_found = []
    
    def check_file(self, filepath: Path) -> bool:
        """Проверка файла на небезопасные markdown конструкции"""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            issues = self._check_line(line, line_num, filepath)
            
            if issues and self.fix_mode:
                # Автоматическое исправление
                fixed_line = self._fix_line(line)
                lines[line_num - 1] = fixed_line
        
        if self.fix_mode and '\n'.join(lines) != original_content:
            # Записываем исправленный файл
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            print(f"🔧 Fixed markdown issues in {filepath}")
        
        return len(self.issues_found) == 0
    
    def _check_line(self, line: str, line_num: int, filepath: Path) -> List[str]:
        """Проверка строки на проблемы"""
        issues = []
        
        # Паттерны для опасных конструкций
        patterns = [
            (r'f"[^"]*\*\*.*\{.*\}.*\*\*[^"]*"', "f-string with bold markdown around variables"),
            (r"f'[^']*\*\*.*\{.*\}.*\*\*[^']*'", "f-string with bold markdown around variables"),
            (r'f"[^"]*`.*\{.*\}`[^"]*"', "f-string with code markdown around variables"),
            (r"f'[^']*`.*\{.*\}`[^']*'", "f-string with code markdown around variables"),
        ]
        
        for pattern, description in patterns:
            if re.search(pattern, line):
                issue = f"{filepath}:{line_num}: {description}"
                issues.append(issue)
                self.issues_found.append(issue)
        
        return issues
    
    def _fix_line(self, line: str) -> str:
        """Автоматическое исправление строки"""
        # Замена f"**{var}**" на MarkdownFormatter.bold(var)
        line = re.sub(
            r'f"([^"]*)\*\*\{([^}]+)\}\*\*([^"]*)"',
            r'f"\1" + MarkdownFormatter.bold(\2) + f"\3"',
            line
        )
        
        # Замена f"`{var}`" на MarkdownFormatter.code(var)
        line = re.sub(
            r'f"([^"]*)`\{([^}]+)\}`([^"]*)"',
            r'f"\1" + MarkdownFormatter.code(\2) + f"\3"',
            line
        )
        
        return line

def main():
    parser = argparse.ArgumentParser(description='Check for unsafe markdown in Python files')
    parser.add_argument('files', nargs='*', help='Files to check')
    parser.add_argument('--fix', action='store_true', help='Automatically fix issues')
    
    args = parser.parse_args()
    
    checker = MarkdownSafetyChecker(fix_mode=args.fix)
    
    all_good = True
    for filepath in args.files:
        if not checker.check_file(Path(filepath)):
            all_good = False
    
    if not all_good:
        print("\n❌ Found unsafe markdown patterns!")
        for issue in checker.issues_found:
            print(f"  {issue}")
        
        if not args.fix:
            print("\nUse --fix to automatically fix these issues")
        
        sys.exit(1)
    else:
        print("✅ All markdown patterns are safe!")

if __name__ == '__main__':
    main()
```

#### Использование
```bash
# Проверка при коммите
git commit -m "Add new feature"

# Ручная проверка
python scripts/check_markdown_safety.py bot/handlers/*.py

# Автоматическое исправление
python scripts/check_markdown_safety.py bot/handlers/*.py --fix
```

#### Преимущества
- ✅ Предотвращает проблемы на этапе коммита
- ✅ Автоматическое исправление
- ✅ Интеграция с CI/CD
- ✅ Обучающий эффект для команды

#### Недостатки
- ❌ Может замедлить процесс коммита
- ❌ Автоматические исправления могут быть неточными
- ❌ Требует настройки инфраструктуры

### 10. Комбинированный строгий подход (Максимально строгий)

#### Описание
Комбинация всех строгих методов для максимальной безопасности.

#### Реализация
```python
# Комбинация компонентов:
# 1. Строгие типы
from typing import NewType
SafeMarkdown = NewType('SafeMarkdown', str)

# 2. Builder для сложных сообщений
class StrictMessageBuilder:
    def build(self) -> SafeMarkdown:
        result = "".join(part.content for part in self._parts)
        self._validate_markdown(result)
        return SafeMarkdown(result)

# 3. Обертка для бота
class StrictSafeTelegramBot:
    async def send_message(self, chat_id: int, text: SafeMarkdown, **kwargs):
        return await self.bot.send_message(chat_id, text, **kwargs)

# 4. Pre-commit хуки
# 5. Линтер правила
# 6. Автоматические тесты
```

#### Архитектура
```python
# Полная архитектура безопасности
class MarkdownSafetySystem:
    def __init__(self):
        self.formatter = MarkdownFormatter()
        self.validator = MarkdownValidator()
        self.bot_wrapper = SafeTelegramBot()
    
    def create_message(self) -> MessageBuilder:
        """Создать безопасный билдер сообщений"""
        return MessageBuilder(self.formatter, self.validator)
    
    def send_message(self, chat_id: int, message: SafeMarkdown):
        """Отправить проверенное сообщение"""
        return self.bot_wrapper.send_message(chat_id, message)
```

#### Преимущества
- ✅ Максимальная безопасность
- ✅ Множественные уровни защиты
- ✅ Автоматическое исправление
- ✅ Проверки на всех этапах

#### Недостатки
- ❌ Высокая сложность
- ❌ Большие затраты на внедрение
- ❌ Может быть избыточным
- ❌ Требует обучения команды

## Сравнительная таблица

| Подход | Сложность | Безопасность | Скорость внедрения | Обслуживание |
|--------|-----------|--------------|-------------------|--------------|
| Утилитарный класс | Низкая | Средняя | Быстрая | Простое |
| Расширение Translator | Средняя | Средняя | Средняя | Простое |
| Шаблонизатор | Средняя | Высокая | Средняя | Среднее |
| Декоратор | Средняя | Средняя | Быстрая | Среднее |
| Конфигурационный | Средняя | Высокая | Средняя | Среднее |
| Строгая типизация | Высокая | Очень высокая | Медленная | Сложное |
| Builder Pattern | Средняя | Высокая | Средняя | Среднее |
| Wrapper для API | Средняя | Высокая | Быстрая | Среднее |
| Pre-commit хуки | Средняя | Высокая | Средняя | Среднее |
| Комбинированный | Очень высокая | Максимальная | Очень медленная | Очень сложное |

## Рекомендации

### Для текущей ситуации (быстрое исправление):
1. **Утилитарный класс** + **Wrapper для API** - быстро и эффективно

### Для долгосрочного развития:
1. **Builder Pattern** + **Pre-commit хуки** - баланс безопасности и удобства

### Для критически важных систем:
1. **Строгая типизация** + **Комбинированный подход** - максимальная безопасность

### Поэтапное внедрение:
1. **Этап 1**: Утилитарный класс + Wrapper для API
2. **Этап 2**: Pre-commit хуки + автоматические тесты
3. **Этап 3**: Builder Pattern для сложных сообщений
4. **Этап 4**: Строгая типизация (опционально)

---

*Этот документ должен быть обновлен при изменении требований к безопасности markdown.*
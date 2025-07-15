# 🚫 Запрещённые действия и анти-паттерны

Критически важный справочник того, что НИКОГДА нельзя делать в проекте.

## 🗺️ Навигация  
- ← [README.md](README.md) - Назад к карте AI документации
- → [workflows/error-patterns.md](workflows/error-patterns.md) - Типичные ошибки

## 🚨 КРИТИЧЕСКИЕ ЗАПРЕТЫ

### 🔴 Пуш в main ветку
```bash
# ❌ АБСОЛЮТНО ЗАПРЕЩЕНО
git push origin main

# ✅ ТОЛЬКО staging разрешён
git push origin staging
```
**Последствия**: Нарушение production pipeline, потенциальные проблемы в продакшене  
**Исключения**: НЕТ исключений

### 🔴 Использование python вместо python3
```bash
# ❌ ЗАПРЕЩЕНО в этом проекте
python script.py
python -m pytest

# ✅ ОБЯЗАТЕЛЬНО python3
python3 script.py  
python3 -m pytest
```
**Последствия**: Несовместимость версий, поломка CI/CD

### 🔴 Коммиты без прохождения тестов
```bash
# ❌ НЕЛЬЗЯ коммитить при failing tests
git commit -m "fix" && git push  # Тесты не запущены!

# ✅ ОБЯЗАТЕЛЬНАЯ последовательность
python3 -m pytest                # Все тесты должны пройти
ruff check .                      # Линтинг  
ruff format .                     # Форматирование
mypy .                           # Проверка типов
bandit -r .                      # Security scan
# Обновить документацию
git add .
git commit -m "message"
git push origin staging
```

### 🔴 Hardcoded строки интерфейса
```python
# ❌ СТРОГО ЗАПРЕЩЕНО
await query.edit_message_text("Настройки сохранены")
button_text = "Нажми здесь"
error_message = "Something went wrong"

# ✅ ОБЯЗАТЕЛЬНО через переводы
await query.edit_message_text(translator.translate("settings.saved"))
button_text = translator.translate("buttons.click_here")
error_message = translator.translate("errors.general")
```

## 🏗️ АРХИТЕКТУРНЫЕ ЗАПРЕТЫ

### 🚫 Settings Handler Usage
**Причина**: Settings handler был удалён из архитектуры

```python
# ❌ ЗАПРЕЩЕНО - handler не существует
callback_data = "settings_toggle_notifications"
callback_data = "settings_anything"

# ✅ ПРАВИЛЬНО - всё в questions handler
callback_data = "questions_toggle_notifications"
callback_data = "questions_show_settings"
```

### 🚫 Отдельные методы для простых операций
```python
# ❌ ИЗБЫТОЧНАЯ сложность для toggle
elif data == "simple_toggle":
    await self._handle_simple_toggle(query, translator)

async def _handle_simple_toggle(self, query, translator):  # НЕ НУЖЕН!
    success = await simple_operation()
    await self._handle_menu_refresh(query, translator)

# ✅ ПРАВИЛЬНО - inline логика
elif data == "simple_toggle":
    success = await simple_operation()
    await self._handle_menu_refresh(query, translator)
```

### 🚫 Добавление методов в файлы >400 строк
**Текущие проблемные файлы**:
- `friends_callbacks.py` - 719 строк
- `questions_callbacks.py` - 642 строки  
- `admin_callbacks.py` - 537 строк

```python
# ❌ ЗАПРЕЩЕНО в больших файлах
async def new_complex_method(self):  # НЕ добавлять в большие handlers!
    # Много логики

# ✅ ТОЛЬКО inline логика в больших файлах
elif data == "new_action":
    # 2-5 строк inline кода
    success = await operation()
    await refresh_menu()
```

### 🚫 Создание новых handlers без крайней необходимости
```python
# ❌ НЕ создавать новые handlers
class UnnecessaryHandler(BaseCallbackHandler):  # Лишний handler!
    
# ✅ Использовать существующие handlers
# questions_* → QuestionsCallbackHandler
# friends_* → FriendsCallbackHandler
# admin_* → AdminCallbackHandler
```

## 💾 DATABASE ЗАПРЕТЫ

### 🚫 Забывать cache invalidation
```python
# ❌ КРИТИЧЕСКАЯ ошибка - нет invalidation
await user_ops.update_user_settings(user_id, {"key": "value"})
# Забыли: await self.user_cache.invalidate(f"user_settings_{user_id}")

# ✅ ОБЯЗАТЕЛЬНО после update
await user_ops.update_user_settings(user_id, {"key": "value"})
await self.user_cache.invalidate(f"user_settings_{user_id}")  # КРИТИЧНО!
```

### 🚫 N+1 Database Queries
```python
# ❌ ПРОИЗВОДИТЕЛЬНОСТЬ убийца
friends_data = []
for friend_id in friend_ids:
    friend = await friend_ops.get_friend(friend_id)  # N запросов!
    friends_data.append(friend)

# ✅ BATCH операции
friends_data = await friend_ops.get_multiple_friends(friend_ids)  # 1 запрос
```

### 🚫 Операции без authorization checks
```python
# ❌ SECURITY риск
await question_ops.delete_question(question_id)  # Кто угодно может удалить!

# ✅ ОБЯЗАТЕЛЬНАЯ проверка ownership
question = await question_ops.get_question_details(question_id)
if not question or question.get('user_id') != user.id:
    raise PermissionError("Unauthorized")
await question_ops.delete_question(question_id)
```

## 🔧 DEVELOPMENT ЗАПРЕТЫ

### 🚫 Коммиты без новых функций без тестов
```python
# ❌ ЗАПРЕЩЕНО добавлять функции без тестов
def new_important_feature():
    # Сложная логика без тестов - НЕДОПУСТИМО!
    
# ✅ ОБЯЗАТЕЛЬНО покрывать тестами
def new_important_feature():
    # Сложная логика
    
def test_new_important_feature():
    # Соответствующий тест
```

### 🚫 Игнорирование code size limits
```python
# ❌ НЕ предлагать рефакторинг при превышении лимитов
# Файл 500+ строк - молчать о проблеме
# Функция 80+ строк - ничего не говорить

# ✅ ОБЯЗАТЕЛЬНО предлагать рефакторинг
# При файле >400 строк → предложить разбиение
# При функции >50 строк → предложить разбиение на подфункции
```

### 🚫 Неясные объяснения и terms без расшифровки
```markdown
# ❌ ПЛОХО
"Используй Repository Pattern"  # Что это такое?
"Добавь dependency injection"   # Как именно?

# ✅ ПРАВИЛЬНО  
"Используй Repository Pattern - паттерн доступа к данным через отдельные классы"
"Добавь dependency injection - передавай зависимости через конструкторы"
```

### 🚫 Работа без согласования изменений
```bash
# ❌ ЗАПРЕЩЕНО менять без спроса
# Изменения в Supabase схеме
# Изменения в Telegram API настройках
# Установка новых tools без проверки доступности

# ✅ ОБЯЗАТЕЛЬНО спрашивать пользователя
"Нужно изменить схему БД. Согласен?"
"Требуется установить новый tool X. Есть ли права?"
```

### 🚫 Начало работы без planning
```markdown
# ❌ ЗАПРЕЩЕНО сразу код писать
User: "Добавь новую функцию X"
Assistant: [сразу пишет код]  # БЕЗ ПЛАНА!

# ✅ ОБЯЗАТЕЛЬНЫЙ planning workflow
1. Оценить uncertainty (0-1)
2. Если >0.1 → задать уточняющие вопросы  
3. Сформировать подробный план
4. Согласовать с пользователем
5. Только потом начать реализацию
```

### 🚫 Использование устаревших tools
```toml
# ❌ БОЛЬШЕ НЕ ИСПОЛЬЗУЕТСЯ
flake8 = "6.0.0"
black = "23.12.1"
isort = "5.12.0"

# ✅ ТЕКУЩИЙ STANDARD
ruff = "0.1.9"  # Заменяет flake8, black, isort
```

### 🚫 Пропуск обязательных инструментов
```bash
# ❌ НЕ использовать обязательные tools
# Пропускать mypy type checking
# Игнорировать bandit security scan
# Не запускать pip-audit
# Работать без Docker

# ✅ ОБЯЗАТЕЛЬНЫЕ инструменты
mypy .              # Type checking
bandit -r .         # Security scan  
pip-audit          # Dependency vulnerabilities
pytest             # Testing
pre-commit         # Git hooks
```

### 🚫 Docker без production конфигурации
```dockerfile
# ❌ ТОЛЬКО development настройки
FROM python:3.8  # Нет production optimizations

# ✅ PRODUCTION-ready образ описан в Dockerfile
# Используй существующий Dockerfile для production
```

### 🚫 Изменения сторонних сервисов без согласования
```python
# ❌ НЕ МЕНЯТЬ без согласования с пользователем
SUPABASE_CONFIG = {...}  # Изменение может сломать БД
TELEGRAM_API_SETTINGS = {...}  # Изменение может сломать бота
```

### 🚫 Работа без backup стратегии
```bash
# ❌ Опасные операции без backup
rm -rf important_data/
git reset --hard HEAD~10  # Потеря данных!

# ✅ ВСЕГДА создавать backup
cp -r important_data/ backup_$(date +%Y%m%d)/
git branch backup_branch
```

## 📝 DOCUMENTATION ЗАПРЕТЫ

### 🚫 Создание документации без запроса
```markdown
# ❌ НЕ создавать .md файлы без explicit request
README_NEW.md
FEATURES.md  
TUTORIAL.md

# ✅ Обновлять только СУЩЕСТВУЮЩИЕ файлы документации
```

### 🚫 Дублирование информации в документах
```markdown
# ❌ НЕ копировать информацию между файлами
# docs/file1.md и docs/file2.md с одинаковой информацией

# ✅ Ссылки на единый источник истины
См. [project-facts.md](project-facts.md) для критических фактов
```

### 🚫 Документация на русском (кроме AI docs)
```markdown
# ❌ Пользовательская документация на русском
# README.md, docs/DEPLOYMENT.md на русском

# ✅ Вся проектная документация на английском
# Только docs/ai/ может быть на русском для Claude
```

### 🚫 Коммиты без обновления документации
```markdown
# ❌ ЗАБЫТЬ обновить документацию
git commit -m "Добавил новую функцию"  # Документация не обновлена!

# ✅ ОБЯЗАТЕЛЬНО обновлять перед коммитом
1. Реализовать функцию
2. Обновить соответствующие .md файлы
3. Проверить что CLAUDE.md актуален
4. Добавить retro запись в docs/ai/retro.md
5. Коммитить все изменения вместе
```

### 🚫 Коммиты без ретроспективы
```markdown
# ❌ ЗАБЫТЬ retro анализ
git commit -m "Исправил проблему"  # Retro не добавлен!

# ✅ ОБЯЗАТЕЛЬНО добавлять в docs/ai/retro.md:
## Commit — <commit-message>

### Что получилось
- Успешные аспекты работы

### Что не получилось  
- Проблемы и сложности

### Причина проблемы (5 Why)
- Корневой анализ причин
```

### 🚫 Неправильная структура CLAUDE.md
```markdown
# ❌ CLAUDE.md как dump всей информации
# Длинный файл с кучей деталей
# Отсутствие ссылок на документацию
# Непонятная навигация

# ✅ CLAUDE.md как навигатор
# Краткое описание проекта
# Ссылки на детальную документацию  
# Быстрая навигация для разработчика/ИИ
```

## 🧪 TESTING ЗАПРЕТЫ

### 🚫 Коммиты без тестов новой функциональности
```python
# ❌ Новая функция без тестов
def new_important_feature():
    # Сложная логика без тестов
    
# ✅ ОБЯЗАТЕЛЬНО покрывать тестами
def new_important_feature():
    # Сложная логика
    
def test_new_important_feature():
    # Тест для новой функции
```

### 🚫 Интерактивные git команды в CI/CD
```bash
# ❌ НЕЛЬЗЯ в автоматизации
git rebase -i  # Требует interaction
git add -i     # Требует interaction

# ✅ Только неинтерактивные команды
git rebase HEAD~3
git add .
```

## 🚨 SECURITY ЗАПРЕТЫ

### 🚫 Логирование sensitive данных
```python
# ❌ SECURITY риск
self.logger.info("User auth", token=user_token)  # Секрет в логах!
self.logger.debug("API call", api_key=api_key)   # Секрет в логах!

# ✅ БЕЗОПАСНОЕ логирование
self.logger.info("User auth", user_id=user.id)   # Только ID
self.logger.debug("API call", status="success")  # Только статус
```

### 🚫 Коммиты secrets в repository
```bash
# ❌ НИКОГДА не коммитить
TELEGRAM_BOT_TOKEN="123456:ABCDEF"  # В коде!
DATABASE_PASSWORD="secret123"       # В файлах!

# ✅ ТОЛЬКО environment variables
export TELEGRAM_BOT_TOKEN="..."
export DATABASE_PASSWORD="..."
```

### 🚫 Hardcoded admin credentials
```python
# ❌ SECURITY катастрофа
ADMIN_USER_ID = 123456789  # Hardcoded в коде!

# ✅ Из environment variables
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
```

## 📊 PERFORMANCE ЗАПРЕТЫ

### 🚫 Blocking операции в async handlers
```python
# ❌ БЛОКИРУЕТ event loop
import time
time.sleep(5)  # Вся система зависнет!

import requests
response = requests.get(url)  # Блокирующий HTTP запрос

# ✅ АСИНХРОННЫЕ операции
import asyncio
await asyncio.sleep(5)

import aiohttp
async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
        data = await response.json()
```

### 🚫 Операции без timeout
```python
# ❌ Может зависнуть навсегда
await long_running_operation()  # Нет timeout!

# ✅ ОБЯЗАТЕЛЬНЫЙ timeout
try:
    await asyncio.wait_for(long_running_operation(), timeout=30.0)
except asyncio.TimeoutError:
    self.logger.error("Operation timeout")
```

## 🔄 DEVELOPMENT WORKFLOW ЗАПРЕТЫ

### 🚫 Работа напрямую с production данными
```python
# ❌ ОПАСНО для production
if ENVIRONMENT == "production":
    # Тестирование на реальных пользователях!
    
# ✅ Разделение environments
if ENVIRONMENT == "development":
    # Тестирование только в dev
```

### 🚫 Force push в shared ветки
```bash
# ❌ ОПАСНО для команды
git push --force origin staging  # Перепишет историю!

# ✅ БЕЗОПАСНЫЕ операции
git push origin staging
git push --force-with-lease origin feature-branch  # Только для personal веток
```

### 🚫 Большие файлы в commits
```bash
# ❌ НЕ коммитить большие файлы
git add large_dataset.csv      # 100MB файл
git add video_tutorial.mp4     # Медиа файлы
git add node_modules/          # Dependencies

# ✅ Использовать .gitignore
echo "*.csv" >> .gitignore
echo "*.mp4" >> .gitignore  
echo "node_modules/" >> .gitignore
```

## ⚠️ WARNING SIGNS - Когда остановиться

### 🟡 Если файл становится >400 строк
**СТОП!** Не добавляй новые методы. Используй только inline логику или планируй рефакторинг.

### 🟡 Если создаёшь 3+ похожих метода
**СТОП!** Ищи существующий паттерн или создавай utility function.

### 🟡 Если логика повторяется в разных местах
**СТОП!** Выноси в shared utilities или service класс.

### 🟡 Если добавляешь новый dependency
**СТОП!** Проверь alternatives среди существующих dependencies.

### 🟡 Если изменяешь core архитектуру
**СТОП!** Согласуй с пользователем через planning phase.

## 📋 Checklist перед любым изменением

### ✅ Pre-change checklist:
- [ ] Прочитал ли docs/ai/project-facts.md?
- [ ] Проверил ли существующие аналогичные решения?
- [ ] Соблюдаю ли size limits файлов?
- [ ] Планирую ли тесты для новой функциональности?
- [ ] Не создаю ли дублирующий код?

### ✅ Pre-commit checklist:
- [ ] Все тесты проходят (`python3 -m pytest`)?
- [ ] Код отформатирован (`ruff format .`)?
- [ ] Нет новых ошибок (`ruff check .`)?
- [ ] Документация обновлена?
- [ ] Коммит в staging ветку?

---

**Последнее обновление**: 2025-07-15 22:35  
**Критичность**: МАКСИМАЛЬНАЯ - нарушение = серьёзные проблемы  
**Применимость**: ВСЕ изменения в проекте без исключений
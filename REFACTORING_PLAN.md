# План рефакторинга архитектуры обработчиков

## Проблема
Текущая структура обработчиков нарушает принцип единственной ответственности и содержит монолитные файлы:
- `command_handlers.py` - **736 строк** (11 команд смешанного назначения)
- `callbacks/friends_callbacks.py` - **719 строк** (вся социальная функциональность)
- `callbacks/questions_callbacks.py` - **642 строки** (система вопросов)
- `callbacks/admin_callbacks.py` - **537 строк** (административные функции)

## Цели рефакторинга
1. **Разделение ответственности** - каждый файл должен отвечать за один домен
2. **Размер файлов** - не более 200-300 строк на файл
3. **Логическое группирование** - связанные функции в одном модуле
4. **Переиспользование** - общая логика в базовых классах
5. **Тестируемость** - изолированные модули легче тестировать

## Этап 1: Разделение command_handlers.py (ПРИОРИТЕТ 1)

### Текущее состояние (736 строк, 11 команд):
```
command_handlers.py:
├── start_command          # регистрация + главное меню
├── settings_command       # меню настроек
├── history_command        # веб-интерфейс
├── add_friend_command     # добавление друзей
├── friends_command        # список друзей  
├── friend_requests_command # запросы дружбы
├── accept_friend_command  # принятие запросов
├── decline_friend_command # отклонение запросов
├── window_command         # настройка времени
├── freq_command           # настройка частоты
└── health_command         # системная диагностика
```

### Новая структура:
```
bot/handlers/commands/
├── __init__.py
├── user_commands.py       # start, settings (120-150 строк)
├── social_commands.py     # add_friend, friends, friend_requests, accept, decline (250-300 строк)  
├── config_commands.py     # window, freq (150-200 строк)
├── history_commands.py    # history (80-100 строк)
└── system_commands.py     # health (80-100 строк)
```

### Детальное распределение:

#### `user_commands.py` (~150 строк)
```python
async def start_command(update, context) -> None:
    """Регистрация пользователя и главное меню."""

async def settings_command(update, context) -> None:
    """Отображение текущих настроек пользователя."""

def setup_user_commands(application: Application) -> None:
    """Регистрация команд управления пользователем."""
```

#### `social_commands.py` (~300 строк)
```python
async def add_friend_command(update, context) -> None:
    """Добавление друга по username."""

async def friends_command(update, context) -> None:
    """Отображение меню друзей."""

async def friend_requests_command(update, context) -> None:
    """Управление запросами дружбы."""

async def accept_friend_command(update, context) -> None:
    """Принятие запроса дружбы."""

async def decline_friend_command(update, context) -> None:
    """Отклонение запроса дружбы."""

def setup_social_commands(application: Application) -> None:
    """Регистрация команд социальных функций."""
```

#### `config_commands.py` (~200 строк)
```python
async def window_command(update, context) -> None:
    """Настройка временного окна уведомлений."""

async def freq_command(update, context) -> None:
    """Настройка частоты уведомлений."""

def setup_config_commands(application: Application) -> None:
    """Регистрация команд настройки."""
```

#### `history_commands.py` (~100 строк)
```python
async def history_command(update, context) -> None:
    """Открытие веб-интерфейса истории."""

def setup_history_commands(application: Application) -> None:
    """Регистрация команд истории."""
```

#### `system_commands.py` (~100 строк)
```python
async def health_command(update, context) -> None:
    """Проверка здоровья системы."""

def setup_system_commands(application: Application) -> None:
    """Регистрация системных команд."""
```

## Этап 2: Разделение friends_callbacks.py (ПРИОРИТЕТ 2)

### Текущее состояние (719 строк):
- Один класс `FriendsCallbackHandler` со всей социальной логикой

### Новая структура:
```
bot/handlers/callbacks/friends/
├── __init__.py
├── friends_menu.py        # базовое меню и навигация (150-200 строк)
├── friends_discovery.py   # алгоритм "друзья друзей" (200-250 строк)  
├── friends_requests.py    # обработка запросов дружбы (200-250 строк)
└── friends_management.py  # управление списком друзей (150-200 строк)
```

#### `friends_menu.py`
```python
class FriendsMenuHandler(BaseCallbackHandler):
    """Обработчик главного меню друзей и навигации."""
    
    async def _handle_friends_menu(self, query, translator) -> None:
    async def _handle_back_to_main(self, query, translator) -> None:
```

#### `friends_discovery.py` 
```python
class FriendsDiscoveryHandler(BaseCallbackHandler):
    """Обработчик поиска и рекомендаций друзей."""
    
    async def _handle_friends_discovery(self, query, translator) -> None:
    async def _handle_add_friend_callback(self, query, data, translator, context) -> None:
    async def _refresh_discovery_list(self, query, translator, friend_ops, user_id) -> None:
```

#### `friends_requests.py`
```python  
class FriendsRequestsHandler(BaseCallbackHandler):
    """Обработчик запросов дружбы."""
    
    async def _handle_requests_help(self, query, translator) -> None:
    async def _handle_friend_accept(self, query, data, translator, context) -> None:
    async def _handle_friend_decline(self, query, data, translator, context) -> None:
```

#### `friends_management.py`
```python
class FriendsManagementHandler(BaseCallbackHandler):
    """Обработчик управления списком друзей."""
    
    async def _handle_friends_list(self, query, translator) -> None:
    async def _handle_add_instruction(self, query, translator) -> None:
```

## Этап 3: Разделение questions_callbacks.py (ПРИОРИТЕТ 3)

### Текущее состояние (642 строки):
- Один класс со всей логикой управления вопросами

### Новая структура:
```
bot/handlers/callbacks/questions/
├── __init__.py
├── questions_crud.py      # создание, редактирование, удаление (250-300 строк)
├── questions_templates.py # система шаблонов (200-250 строк)  
└── questions_testing.py   # тестирование и расписание (150-200 строк)
```

## Этап 4: Рефакторинг admin_callbacks.py

### Новая структура:
```
bot/handlers/callbacks/admin/
├── __init__.py
├── admin_panel.py         # основная панель управления (150-200 строк)
├── admin_statistics.py    # статистика пользователей (150-200 строк)
├── admin_monitoring.py    # мониторинг системы (150-200 строк)
└── admin_activities.py    # активность друзей (100-150 строк)
```

## Этап 5: Общие улучшения архитектуры

### 5.1 Базовые классы

#### `BaseCommandHandler`
```python
class BaseCommandHandler:
    """Базовый класс для обработчиков команд."""
    
    def __init__(self, db_client: DatabaseClient, config: Config):
        self.db_client = db_client
        self.config = config
        self.logger = get_logger(self.__class__.__name__)
    
    def get_user_translator(self, user) -> Translator:
        """Получить переводчик для пользователя."""
        
    async def ensure_user_exists(self, user) -> bool:
        """Убедиться что пользователь существует в БД."""
```

#### `BaseDomainHandler` 
```python
class BaseDomainHandler(BaseCallbackHandler):
    """Базовый класс для доменных обработчиков."""
    
    def __init__(self, domain_name: str):
        super().__init__()
        self.domain_name = domain_name
    
    def can_handle(self, data: str) -> bool:
        """Проверить принадлежность данных к домену."""
        return data.startswith(f"{self.domain_name}_")
```

### 5.2 Обновление регистрации обработчиков

#### Новый `main.py` setup:
```python
def setup_handlers(application: Application, dependencies: Dict) -> None:
    """Настройка всех обработчиков."""
    
    # Command handlers
    setup_user_commands(application, dependencies)
    setup_social_commands(application, dependencies)  
    setup_config_commands(application, dependencies)
    setup_history_commands(application, dependencies)
    setup_system_commands(application, dependencies)
    
    # Callback handlers  
    callback_router = CallbackRouter()
    
    # Register domain handlers
    callback_router.register_handler(FriendsMenuHandler())
    callback_router.register_handler(FriendsDiscoveryHandler())
    callback_router.register_handler(FriendsRequestsHandler())
    callback_router.register_handler(FriendsManagementHandler())
    
    callback_router.register_handler(QuestionsCrudHandler())
    callback_router.register_handler(QuestionsTemplatesHandler())
    callback_router.register_handler(QuestionsTestingHandler())
    
    # ... other handlers
```

### 5.3 Улучшение переиспользования

#### Общие утилиты:
```python
# bot/handlers/utils/
├── user_utils.py          # общая работа с пользователями
├── translation_utils.py   # переводы и локализация
├── validation_utils.py    # валидация входных данных
└── response_utils.py      # форматирование ответов
```

## План выполнения

### Фаза 1: Подготовка (1-2 дня)
1. Создать новые директории структуры
2. Создать базовые классы и утилиты
3. Написать тесты для проверки совместимости

### Фаза 2: Разделение команд (2-3 дня)
1. Разделить `command_handlers.py` на модули
2. Обновить импорты и регистрацию
3. Проверить работоспособность всех команд

### Фаза 3: Разделение callbacks (3-4 дня)
1. Разделить `friends_callbacks.py`
2. Разделить `questions_callbacks.py`  
3. Разделить `admin_callbacks.py`
4. Обновить callback router

### Фаза 4: Тестирование и документация (1-2 дня)
1. Полное тестирование всех функций
2. Обновление документации
3. Проверка производительности

### Фаза 5: Очистка (1 день)
1. Удаление старых файлов
2. Очистка неиспользуемых импортов
3. Финальная проверка

## Преимущества после рефакторинга

1. **Читаемость** - файлы 150-300 строк легче понимать
2. **Поддерживаемость** - изменения затрагивают меньше кода
3. **Тестируемость** - изолированные модули проще тестировать  
4. **Переиспользование** - общая логика в базовых классах
5. **Масштабируемость** - легко добавлять новые функции
6. **Безопасность** - изолированные домены снижают риски

## Риски и митигация

### Риски:
1. **Поломка существующего функционала**
2. **Сложность отладки** при разделенной логике
3. **Увеличение количества файлов**

### Митигация:
1. **Постепенный перенос** с тестированием на каждом этапе
2. **Сохранение API** - не меняем интерфейсы функций
3. **Автоматизированные тесты** для проверки совместимости
4. **Backup** старой версии до завершения рефакторинга

## Критерии успеха

1. ✅ Все тесты проходят
2. ✅ Размер файлов < 300 строк
3. ✅ Каждый модуль отвечает за один домен
4. ✅ Нет дублирования кода
5. ✅ Покрытие тестами > 85%
6. ✅ Время отклика < 200ms
7. ✅ Flake8 показывает 0 ошибок

---

*Этот план служит дорожной картой для улучшения архитектуры обработчиков. Выполнение по этапам обеспечит стабильность системы и качество кода.*
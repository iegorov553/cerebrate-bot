# Hour Watcher Bot

Telegram-бот для отслеживания активности пользователей. Бот автоматически отправляет вопрос "Что ты сейчас делаешь?" каждый час с 10:00 до 23:00 и сохраняет ответы в базу данных Supabase.

## Возможности

- 🕐 Автоматическая отправка вопросов каждый час (10:00-23:00)
- 📊 Сохранение всех ответов в Supabase PostgreSQL
- 🎯 Работа только с указанными пользователями
- ☁️ Готов к деплою на Railway, Render, VPS

## Установка и настройка

### Локальная разработка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd cerebrate-bot
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` с переменными окружения:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
TARGET_USER_IDS=123456789,987654321
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
```

4. Запустите бота:
```bash
python cerebrate_bot.py
```

### Деплой на Railway

1. Создайте проект на [Railway](https://railway.app)
2. Подключите ваш GitHub репозиторий
3. Добавьте переменные окружения в настройках проекта:
   - `TELEGRAM_BOT_TOKEN`
   - `TARGET_USER_IDS`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`

## Настройка Telegram бота

1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Получите токен и добавьте в переменные окружения
3. Узнайте ID пользователей (можно через [@userinfobot](https://t.me/userinfobot))

## Настройка Supabase

1. Создайте проект на [Supabase](https://supabase.com)
2. Создайте таблицу `tg_jobs`:

```sql
create table public.tg_jobs (
  tg_name text null,
  jobs_timestamp timestamp with time zone null,
  job_text text null,
  job_uid uuid not null default gen_random_uuid (),
  constraint tg_jobs_pkey primary key (job_uid)
) TABLESPACE pg_default;
```

3. Получите URL проекта и Service Role Key из настроек

## Переменные окружения

| Переменная | Описание | Пример |
|-----------|----------|--------|
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота | `1234567890:ABC...` |
| `TARGET_USER_IDS` | ID пользователей (через запятую) | `123456789,987654321` |
| `SUPABASE_URL` | URL проекта Supabase | `https://abc123.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Service Role ключ Supabase | `eyJhbGciOi...` |

## Структура базы данных

Таблица `tg_jobs`:
- `job_uid` (uuid) - Уникальный идентификатор записи
- `tg_name` (text) - Имя пользователя Telegram
- `jobs_timestamp` (timestamptz) - Время ответа (UTC)
- `job_text` (text) - Текст ответа пользователя

## Технические детали

- Python 3.8+
- Асинхронная архитектура с asyncio
- Совместимость с облачными платформами
- Автоматическое управление event loop для Railway/Render
- Логирование всех операций
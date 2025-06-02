# Hour Watcher Bot

Telegram-бот для отслеживания активности пользователей. Бот автоматически отправляет вопрос "Что ты сейчас делаешь?" каждый час с 10:00 до 23:00 и сохраняет ответы в базу данных Supabase.

## Возможности

- 🆕 **Автоматическая регистрация** - любой пользователь может начать работу с ботом
- 🕐 **Гибкие настройки времени** - каждый пользователь может настроить свое время работы бота
- 📊 **Сохранение ответов** в Supabase PostgreSQL с полной историей
- ⚙️ **Персональные настройки** через команду `/settings`
- ☁️ **Готов к деплою** на Railway, Render, VPS

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
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`

## Настройка Telegram бота

1. Создайте бота через [@BotFather](https://t.me/BotFather)
2. Получите токен и добавьте в переменные окружения
3. Пользователи будут автоматически регистрироваться при первом сообщении боту

## Настройка Supabase

1. Создайте проект на [Supabase](https://supabase.com)
2. Создайте таблицы:

**Таблица пользователей:**
```sql
create table public.users (
  user_id uuid not null default gen_random_uuid (),
  tg_id bigint not null unique,
  tg_username text null,
  tg_first_name text null,
  tg_last_name text null,
  enabled boolean not null default true,
  window_start time without time zone not null default '09:00:00',
  window_end time without time zone not null default '23:00:00',
  interval_min integer not null default 60,
  created_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  constraint users_pkey primary key (user_id),
  constraint users_tg_id_unique unique (tg_id)
) TABLESPACE pg_default;
```

**Таблица ответов:**
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
| `SUPABASE_URL` | URL проекта Supabase | `https://abc123.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | Service Role ключ Supabase | `eyJhbGciOi...` |

## Структура базы данных

**Таблица `users` (пользователи):**
- `user_id` (uuid) - Уникальный идентификатор пользователя
- `tg_id` (bigint) - Telegram ID пользователя
- `tg_username` (text) - Username в Telegram
- `tg_first_name` (text) - Имя пользователя
- `tg_last_name` (text) - Фамилия пользователя
- `enabled` (boolean) - Включен ли бот для пользователя
- `window_start` (time) - Время начала работы бота
- `window_end` (time) - Время окончания работы бота
- `interval_min` (integer) - Интервал в минутах между вопросами
- `created_at` (timestamptz) - Время регистрации
- `updated_at` (timestamptz) - Время последнего обновления

**Таблица `tg_jobs` (ответы):**
- `job_uid` (uuid) - Уникальный идентификатор записи
- `tg_name` (text) - Имя пользователя Telegram
- `jobs_timestamp` (timestamptz) - Время ответа (UTC)
- `job_text` (text) - Текст ответа пользователя

## Команды бота

- `/settings` - Показать текущие настройки пользователя
- `/notify_on` - Включить оповещения
- `/notify_off` - Отключить оповещения  
- `/window HH:MM-HH:MM` - Установить время работы бота (например: `/window 09:00-23:00`)
- `/freq N` - Установить интервал между вопросами в минутах (например: `/freq 60`)

## Технические детали

- Python 3.8+
- Асинхронная архитектура с asyncio
- Совместимость с облачными платформами
- Автоматическое управление event loop для Railway/Render
- Логирование всех операций
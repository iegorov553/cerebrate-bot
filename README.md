# Hour Watcher Bot

Telegram-бот для отслеживания активности пользователей. Бот автоматически отправляет вопрос "Чё делаешь? 🤔" с настраиваемыми интервалами и временными окнами и сохраняет ответы в базу данных Supabase.

## Возможности

- 🆕 **Автоматическая регистрация** - любой пользователь может начать работу с ботом
- 🕐 **Гибкие настройки времени** - каждый пользователь может настроить свое время работы бота
- 📊 **Сохранение ответов** в Supabase PostgreSQL с полной историей
- ⚙️ **Персональные настройки** через команду `/settings`
- 📱 **Веб-интерфейс** для просмотра истории активностей через Telegram Web App
- 🔍 **Поиск и фильтрация** записей по датам с подробной статистикой
- 👥 **Система друзей** для совместного просмотра активностей
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
  last_notification_sent timestamp with time zone null,
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
  tg_id bigint null,
  jobs_timestamp timestamp with time zone null,
  job_text text null,
  job_uid uuid not null default gen_random_uuid (),
  constraint tg_jobs_pkey primary key (job_uid)
) TABLESPACE pg_default;

-- Индекс для быстрого поиска по пользователю
CREATE INDEX idx_tg_jobs_tg_id ON tg_jobs(tg_id);

-- RLS политика для доступа к данным
CREATE POLICY "Allow anonymous read access to tg_jobs" 
ON tg_jobs FOR SELECT 
TO anon 
USING (true);
```

**Таблица друзей:**
```sql
CREATE TABLE friendships (
  friendship_id uuid NOT NULL DEFAULT gen_random_uuid(),
  requester_id bigint NOT NULL,
  addressee_id bigint NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted')),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  
  CONSTRAINT friendships_pkey PRIMARY KEY (friendship_id),
  CONSTRAINT friendships_requester_fkey FOREIGN KEY (requester_id) REFERENCES users(tg_id),
  CONSTRAINT friendships_addressee_fkey FOREIGN KEY (addressee_id) REFERENCES users(tg_id),
  CONSTRAINT friendships_unique UNIQUE (requester_id, addressee_id),
  CONSTRAINT friendships_no_self CHECK (requester_id != addressee_id)
);

-- Создание индексов
CREATE INDEX idx_friendships_requester ON friendships(requester_id);
CREATE INDEX idx_friendships_addressee ON friendships(addressee_id);
CREATE INDEX idx_friendships_status ON friendships(status);

-- Включение RLS
ALTER TABLE friendships ENABLE ROW LEVEL SECURITY;

-- RLS политика для друзей
CREATE POLICY "Allow anonymous access to friendships" ON friendships
  FOR ALL TO anon USING (true);
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
- `last_notification_sent` (timestamptz) - Время последнего отправленного уведомления
- `created_at` (timestamptz) - Время регистрации
- `updated_at` (timestamptz) - Время последнего обновления

**Таблица `tg_jobs` (ответы):**
- `job_uid` (uuid) - Уникальный идентификатор записи
- `tg_name` (text) - Имя пользователя Telegram
- `tg_id` (bigint) - Telegram ID пользователя для связи с таблицей users
- `jobs_timestamp` (timestamptz) - Время ответа (UTC)
- `job_text` (text) - Текст ответа пользователя

## Команды бота

**Основные команды:**
- `/start` - Регистрация и первое знакомство с ботом
- `/settings` - Показать текущие настройки пользователя
- `/notify_on` - Включить оповещения
- `/notify_off` - Отключить оповещения  
- `/window HH:MM-HH:MM` - Установить время работы бота (например: `/window 09:00-23:00`)
- `/freq N` - Установить интервал между вопросами в минутах (например: `/freq 60`)
- `/history` - Открыть веб-интерфейс для просмотра истории активностей

**Система друзей:**
- `/add_friend @username` - Отправить запрос в друзья
- `/friend_requests` - Посмотреть входящие и исходящие запросы
- `/accept [short_id]` - Принять запрос в друзья
- `/decline [short_id]` - Отклонить запрос в друзья
- `/friends` - Список всех друзей
- `/activities [@username]` - Просмотр активностей друга (последние 10 за неделю)

## Веб-интерфейс (Telegram Web App)

Проект включает полноценное веб-приложение для просмотра истории активностей:

**Возможности веб-интерфейса:**
- 📊 Просмотр всех ваших ответов с красивым дизайном
- 👥 **Выбор пользователя**: свои активности или активности друзей
- 📅 Фильтрация по периодам (сегодня, неделя, месяц, все время)
- 🔍 Поиск по тексту ответов
- 📈 Детальная статистика активности
- 📱 Адаптивный дизайн для мобильных устройств

**Технологии веб-приложения:**
- Next.js 15 + TypeScript
- Tailwind CSS для стилей  
- Supabase для данных
- Telegram Web Apps SDK для интеграции

**Развертывание веб-приложения:**

1. Разверните на Vercel:
   - Подключите GitHub репозиторий
   - Укажите Root Directory: `webapp`
   - Добавьте переменные окружения:
     - `NEXT_PUBLIC_SUPABASE_URL`
     - `NEXT_PUBLIC_SUPABASE_ANON_KEY`

2. Обновите URL в боте (`cerebrate_bot.py:535`) на ваш Vercel URL

## Система друзей

Бот поддерживает минимальную систему друзей для совместного просмотра активностей:

**Как это работает:**
1. **Отправить запрос**: `/add_friend @username`
2. **Принять запрос**: Друг использует `/friend_requests` и `/accept [id]`
3. **Просмотр активностей**: Оба могут использовать `/activities @друг` или веб-интерфейс

**Безопасность:**
- Можно просматривать активности только принятых друзей
- Валидация на уровне базы данных
- RLS политики защищают данные

**Интеграция с веб-интерфейсом:**
- Dropdown для выбора чьи активности смотреть
- Автоматическая загрузка списка друзей
- Бесшовное переключение между пользователями

## Технические детали

- Python 3.8+
- Асинхронная архитектура с asyncio
- Совместимость с облачными платформами
- Автоматическое управление event loop для Railway/Render
- Логирование всех операций
- Telegram Web App интеграция

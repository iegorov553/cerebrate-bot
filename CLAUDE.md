# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot called "Hour Watcher" that:
- Automatically registers new users when they send any message
- Sends personalized questions based on user settings ("Чё делаешь? 🤔")
- Records replies to Supabase database with full user management
- Supports individual user settings for time windows and intervals

## Architecture

**Single-file application** (`cerebrate_bot.py`) with key components:
- **Telegram integration**: Uses python-telegram-bot library for messaging
- **Supabase integration**: Uses supabase-py for data storage in PostgreSQL (users + responses)
- **User management**: Automatic registration and settings persistence
- **Scheduling**: APScheduler with per-user customizable time windows
- **Event loop handling**: Custom logic for Railway/cloud deployment compatibility

## Environment Variables

Required for deployment:
- `TELEGRAM_BOT_TOKEN`: Bot token from @BotFather
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key

## Development Commands

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Run the bot:**
```bash
python3 cerebrate_bot.py
```

**Test deployment locally:**
Set environment variables in a `.env` file and run the bot.

## Railway CLI Commands

**Login to Railway:**
```bash
railway login
```

**Deploy to Railway:**
```bash
railway up
```

**View logs:**
```bash
railway logs
```

**Set environment variables:**
```bash
railway variables set VARIABLE_NAME=value
```

## Supabase CLI Commands

**Login to Supabase:**
```bash
supabase login
```

**Initialize project:**
```bash
supabase init
```

**Start local development:**
```bash
supabase start
```

**Generate TypeScript types:**
```bash
supabase gen types typescript --local > types/supabase.ts
```

**Run migrations:**
```bash
supabase db push
```

## Key Technical Details

- Uses `nest_asyncio` for event loop compatibility in cloud environments
- Custom `run_coro_in_loop()` function handles asyncio event loop edge cases for cloud platforms (line 914-919)
- **Auto-registration**: Any user sending a message gets automatically registered with default settings via `ensure_user_exists()` (line 155-182)
- **User settings**: Individual time windows, intervals, and enable/disable functionality
- **Smart scheduling**: Per-user interval checking with `last_notification_sent` tracking to prevent spam
- All text messages (non-commands) are logged to Supabase table `tg_jobs` with username and UTC timestamp
- **Friend system**: Complete friendship workflow with request validation and notifications
- Database schema: 
  - `users` table: user management with personalized settings (tg_id, enabled, window_start/end, interval_min, last_notification_sent)
  - `tg_jobs` table: response logging with timestamps and user links (tg_name, tg_id, jobs_timestamp, job_text)
  - `friendships` table: friend relationships and requests (requester_id, addressee_id, status, created_at) with duplicate prevention
- Commands: `/start`, `/settings`, `/notify_on`, `/notify_off`, `/window HH:MM-HH:MM`, `/freq N`, `/history`, `/add_friend`, `/friend_requests`, `/accept`, `/decline`, `/friends`, `/activities` for user control
- RLS policies: Anonymous read access enabled for tg_jobs and friendships tables
- Error handling: Comprehensive exception catching with proper logging throughout all functions

## Web Interface

**Telegram Web App** (`webapp/` directory):
- **Next.js 15 + TypeScript** frontend with Tailwind CSS
- **History page** with filtering and search functionality (`/history`)
- **Vercel deployment** configuration included
- **Telegram Web Apps SDK** integration for seamless user authentication
- **Supabase RLS integration** with proper anonymous access policies
- **Features**: date filtering (today/week/month/all), text search, activity statistics, responsive design
- **Friend system**: dropdown to select whose activities to view (own/friends)
- **Data flow**: tg_id-based queries with fallback to username for legacy records
- **URL**: Configured to work with doyobi-diary.vercel.app domain

## Friend System

**Минимальная система друзей** для совместного просмотра активностей:

**Commands:**
- `/add_friend @username` - отправить запрос в друзья
- `/friend_requests` - посмотреть входящие и исходящие запросы
- `/accept [short_id]` - принять запрос (используется короткий ID из списка)
- `/decline [short_id]` - отклонить запрос
- `/friends` - список всех друзей
- `/activities [@username]` - просмотр активностей друга (последние 10 за неделю)

**Database:**
- `friendships` table with RLS policies for secure friend relationships
- Status: 'pending' → 'accepted' workflow
- Automatic notifications when requests are sent/accepted

**Web Interface:**
- Dropdown selector in history page to choose whose activities to view
- Loads friends list automatically via Supabase API
- Seamless switching between own and friends' activities

**Security:**
- Users can only view activities of accepted friends
- RLS policies protect friendship data
- Validation prevents self-friending and duplicate requests

## Deployment Notes

- и для railway и для supabase я уже привязал проекты
- Webapp deployed to Vercel at doyobi-diary.vercel.app with environment variables:
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- Critical setup steps completed:
  - RLS policy "Allow anonymous read access to tg_jobs" created for webapp access
  - tg_id field added to tg_jobs table for proper user-record linking
  - friendships table with RLS policies for friend system
  - Telegram Web App SDK integration working with fallback authentication
  - Both bot and webapp automatically deploy via GitHub integration
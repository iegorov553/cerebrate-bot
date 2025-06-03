# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot called "Hour Watcher" that:
- Automatically registers new users when they send any message
- Sends personalized questions based on user settings ("Что ты сейчас делаешь?")
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
python cerebrate_bot.py
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
- Custom `run_coro_in_loop()` function handles asyncio event loop edge cases for cloud platforms
- **Auto-registration**: Any user sending a message gets automatically registered with default settings
- **User settings**: Individual time windows, intervals, and enable/disable functionality
- All text messages (non-commands) are logged to Supabase table `tg_jobs` with username and UTC timestamp
- Database schema: 
  - `users` table: user management with personalized settings (tg_id, enabled, window_start/end, interval_min, last_notification_sent)
  - `tg_jobs` table: response logging with timestamps (tg_name, jobs_timestamp, job_text)
- Commands: `/settings`, `/notify_on`, `/notify_off`, `/window HH:MM-HH:MM`, `/freq N`, `/history` for user control

## Web Interface

**Telegram Web App** (`webapp/` directory):
- **Next.js + TypeScript** frontend with Tailwind CSS
- **History page** with filtering and search functionality
- **Vercel deployment** configuration included
- **Telegram Web Apps SDK** integration for seamless auth
- Features: date filtering, text search, activity statistics

## Deployment Notes

- и для railway и для supabase я уже привязал проекты
- Webapp can be deployed to Vercel with environment variables:
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
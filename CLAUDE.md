# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot called "Hour Watcher" that:
- Sends hourly questions to specific users ("Что ты сейчас делаешь?")
- Records their replies to Supabase database with timestamps
- Runs on a cron schedule from 10:00 to 23:00 daily

## Architecture

**Single-file application** (`cerebrate_bot.py`) with key components:
- **Telegram integration**: Uses python-telegram-bot library for messaging
- **Supabase integration**: Uses supabase-py for data storage in PostgreSQL
- **Scheduling**: APScheduler with cron jobs for hourly questions
- **Event loop handling**: Custom logic for Railway/cloud deployment compatibility

## Environment Variables

Required for deployment:
- `TELEGRAM_BOT_TOKEN`: Bot token from @BotFather
- `TARGET_USER_IDS`: Comma-separated list of Telegram user IDs
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

## Key Technical Details

- Uses `nest_asyncio` for event loop compatibility in cloud environments
- Custom `run_coro_in_loop()` function handles asyncio event loop edge cases for cloud platforms
- Bot only responds to users listed in `TARGET_USER_IDS`
- All text messages (non-commands) are logged to Supabase table `tg_jobs` with username and UTC timestamp
- Database schema: `tg_name` (text), `jobs_timestamp` (timestamptz), `job_text` (text), `job_uid` (uuid primary key)
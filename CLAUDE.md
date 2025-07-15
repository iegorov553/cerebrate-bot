# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 🗺️ НАВИГАТОР ДЛЯ CLAUDE CODE

## ⚡ КРИТИЧЕСКИЕ ФАКТЫ
- **Settings меню УДАЛЕНО** - все настройки в questions menu!
- **Callback patterns**: questions_*, friends_*, admin_*, feedback_*, menu_*
- **Handlers location**: bot/handlers/callbacks/
- **Settings toggles**: обрабатываются в QuestionsCallbackHandler
- **Rate limits**: по типам действий (см. bot/utils/rate_limiter.py)

## 🎯 АЛГОРИТМ ПЕРЕД ЗАДАЧЕЙ
1. ✅ Читай [docs/ai/project-facts.md](docs/ai/project-facts.md) - детальные факты
2. ✅ Проверь [docs/ai/handlers/](docs/ai/handlers/) по типу задачи
3. ✅ Если большая задача → [docs/ai/big-tasks/](docs/ai/big-tasks/)
4. ✅ Поиск в коде: `grep -r "паттерн"`

## 🔄 АЛГОРИТМ ПЕРЕД КОММИТОМ
1. ✅ Обнови [docs/ai/](docs/ai/) если изменилась архитектура
2. ✅ Если большая задача завершена → обнови [docs/ai/big-tasks/](docs/ai/big-tasks/)

## 📋 НАВИГАЦИЯ ПО AI DOCS
- **[docs/ai/README.md](docs/ai/README.md)** - полная карта AI документации
- **[docs/ai/project-facts.md](docs/ai/project-facts.md)** - критические факты проекта
- **[docs/ai/forbidden-actions.md](docs/ai/forbidden-actions.md)** - что НЕ делать
- **[docs/ai/handlers/](docs/ai/handlers/)** - всё про callback handlers
- **[docs/ai/big-tasks/](docs/ai/big-tasks/)** - планирование крупных задач
- **[docs/ai/workflows/](docs/ai/workflows/)** - пошаговые процессы

---

## Project Overview

**Doyobi Diary** is a modern Telegram bot for activity tracking and social connections with Enterprise-grade architecture. The project features a comprehensive ecosystem including a bot, web application, and monitoring system with hybrid modular architecture.

## Technology Stack

- **Backend**: Python 3.8+ with python-telegram-bot==20.3, Supabase (PostgreSQL), APScheduler
- **Frontend**: Next.js 15 with TypeScript, React 18.3.1, Tailwind CSS
- **Infrastructure**: Docker, Railway (bot), Vercel (web app), GitHub Actions
- **Development**: pytest, ruff, mypy, bandit, pre-commit
- **Monitoring**: Sentry, structured logging, health checks

## Important Development Notes

- Always use `python3` command, never `python`
- Push changes **only** to `staging` branch; `main` branch pushes are forbidden
- Run tests before every commit to ensure all pass
- Use Docker for both production and testing environments
- Update documentation before each commit
- File size limit: 400 lines per file, 50 lines per function
- Rate limiting is enabled by default - test with appropriate delays
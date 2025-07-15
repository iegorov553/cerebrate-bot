# Deployment Documentation

This document provides comprehensive deployment instructions for the Doyobi Diary across all environments and platforms.

## Overview

The Doyobi Diary uses a **multi-platform deployment strategy** with Railway for the bot backend and Vercel for the web interface, backed by Supabase for data storage.

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  PRODUCTION ENVIRONMENT                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐ │
│  │   Railway   │    │   Supabase   │    │     Vercel      │ │
│  │    (Bot)    │    │ (Database)   │    │   (Web App)     │ │
│  ├─────────────┤    ├──────────────┤    ├─────────────────┤ │
│  │ Python Bot  │◄──►│ PostgreSQL   │◄──►│ Next.js React  │ │
│  │ Monitoring  │    │ RLS Policies │    │ Tailwind CSS   │ │
│  │ Health Check│    │ Migrations   │    │ Analytics      │ │
│  └─────────────┘    └──────────────┘    └─────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Accounts
- [ ] **GitHub account** (for source code and CI/CD)
- [ ] **Railway account** (for bot hosting)
- [ ] **Vercel account** (for web app hosting)
- [ ] **Supabase account** (for database)
- [ ] **Telegram Bot Token** (from @BotFather)
- [ ] **Sentry account** (optional, for monitoring)

### Local Development Tools
- [ ] **Python 3.8+** with pip
- [ ] **Node.js 18+** with npm/yarn
- [ ] **Git** for version control
- [ ] **Railway CLI** for deployment
- [ ] **Vercel CLI** for web deployment
- [ ] **Supabase CLI** for database management

### Installation Commands

```bash
# Python and dependencies
pip install -r requirements.txt

# Node.js tools
npm install -g @railway/cli
npm install -g vercel
npm install -g supabase

# Verify installations
python3 --version
railway --version
vercel --version
supabase --version
```

---

## Environment Setup

### 1. Telegram Bot Creation

```bash
# Create bot with @BotFather on Telegram
# 1. Start chat with @BotFather
# 2. Send /newbot
# 3. Choose bot name and username
# 4. Save the bot token

export TELEGRAM_BOT_TOKEN="your_bot_token_here"
```

### 2. Supabase Database Setup

#### Create Supabase Project

```bash
# Login to Supabase
supabase login

# Create new project at https://supabase.com/dashboard
# Save your project URL and service role key
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your_service_role_key"
export SUPABASE_ANON_KEY="your_anon_key"
```

#### Database Schema Setup

```sql
-- Run these commands in Supabase SQL editor

-- Users table for bot users
CREATE TABLE users (
    tg_id BIGINT PRIMARY KEY,
    enabled BOOLEAN DEFAULT true,
    window_start TIME DEFAULT '09:00:00',
    window_end TIME DEFAULT '22:00:00',
    interval_min INTEGER DEFAULT 120,
    last_notification_sent TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Activity logging table
CREATE TABLE tg_jobs (
    id BIGSERIAL PRIMARY KEY,
    tg_name TEXT,
    tg_id BIGINT,
    jobs_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    job_text TEXT NOT NULL
);

-- Friendships table for social features
CREATE TABLE friendships (
    id BIGSERIAL PRIMARY KEY,
    requester_id BIGINT NOT NULL,
    addressee_id BIGINT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'accepted', 'declined')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(requester_id, addressee_id)
);

-- Indexes for performance
CREATE INDEX idx_users_tg_id ON users(tg_id);
CREATE INDEX idx_tg_jobs_tg_id ON tg_jobs(tg_id);
CREATE INDEX idx_tg_jobs_timestamp ON tg_jobs(jobs_timestamp);
CREATE INDEX idx_friendships_requester ON friendships(requester_id);
CREATE INDEX idx_friendships_addressee ON friendships(addressee_id);
CREATE INDEX idx_friendships_status ON friendships(status);
```

#### RLS Policies for Security

```sql
-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE tg_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE friendships ENABLE ROW LEVEL SECURITY;

-- Anonymous read access for web app
CREATE POLICY "Allow anonymous read access to tg_jobs" 
ON tg_jobs FOR SELECT 
TO anon 
USING (true);

CREATE POLICY "Allow anonymous read access to friendships" 
ON friendships FOR SELECT 
TO anon 
USING (true);

-- Service role full access
CREATE POLICY "Service role full access to users" 
ON users FOR ALL 
TO service_role 
USING (true);

CREATE POLICY "Service role full access to tg_jobs" 
ON tg_jobs FOR ALL 
TO service_role 
USING (true);

CREATE POLICY "Service role full access to friendships" 
ON friendships FOR ALL 
TO service_role 
USING (true);
```

#### Performance Optimization Functions

```sql
-- Optimized friend discovery function
CREATE OR REPLACE FUNCTION get_friends_of_friends_optimized(user_id BIGINT)
RETURNS TABLE (
    friend_id BIGINT,
    mutual_friends_count INTEGER,
    mutual_friends_sample TEXT[]
) AS $$
BEGIN
    RETURN QUERY
    WITH user_friends AS (
        SELECT CASE 
            WHEN requester_id = user_id THEN addressee_id
            ELSE requester_id
        END as friend_id
        FROM friendships 
        WHERE (requester_id = user_id OR addressee_id = user_id) 
        AND status = 'accepted'
    ),
    friends_of_friends AS (
        SELECT CASE 
            WHEN f2.requester_id = uf.friend_id THEN f2.addressee_id
            ELSE f2.requester_id
        END as potential_friend_id,
        uf.friend_id as mutual_friend_id
        FROM user_friends uf
        JOIN friendships f2 ON (f2.requester_id = uf.friend_id OR f2.addressee_id = uf.friend_id)
        WHERE f2.status = 'accepted'
    )
    SELECT 
        fof.potential_friend_id,
        COUNT(DISTINCT fof.mutual_friend_id)::INTEGER as mutual_count,
        ARRAY_AGG(DISTINCT fof.mutual_friend_id::TEXT ORDER BY fof.mutual_friend_id LIMIT 3) as mutual_sample
    FROM friends_of_friends fof
    WHERE fof.potential_friend_id != user_id
    AND fof.potential_friend_id NOT IN (SELECT friend_id FROM user_friends)
    AND NOT EXISTS (
        SELECT 1 FROM friendships 
        WHERE ((requester_id = user_id AND addressee_id = fof.potential_friend_id)
            OR (requester_id = fof.potential_friend_id AND addressee_id = user_id))
    )
    GROUP BY fof.potential_friend_id
    ORDER BY mutual_count DESC, fof.potential_friend_id
    LIMIT 10;
END;
$$ LANGUAGE plpgsql;

-- User statistics function for admin
CREATE OR REPLACE FUNCTION get_user_statistics()
RETURNS TABLE (
    total_users BIGINT,
    active_users BIGINT,
    new_users_week BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*) FROM users) as total_users,
        (SELECT COUNT(*) FROM users WHERE enabled = true) as active_users,
        (SELECT COUNT(*) FROM users WHERE created_at >= NOW() - INTERVAL '7 days') as new_users_week;
END;
$$ LANGUAGE plpgsql;
```

### 3. Sentry Monitoring Setup (Optional)

```bash
# Create Sentry project at https://sentry.io
# Save your DSN
export SENTRY_DSN="https://your-key@sentry.io/project-id"
export ENVIRONMENT="production"
export RELEASE_VERSION="v2.2.0"
```

---

## Railway Bot Deployment

### 1. Railway Setup

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Create new project
railway init
# Choose "Create new project"
# Select your GitHub repository
```

### 2. Environment Variables Configuration

```bash
# Set all required environment variables
railway variables set TELEGRAM_BOT_TOKEN="your_bot_token"
railway variables set SUPABASE_URL="https://your-project.supabase.co"
railway variables set SUPABASE_SERVICE_ROLE_KEY="your_service_role_key"

# Optional: Admin functionality
railway variables set ADMIN_USER_ID="your_telegram_id"

# Optional: Voice Recognition (primary provider recommended)
railway variables set GROQ_API_KEY="your_groq_api_key"
railway variables set OPENAI_API_KEY="your_openai_api_key"

# Optional: Voice Recognition model configuration
railway variables set GROQ_PRIMARY_MODEL="whisper-large-v3"
railway variables set GROQ_FALLBACK_MODEL="whisper-large-v3-turbo"
railway variables set GROQ_TIMEOUT_SECONDS="30"

# Optional: Monitoring
railway variables set SENTRY_DSN="your_sentry_dsn"
railway variables set ENVIRONMENT="production"
railway variables set RELEASE_VERSION="v2.2.0"

# Performance tuning
railway variables set CACHE_TTL_SECONDS="300"
railway variables set RATE_LIMIT_ENABLED="true"
railway variables set BATCH_SIZE="10"

# Verify variables
railway variables
```

### 3. Railway Deployment

```bash
# Deploy to Railway
railway up

# Monitor deployment
railway logs --tail

# Check service status
railway status
```

### 4. Custom Domain Setup (Optional)

```bash
# Add custom domain in Railway dashboard
# or via CLI
railway domain add your-bot-domain.com

# Configure DNS records as shown in Railway dashboard
```

---

## Vercel Web App Deployment

### 1. Web App Setup

```bash
# Navigate to webapp directory
cd webapp

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env.local

# Edit .env.local with your values
cat > .env.local << EOF
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
EOF
```

### 2. Vercel Deployment

```bash
# Install Vercel CLI
npm install -g vercel

# Login to Vercel
vercel login

# Deploy from webapp directory
vercel --prod

# Follow prompts to configure:
# - Link to existing project or create new
# - Set project name
# - Configure build settings

# Set environment variables in Vercel
vercel env add NEXT_PUBLIC_SUPABASE_URL
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY

# Redeploy with environment variables
vercel --prod
```

### 3. Custom Domain for Web App (Optional)

```bash
# Add domain via Vercel CLI
vercel domains add your-app-domain.com

# Or configure in Vercel dashboard
# Follow DNS configuration instructions
```

---

## GitHub Actions CI/CD Setup

### 1. Repository Secrets

Set up the following secrets in your GitHub repository:

```bash
# Navigate to GitHub repository settings > Secrets and variables > Actions
# Add the following repository secrets:

RAILWAY_TOKEN          # From Railway dashboard > Settings > Tokens
VERCEL_TOKEN          # From Vercel dashboard > Settings > Tokens
VERCEL_ORG_ID         # From vercel.json or CLI output
VERCEL_PROJECT_ID     # From vercel.json or CLI output

# Optional: Sentry integration
SENTRY_AUTH_TOKEN     # From Sentry > Settings > Auth Tokens
SENTRY_ORG           # Your Sentry organization
SENTRY_PROJECT       # Your Sentry project name
```

### 2. GitHub Actions Workflow

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
  VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
  VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
  VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Run tests
        run: |
          python -m pytest --cov=. --cov-report=xml
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true

  deploy-bot:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Railway CLI
        run: npm install -g @railway/cli
      
      - name: Set Release Version
        run: echo "RELEASE_VERSION=v2.2.0-$(git rev-parse --short HEAD)" >> $GITHUB_ENV
      
      - name: Deploy to Railway
        run: |
          railway variables set RELEASE_VERSION=$RELEASE_VERSION
          railway up --detach
      
      - name: Wait for deployment
        run: sleep 30
      
      - name: Health check
        run: |
          # Add health check URL when available
          echo "Bot deployed successfully"

  deploy-webapp:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: webapp/package-lock.json
      
      - name: Install webapp dependencies
        run: |
          cd webapp
          npm ci
      
      - name: Build webapp
        run: |
          cd webapp
          npm run build
      
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: ./webapp
          vercel-args: '--prod'

  notify-sentry:
    needs: [deploy-bot, deploy-webapp]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && success()
    steps:
      - uses: actions/checkout@v4
      
      - name: Create Sentry Release
        if: env.SENTRY_AUTH_TOKEN != ''
        env:
          SENTRY_AUTH_TOKEN: ${{ secrets.SENTRY_AUTH_TOKEN }}
          SENTRY_ORG: ${{ secrets.SENTRY_ORG }}
          SENTRY_PROJECT: ${{ secrets.SENTRY_PROJECT }}
        run: |
          curl -sL https://sentry.io/get-cli/ | bash
          export SENTRY_RELEASE=v2.2.0-$(git rev-parse --short HEAD)
          sentry-cli releases new $SENTRY_RELEASE
          sentry-cli releases set-commits $SENTRY_RELEASE --auto
          sentry-cli releases deploy $SENTRY_RELEASE --env production
          sentry-cli releases finalize $SENTRY_RELEASE
```

### 3. Test Workflow

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', 3.11, 3.12]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Lint with flake8
        run: |
          pip install flake8
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
          flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
      
      - name: Type check with mypy
        run: |
          pip install mypy
          mypy --ignore-missing-imports cerebrate_bot.py
      
      - name: Security check with bandit
        run: |
          pip install bandit
          bandit -r . -f json -o bandit-report.json || true
      
      - name: Run tests
        run: |
          python -m pytest -v --cov=. --cov-report=term-missing --cov-report=xml
      
      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-umbrella
```

---

## Staging Environment Setup

### 1. Railway Staging Environment

```bash
# Create staging environment in Railway
railway environment create staging

# Switch to staging
railway environment staging

# Set staging environment variables
railway variables set TELEGRAM_BOT_TOKEN="staging_bot_token"
railway variables set SUPABASE_URL="https://staging-project.supabase.co"
railway variables set SUPABASE_SERVICE_ROLE_KEY="staging_service_key"
railway variables set ENVIRONMENT="staging"
railway variables set RELEASE_VERSION="staging"

# Deploy to staging
railway up
```

### 2. Vercel Staging Environment

```bash
# Deploy staging version
cd webapp
vercel --env NEXT_PUBLIC_SUPABASE_URL=https://staging-project.supabase.co
vercel --env NEXT_PUBLIC_SUPABASE_ANON_KEY=staging_anon_key

# Set up staging domain
vercel alias set https://staging-deployment-url.vercel.app staging.your-domain.com
```

---

## Health Checks and Monitoring

### 1. Railway Health Checks

Add health check endpoint to your bot (optional):

```python
# Add to cerebrate_bot.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy", "timestamp": "' + 
                           datetime.now().isoformat().encode() + b'"}')
        else:
            self.send_response(404)
            self.end_headers()

def start_health_server():
    server = HTTPServer(('0.0.0.0', int(os.environ.get('PORT', 8080))), HealthCheckHandler)
    server.serve_forever()

# Start health check server in background
health_thread = threading.Thread(target=start_health_server, daemon=True)
health_thread.start()
```

### 2. Monitoring Setup

```bash
# Set up monitoring in Railway dashboard
# 1. Go to Railway project settings
# 2. Enable "Health Check" with path /health
# 3. Set up alerts for failures

# Vercel monitoring is automatic
# Check analytics in Vercel dashboard
```

---

## Domain Configuration

### 1. Custom Domain for Bot (Optional)

```bash
# In Railway dashboard:
# 1. Go to Settings > Domains
# 2. Add custom domain
# 3. Configure DNS:

# DNS Records needed:
# CNAME bot.yourdomain.com -> railway-url.railway.app
```

### 2. Custom Domain for Web App

```bash
# In Vercel dashboard:
# 1. Go to Project Settings > Domains
# 2. Add custom domain
# 3. Configure DNS:

# DNS Records needed:
# CNAME app.yourdomain.com -> vercel-url.vercel.app
# Or A record pointing to Vercel IP
```

---

## Deployment Checklist

### Pre-Deployment Checklist
- [ ] **Environment Variables**: All required variables set
- [ ] **Database Schema**: Tables and functions created
- [ ] **RLS Policies**: Security policies configured
- [ ] **Telegram Bot**: Bot created and token obtained
- [ ] **Domain Names**: DNS configured if using custom domains
- [ ] **Monitoring**: Sentry project created (if using)
- [ ] **Repository Secrets**: GitHub secrets configured
- [ ] **CI/CD**: GitHub Actions workflows tested

### Post-Deployment Verification
- [ ] **Bot Functionality**: Bot responds to /start command
- [ ] **Database Connection**: Bot can register users
- [ ] **Web App**: Web interface loads correctly
- [ ] **Friend System**: Social features working
- [ ] **Admin Features**: Broadcast system functional (if admin configured)
- [ ] **Monitoring**: Sentry receiving events (if configured)
- [ ] **Health Checks**: All services reporting healthy
- [ ] **Performance**: Response times within targets

### Production Monitoring
- [ ] **Error Rates**: Monitor Sentry dashboard
- [ ] **Performance**: Check Railway metrics
- [ ] **Uptime**: Monitor service availability
- [ ] **User Growth**: Track user registration
- [ ] **Feature Usage**: Monitor friend discovery usage
- [ ] **Database Performance**: Check Supabase metrics

---

## Troubleshooting

### Common Deployment Issues

#### Railway Deployment Fails

```bash
# Check logs
railway logs --tail

# Common issues:
# 1. Missing environment variables
railway variables

# 2. Build failures
# Check requirements.txt is present and correct

# 3. Port binding issues
# Railway automatically sets PORT environment variable
```

#### Vercel Deployment Fails

```bash
# Check build logs
vercel logs your-deployment-url

# Common issues:
# 1. Missing environment variables
vercel env ls

# 2. Build command failures
# Check package.json scripts

# 3. Node.js version issues
# Specify Node version in package.json
```

#### Database Connection Issues

```sql
-- Test connection from Railway logs
-- Look for Supabase connection errors

-- Common issues:
-- 1. Incorrect RLS policies
-- 2. Wrong service role key
-- 3. Network connectivity

-- Test with simple query:
SELECT 1 as test;
```

#### Bot Not Responding

```bash
# Check bot token
curl -X GET "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe"

# Check Railway logs for errors
railway logs --filter error

# Verify webhook is set (if using webhooks)
curl -X GET "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getWebhookInfo"
```

### Performance Issues

```bash
# Monitor Railway metrics
railway metrics

# Check database performance in Supabase dashboard
# Monitor query performance and slow queries

# Verify caching is working
# Check logs for cache hit/miss rates
```

### Security Issues

```bash
# Verify RLS policies
-- Run in Supabase SQL editor:
SELECT * FROM pg_policies WHERE tablename IN ('users', 'tg_jobs', 'friendships');

# Check environment variables don't contain secrets in logs
railway logs --filter "secret\|token\|key" | head -10

# Verify HTTPS is enforced
curl -I https://your-domain.com
```

---

## Rollback Procedures

### Railway Rollback

```bash
# View deployment history
railway deployments

# Rollback to previous deployment
railway rollback [deployment-id]

# Or redeploy specific commit
git checkout previous-working-commit
railway up
```

### Vercel Rollback

```bash
# View deployments
vercel list

# Promote previous deployment
vercel promote [deployment-url] --prod
```

### Database Rollback

```sql
-- Create backup before changes
pg_dump database_url > backup.sql

-- Restore from backup if needed
psql database_url < backup.sql

-- Or use Supabase point-in-time recovery
-- Available in Supabase dashboard
```

---

## Scaling Considerations

### Railway Scaling

```bash
# Monitor resource usage
railway metrics

# Upgrade plan if needed
# Go to Railway dashboard > Settings > Plan

# Consider horizontal scaling for high load
# Multiple Railway services with load balancer
```

### Database Scaling

```bash
# Monitor Supabase dashboard for:
# - Query performance
# - Connection limits
# - Storage usage

# Upgrade Supabase plan if needed
# Consider read replicas for high read loads
```

### Vercel Scaling

```bash
# Vercel automatically scales
# Monitor usage in dashboard

# Consider Edge Functions for dynamic content
# Configure CDN caching for static assets
```

---

This deployment documentation provides comprehensive instructions for deploying the Doyobi Diary to production with proper monitoring, security, and scalability considerations.
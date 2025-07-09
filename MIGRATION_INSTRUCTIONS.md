# Migration Instructions for Language Support

## Problem
The `language` column is missing from the `users` table in the production database.

## Solution
Execute the following SQL commands in the Supabase SQL Editor:

### 1. Add Language Column
```sql
-- Add language preference to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS language VARCHAR(5) DEFAULT 'ru' CHECK (language IN ('ru', 'en', 'es'));
```

### 2. Create Index
```sql
-- Add index for better performance
CREATE INDEX IF NOT EXISTS idx_users_language ON users(language);
```

### 3. Update Existing Users
```sql
-- Update existing users to have default language
UPDATE users SET language = 'ru' WHERE language IS NULL;
```

### 4. Add Comment
```sql
-- Add comment
COMMENT ON COLUMN users.language IS 'User preferred language (ru/en/es)';
```

## How to Execute

1. Go to Supabase Dashboard → SQL Editor
2. Execute each SQL command above one by one
3. Verify the column was added: `SELECT * FROM users LIMIT 1;`

## Verification
After running the migration, the bot will be able to save language preferences.

## Temporary Fallback
The bot code includes fallback handling for missing language column:
- Language changes work in the interface temporarily
- Database updates are gracefully handled
- Users see appropriate feedback messages
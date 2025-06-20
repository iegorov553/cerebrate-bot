-- Add language preference to users table
ALTER TABLE users 
ADD COLUMN language VARCHAR(5) DEFAULT 'ru' CHECK (language IN ('ru', 'en', 'es'));

-- Add index for better performance
CREATE INDEX idx_users_language ON users(language);

-- Add comment
COMMENT ON COLUMN users.language IS 'User preferred language (ru/en/es)';

-- Update existing users to have default language
UPDATE users SET language = 'ru' WHERE language IS NULL;
-- Add last_notification_sent field to users table
ALTER TABLE users ADD COLUMN last_notification_sent TIMESTAMP DEFAULT NULL;

-- Add index for better performance when querying by notification times
CREATE INDEX idx_users_last_notification_sent ON users(last_notification_sent);
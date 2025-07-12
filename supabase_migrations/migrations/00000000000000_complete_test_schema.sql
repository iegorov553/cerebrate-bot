-- Complete schema recreation for Doyobi Diary Bot testing environment
-- This migration recreates the full production schema in one file
-- WARNING: This will drop and recreate all tables - use only for testing!

-- Drop existing tables if they exist (for clean recreation)
DROP TABLE IF EXISTS question_notifications CASCADE;
DROP TABLE IF EXISTS user_questions CASCADE;
DROP TABLE IF EXISTS friendships CASCADE;
DROP TABLE IF EXISTS tg_jobs CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Drop functions if they exist
DROP FUNCTION IF EXISTS cleanup_expired_notifications() CASCADE;
DROP FUNCTION IF EXISTS get_user_stats() CASCADE;
DROP FUNCTION IF EXISTS get_friends_list_optimized(bigint) CASCADE;
DROP FUNCTION IF EXISTS get_friend_requests_optimized(bigint) CASCADE;
DROP FUNCTION IF EXISTS get_friends_of_friends_optimized(bigint, integer) CASCADE;

-- =============================================================================
-- 1. USERS TABLE - Base user management
-- =============================================================================

CREATE TABLE users (
    tg_id BIGINT PRIMARY KEY,
    tg_username TEXT,
    tg_first_name TEXT,
    enabled BOOLEAN DEFAULT true,
    window_start TIME DEFAULT '09:00',
    window_end TIME DEFAULT '22:00',
    interval_min INTEGER DEFAULT 120,
    last_notification_sent TIMESTAMP DEFAULT NULL,
    language VARCHAR(5) DEFAULT 'ru' CHECK (language IN ('ru', 'en', 'es')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_interval CHECK (interval_min >= 30),
    CONSTRAINT valid_time_window CHECK (window_start < window_end)
);

-- Indexes for users table
CREATE INDEX idx_users_enabled ON users(enabled);
CREATE INDEX idx_users_last_notification_sent ON users(last_notification_sent);
CREATE INDEX idx_users_language ON users(language);
CREATE INDEX idx_users_notification_settings ON users(enabled, window_start, window_end) WHERE enabled = true;

-- Comments
COMMENT ON TABLE users IS 'Base user management with notification settings and language preferences';
COMMENT ON COLUMN users.tg_id IS 'Telegram user ID (primary key)';
COMMENT ON COLUMN users.language IS 'User preferred language (ru/en/es)';
COMMENT ON COLUMN users.last_notification_sent IS 'Timestamp of last notification for scheduling';

-- =============================================================================
-- 2. TG_JOBS TABLE - Activity logging
-- =============================================================================

CREATE TABLE tg_jobs (
    id BIGSERIAL PRIMARY KEY,
    tg_id BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    job_text TEXT NOT NULL,
    jobs_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    question_id BIGINT, -- Will be linked after user_questions table creation
    
    -- Constraints
    CONSTRAINT job_text_not_empty CHECK (LENGTH(TRIM(job_text)) > 0)
);

-- Indexes for tg_jobs table
CREATE INDEX idx_tg_jobs_user ON tg_jobs(tg_id);
CREATE INDEX idx_tg_jobs_timestamp ON tg_jobs(jobs_timestamp DESC);
CREATE INDEX idx_tg_jobs_user_recent ON tg_jobs(tg_id, jobs_timestamp DESC);

-- Comments
COMMENT ON TABLE tg_jobs IS 'User activity logging with timestamps';
COMMENT ON COLUMN tg_jobs.question_id IS 'Link to specific question that generated this activity';

-- =============================================================================
-- 3. FRIENDSHIPS TABLE - Social connections
-- =============================================================================

CREATE TABLE friendships (
    id BIGSERIAL PRIMARY KEY,
    requester_id BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    addressee_id BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT friendships_unique UNIQUE (requester_id, addressee_id),
    CONSTRAINT friendships_no_self CHECK (requester_id != addressee_id)
);

-- Indexes for friendships table
CREATE INDEX idx_friendships_requester ON friendships(requester_id);
CREATE INDEX idx_friendships_addressee ON friendships(addressee_id);
CREATE INDEX idx_friendships_status ON friendships(status);
CREATE INDEX idx_friendships_active ON friendships(requester_id, addressee_id) WHERE status = 'accepted';

-- Comments
COMMENT ON TABLE friendships IS 'Friend requests and relationships with status tracking';
COMMENT ON COLUMN friendships.status IS 'Request status: pending, accepted, declined';

-- =============================================================================
-- 4. USER_QUESTIONS TABLE - Custom questions system
-- =============================================================================

CREATE TABLE user_questions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    question_name VARCHAR(100) NOT NULL,
    question_text TEXT NOT NULL,
    window_start TIME DEFAULT '09:00',
    window_end TIME DEFAULT '22:00',
    interval_minutes INTEGER DEFAULT 120,
    is_default BOOLEAN DEFAULT false,
    active BOOLEAN DEFAULT true,
    parent_question_id BIGINT REFERENCES user_questions(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_interval_questions CHECK (interval_minutes >= 30),
    CONSTRAINT valid_time_window_questions CHECK (window_start < window_end),
    CONSTRAINT question_name_not_empty CHECK (LENGTH(TRIM(question_name)) > 0),
    CONSTRAINT question_text_not_empty CHECK (LENGTH(TRIM(question_text)) > 0)
);

-- Unique indexes with conditions
CREATE UNIQUE INDEX idx_user_questions_default 
    ON user_questions(user_id, is_default) 
    WHERE is_default = true AND active = true;

CREATE UNIQUE INDEX idx_user_questions_name_active 
    ON user_questions(user_id, question_name) 
    WHERE active = true;

-- Regular indexes for performance
CREATE INDEX idx_user_questions_user_active ON user_questions(user_id, active);
CREATE INDEX idx_user_questions_parent ON user_questions(parent_question_id);

-- Comments
COMMENT ON TABLE user_questions IS 'Custom user questions with versioning support';
COMMENT ON COLUMN user_questions.is_default IS 'Default question marker (only one active per user)';
COMMENT ON COLUMN user_questions.parent_question_id IS 'Link to previous version for versioning';

-- =============================================================================
-- 5. QUESTION_NOTIFICATIONS TABLE - Notification tracking
-- =============================================================================

CREATE TABLE question_notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    question_id BIGINT NOT NULL REFERENCES user_questions(id) ON DELETE CASCADE,
    telegram_message_id BIGINT NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '3 months'),
    
    -- Constraints
    CONSTRAINT valid_expiry CHECK (expires_at > sent_at)
);

-- Indexes for question_notifications table
CREATE INDEX idx_question_notifications_lookup 
    ON question_notifications(user_id, telegram_message_id, expires_at);
CREATE INDEX idx_question_notifications_cleanup 
    ON question_notifications(expires_at);
CREATE INDEX idx_question_notifications_user_recent 
    ON question_notifications(user_id, sent_at DESC);

-- Comments
COMMENT ON TABLE question_notifications IS 'Notification tracking for Telegram Reply (TTL = 3 months)';
COMMENT ON COLUMN question_notifications.telegram_message_id IS 'Telegram message ID for reply tracking';

-- Add foreign key constraint to tg_jobs now that user_questions exists
ALTER TABLE tg_jobs ADD CONSTRAINT tg_jobs_question_fkey 
    FOREIGN KEY (question_id) REFERENCES user_questions(id);

-- Add indexes for tg_jobs question relationships
CREATE INDEX idx_tg_jobs_question ON tg_jobs(question_id);
CREATE INDEX idx_tg_jobs_user_question ON tg_jobs(tg_id, question_id);

-- =============================================================================
-- 6. ROW LEVEL SECURITY (RLS) POLICIES
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE tg_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE friendships ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_notifications ENABLE ROW LEVEL SECURITY;

-- Create policies for anonymous access (service role operations)
CREATE POLICY "Allow anonymous access to users" ON users FOR ALL TO anon USING (true);
CREATE POLICY "Allow anonymous access to tg_jobs" ON tg_jobs FOR ALL TO anon USING (true);
CREATE POLICY "Allow anonymous access to friendships" ON friendships FOR ALL TO anon USING (true);
CREATE POLICY "Allow anonymous access to user_questions" ON user_questions FOR ALL TO anon USING (true);
CREATE POLICY "Allow anonymous access to question_notifications" ON question_notifications FOR ALL TO anon USING (true);

-- =============================================================================
-- 7. OPTIMIZATION FUNCTIONS
-- =============================================================================

-- Function: Get user statistics for admin panel
CREATE OR REPLACE FUNCTION get_user_stats()
RETURNS TABLE (
    total_users BIGINT,
    active_users BIGINT,
    new_users_week BIGINT,
    total_activities BIGINT,
    total_friendships BIGINT,
    languages JSONB
) LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*) FROM users) as total_users,
        (SELECT COUNT(*) FROM users WHERE enabled = true) as active_users,
        (SELECT COUNT(*) FROM users WHERE created_at >= NOW() - INTERVAL '7 days') as new_users_week,
        (SELECT COUNT(*) FROM tg_jobs) as total_activities,
        (SELECT COUNT(*) FROM friendships WHERE status = 'accepted') as total_friendships,
        (SELECT jsonb_object_agg(language, count) 
         FROM (SELECT language, COUNT(*) as count FROM users GROUP BY language) lang_counts) as languages;
END;
$$;

-- Function: Get optimized friends list
CREATE OR REPLACE FUNCTION get_friends_list_optimized(user_tg_id BIGINT)
RETURNS TABLE (
    friend_id BIGINT,
    friend_username TEXT,
    friend_first_name TEXT,
    friendship_created_at TIMESTAMP WITH TIME ZONE
) LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT 
        CASE 
            WHEN f.requester_id = user_tg_id THEN f.addressee_id
            ELSE f.requester_id
        END as friend_id,
        u.tg_username as friend_username,
        u.tg_first_name as friend_first_name,
        f.created_at as friendship_created_at
    FROM friendships f
    JOIN users u ON (
        CASE 
            WHEN f.requester_id = user_tg_id THEN u.tg_id = f.addressee_id
            ELSE u.tg_id = f.requester_id
        END
    )
    WHERE (f.requester_id = user_tg_id OR f.addressee_id = user_tg_id)
        AND f.status = 'accepted'
    ORDER BY f.created_at DESC;
END;
$$;

-- Function: Get optimized friend requests
CREATE OR REPLACE FUNCTION get_friend_requests_optimized(user_tg_id BIGINT)
RETURNS TABLE (
    request_type TEXT,
    user_id BIGINT,
    username TEXT,
    first_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE
) LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    -- Incoming requests
    SELECT 
        'incoming'::TEXT as request_type,
        u.tg_id as user_id,
        u.tg_username as username,
        u.tg_first_name as first_name,
        f.created_at
    FROM friendships f
    JOIN users u ON u.tg_id = f.requester_id
    WHERE f.addressee_id = user_tg_id AND f.status = 'pending'
    
    UNION ALL
    
    -- Outgoing requests
    SELECT 
        'outgoing'::TEXT as request_type,
        u.tg_id as user_id,
        u.tg_username as username,
        u.tg_first_name as first_name,
        f.created_at
    FROM friendships f
    JOIN users u ON u.tg_id = f.addressee_id
    WHERE f.requester_id = user_tg_id AND f.status = 'pending'
    
    ORDER BY created_at DESC;
END;
$$;

-- Function: Get friends of friends (optimized social discovery)
CREATE OR REPLACE FUNCTION get_friends_of_friends_optimized(user_tg_id BIGINT, limit_count INTEGER DEFAULT 10)
RETURNS TABLE (
    friend_of_friend_id BIGINT,
    friend_of_friend_username TEXT,
    friend_of_friend_first_name TEXT,
    mutual_friends_count INTEGER,
    mutual_friends_names TEXT[]
) LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    WITH user_friends AS (
        -- Get all friends of the user
        SELECT 
            CASE 
                WHEN f.requester_id = user_tg_id THEN f.addressee_id
                ELSE f.requester_id
            END as friend_id
        FROM friendships f
        WHERE (f.requester_id = user_tg_id OR f.addressee_id = user_tg_id)
            AND f.status = 'accepted'
    ),
    friends_of_friends AS (
        -- Get friends of user's friends
        SELECT 
            CASE 
                WHEN f2.requester_id = uf.friend_id THEN f2.addressee_id
                ELSE f2.requester_id
            END as candidate_id,
            uf.friend_id as mutual_friend_id
        FROM user_friends uf
        JOIN friendships f2 ON (f2.requester_id = uf.friend_id OR f2.addressee_id = uf.friend_id)
        WHERE f2.status = 'accepted'
            AND CASE 
                WHEN f2.requester_id = uf.friend_id THEN f2.addressee_id
                ELSE f2.requester_id
            END != user_tg_id  -- Exclude self
    ),
    excluded_users AS (
        -- Get users to exclude (already friends or pending requests)
        SELECT friend_id as excluded_id FROM user_friends
        UNION
        SELECT requester_id FROM friendships WHERE addressee_id = user_tg_id
        UNION  
        SELECT addressee_id FROM friendships WHERE requester_id = user_tg_id
        UNION
        SELECT user_tg_id -- Exclude self
    ),
    candidates_with_mutuals AS (
        -- Count mutual friends for each candidate
        SELECT 
            fof.candidate_id,
            COUNT(DISTINCT fof.mutual_friend_id) as mutual_count,
            array_agg(DISTINCT u_mutual.tg_username) FILTER (WHERE u_mutual.tg_username IS NOT NULL) as mutual_usernames
        FROM friends_of_friends fof
        LEFT JOIN users u_mutual ON u_mutual.tg_id = fof.mutual_friend_id
        WHERE fof.candidate_id NOT IN (SELECT excluded_id FROM excluded_users)
        GROUP BY fof.candidate_id
        HAVING COUNT(DISTINCT fof.mutual_friend_id) > 0
    )
    SELECT 
        c.candidate_id as friend_of_friend_id,
        u.tg_username as friend_of_friend_username,
        u.tg_first_name as friend_of_friend_first_name,
        c.mutual_count::INTEGER as mutual_friends_count,
        c.mutual_usernames as mutual_friends_names
    FROM candidates_with_mutuals c
    JOIN users u ON u.tg_id = c.candidate_id
    ORDER BY c.mutual_count DESC, u.tg_first_name
    LIMIT limit_count;
END;
$$;

-- Function: Cleanup expired notifications
CREATE OR REPLACE FUNCTION cleanup_expired_notifications()
RETURNS INTEGER LANGUAGE plpgsql AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM question_notifications 
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RAISE NOTICE 'Cleaned up % expired notifications', deleted_count;
    RETURN deleted_count;
END;
$$;

-- Comments for functions
COMMENT ON FUNCTION get_user_stats() IS 'Get comprehensive user statistics for admin dashboard';
COMMENT ON FUNCTION get_friends_list_optimized(BIGINT) IS 'Get user friends list with single optimized query';
COMMENT ON FUNCTION get_friend_requests_optimized(BIGINT) IS 'Get incoming/outgoing friend requests optimized';
COMMENT ON FUNCTION get_friends_of_friends_optimized(BIGINT, INTEGER) IS 'Social discovery: find friends of friends with mutual connections';
COMMENT ON FUNCTION cleanup_expired_notifications() IS 'Remove expired notification records (call periodically)';

-- =============================================================================
-- 8. SAMPLE TEST DATA
-- =============================================================================

-- Insert test users with different languages
INSERT INTO users (tg_id, tg_username, tg_first_name, enabled, language) VALUES
(123456789, 'test_user_ru', 'Иван', true, 'ru'),
(987654321, 'test_user_en', 'John', true, 'en'),
(555666777, 'test_user_es', 'Carlos', true, 'es'),
(111222333, 'test_disabled', 'Disabled User', false, 'ru');

-- Insert default questions for each user
INSERT INTO user_questions (user_id, question_name, question_text, is_default, active) VALUES
(123456789, 'Основной', 'Время отчёта! Что делаешь?', true, true),
(987654321, 'Main', 'Time for report! What are you doing?', true, true),
(555666777, 'Principal', '¡Tiempo de informe! ¿Qué estás haciendo?', true, true),
(111222333, 'Основной', 'Время отчёта! Что делаешь?', true, true);

-- Insert some test activities
INSERT INTO tg_jobs (tg_id, job_text, question_id) VALUES
(123456789, 'Работаю над проектом', 1),
(123456789, 'Обедаю', 1),
(987654321, 'Working on code', 2),
(987654321, 'Having lunch', 2),
(555666777, 'Trabajando en código', 3),
(555666777, 'Almorzando', 3);

-- Insert test friendships
INSERT INTO friendships (requester_id, addressee_id, status) VALUES
(123456789, 987654321, 'accepted'),    -- Ivan and John are friends
(123456789, 555666777, 'pending'),     -- Ivan requested Carlos
(987654321, 555666777, 'accepted');    -- John and Carlos are friends

-- =============================================================================
-- MIGRATION COMPLETE
-- =============================================================================

-- Final notification
DO $$
DECLARE
    users_count INTEGER;
    questions_count INTEGER;
    activities_count INTEGER;
    friendships_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO users_count FROM users;
    SELECT COUNT(*) INTO questions_count FROM user_questions;
    SELECT COUNT(*) INTO activities_count FROM tg_jobs;
    SELECT COUNT(*) INTO friendships_count FROM friendships;
    
    RAISE NOTICE '=== MIGRATION COMPLETED SUCCESSFULLY ===';
    RAISE NOTICE 'Created % users with % questions', users_count, questions_count;
    RAISE NOTICE 'Created % activities and % friendships', activities_count, friendships_count;
    RAISE NOTICE 'All tables, indexes, functions and test data ready!';
END $$;
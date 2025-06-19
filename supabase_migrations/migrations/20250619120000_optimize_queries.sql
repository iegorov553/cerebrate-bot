-- Optimization migration: Add SQL functions for eliminating N+1 queries
-- Created: 2025-06-19

-- Function to execute raw SQL queries (for complex optimized queries)
CREATE OR REPLACE FUNCTION exec_sql(query TEXT, params JSONB DEFAULT '[]'::JSONB)
RETURNS TABLE(result JSONB)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    sql_query TEXT;
    param_count INTEGER;
    i INTEGER;
    param_value TEXT;
BEGIN
    sql_query := query;
    param_count := jsonb_array_length(params);
    
    -- Replace parameters %s with actual values
    FOR i IN 0..param_count-1 LOOP
        param_value := params->>i;
        sql_query := replace(sql_query, '%s', quote_literal(param_value));
        EXIT WHEN position('%s' IN sql_query) = 0;
    END LOOP;
    
    -- Execute the query and return results as JSONB
    RETURN QUERY EXECUTE format('SELECT to_jsonb(t.*) FROM (%s) t', sql_query);
END;
$$;

-- Optimized function to get friend requests with user info (eliminates N+1)
CREATE OR REPLACE FUNCTION get_friend_requests_optimized(p_user_id BIGINT)
RETURNS TABLE(
    direction TEXT,
    friendship_id UUID,
    requester_id BIGINT,
    addressee_id BIGINT,
    status TEXT,
    created_at TIMESTAMPTZ,
    other_user_id BIGINT,
    other_username TEXT,
    other_first_name TEXT
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    -- Incoming requests
    SELECT 
        'incoming'::TEXT as direction,
        f.friendship_id,
        f.requester_id,
        f.addressee_id,
        f.status,
        f.created_at,
        f.requester_id as other_user_id,
        u.tg_username as other_username,
        u.tg_first_name as other_first_name
    FROM friendships f
    JOIN users u ON u.tg_id = f.requester_id
    WHERE f.addressee_id = p_user_id AND f.status = 'pending'
    
    UNION ALL
    
    -- Outgoing requests
    SELECT 
        'outgoing'::TEXT as direction,
        f.friendship_id,
        f.requester_id,
        f.addressee_id,
        f.status,
        f.created_at,
        f.addressee_id as other_user_id,
        u.tg_username as other_username,
        u.tg_first_name as other_first_name
    FROM friendships f
    JOIN users u ON u.tg_id = f.addressee_id
    WHERE f.requester_id = p_user_id AND f.status = 'pending'
    
    ORDER BY created_at DESC;
END;
$$;

-- Optimized function to get friends list (eliminates N+1)
CREATE OR REPLACE FUNCTION get_friends_list_optimized(p_user_id BIGINT)
RETURNS TABLE(
    tg_id BIGINT,
    tg_username TEXT,
    tg_first_name TEXT,
    tg_last_name TEXT,
    friendship_created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        u.tg_id,
        u.tg_username,
        u.tg_first_name,
        u.tg_last_name,
        f.created_at as friendship_created_at
    FROM users u
    JOIN friendships f ON (
        (f.requester_id = p_user_id AND f.addressee_id = u.tg_id) OR
        (f.addressee_id = p_user_id AND f.requester_id = u.tg_id)
    )
    WHERE f.status = 'accepted'
    ORDER BY u.tg_username NULLS LAST, u.tg_first_name NULLS LAST;
END;
$$;

-- Optimized function for friends discovery (eliminates N+1)
CREATE OR REPLACE FUNCTION get_friends_of_friends_optimized(p_user_id BIGINT, p_limit INTEGER DEFAULT 10)
RETURNS TABLE(
    candidate_id BIGINT,
    candidate_username TEXT,
    candidate_first_name TEXT,
    candidate_last_name TEXT,
    mutual_friends_count INTEGER,
    mutual_friends_list TEXT[]
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    WITH user_friends AS (
        -- Get all friends of the user
        SELECT DISTINCT
            CASE 
                WHEN f.requester_id = p_user_id THEN f.addressee_id
                ELSE f.requester_id
            END as friend_id
        FROM friendships f
        WHERE (f.requester_id = p_user_id OR f.addressee_id = p_user_id)
        AND f.status = 'accepted'
    ),
    friends_of_friends AS (
        -- Get friends of friends (potential recommendations)
        SELECT DISTINCT
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
        END != p_user_id  -- Exclude self
        AND CASE 
            WHEN f2.requester_id = uf.friend_id THEN f2.addressee_id
            ELSE f2.requester_id
        END NOT IN (SELECT friend_id FROM user_friends)  -- Exclude existing friends
    ),
    recommendations AS (
        -- Aggregate mutual friends for each candidate
        SELECT 
            fof.candidate_id,
            COUNT(DISTINCT fof.mutual_friend_id) as mutual_count,
            ARRAY_AGG(DISTINCT u_mutual.tg_username ORDER BY u_mutual.tg_username) as mutual_usernames
        FROM friends_of_friends fof
        JOIN users u_mutual ON u_mutual.tg_id = fof.mutual_friend_id
        GROUP BY fof.candidate_id
        HAVING COUNT(DISTINCT fof.mutual_friend_id) > 0
        ORDER BY COUNT(DISTINCT fof.mutual_friend_id) DESC, fof.candidate_id
        LIMIT p_limit
    )
    SELECT 
        r.candidate_id,
        u.tg_username as candidate_username,
        u.tg_first_name as candidate_first_name,
        u.tg_last_name as candidate_last_name,
        r.mutual_count::INTEGER as mutual_friends_count,
        r.mutual_usernames as mutual_friends_list
    FROM recommendations r
    JOIN users u ON u.tg_id = r.candidate_id
    ORDER BY r.mutual_count DESC, u.tg_username NULLS LAST;
END;
$$;

-- Function to get user statistics for admin dashboard
CREATE OR REPLACE FUNCTION get_user_stats()
RETURNS TABLE(
    total_users BIGINT,
    active_users BIGINT,
    new_users_week BIGINT,
    active_percentage NUMERIC
)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*) FROM users) as total_users,
        (SELECT COUNT(*) FROM users WHERE enabled = true) as active_users,
        (SELECT COUNT(*) FROM users WHERE created_at >= NOW() - INTERVAL '7 days') as new_users_week,
        CASE 
            WHEN (SELECT COUNT(*) FROM users) > 0 
            THEN ROUND((SELECT COUNT(*) FROM users WHERE enabled = true)::NUMERIC / (SELECT COUNT(*) FROM users)::NUMERIC * 100, 2)
            ELSE 0
        END as active_percentage;
END;
$$;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_friendships_composite_status ON friendships(requester_id, addressee_id, status);
CREATE INDEX IF NOT EXISTS idx_friendships_addressee_status ON friendships(addressee_id, status);
CREATE INDEX IF NOT EXISTS idx_friendships_requester_status ON friendships(requester_id, status);
CREATE INDEX IF NOT EXISTS idx_users_username_lower ON users(LOWER(tg_username));

-- Update RLS policies to allow function access
DROP POLICY IF EXISTS "Allow anonymous read access to friendships" ON friendships;
CREATE POLICY "Allow anonymous read access to friendships" ON friendships
  FOR SELECT
  USING (true);  -- Allow all reads for the optimization functions

-- Grant execute permissions on the functions
GRANT EXECUTE ON FUNCTION exec_sql(TEXT, JSONB) TO anon;
GRANT EXECUTE ON FUNCTION get_friend_requests_optimized(BIGINT) TO anon;
GRANT EXECUTE ON FUNCTION get_friends_list_optimized(BIGINT) TO anon;
GRANT EXECUTE ON FUNCTION get_friends_of_friends_optimized(BIGINT, INTEGER) TO anon;
GRANT EXECUTE ON FUNCTION get_user_stats() TO anon;

-- Add comments for documentation
COMMENT ON FUNCTION get_friend_requests_optimized(BIGINT) IS 'Optimized function to get friend requests, eliminating N+1 queries';
COMMENT ON FUNCTION get_friends_list_optimized(BIGINT) IS 'Optimized function to get friends list with single query';
COMMENT ON FUNCTION get_friends_of_friends_optimized(BIGINT, INTEGER) IS 'Optimized friends discovery algorithm';
COMMENT ON FUNCTION get_user_stats() IS 'Get user statistics for admin dashboard';
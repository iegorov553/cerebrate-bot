-- ================================================================================
-- ПОЛНАЯ МИГРАЦИЯ ДЛЯ ВОССОЗДАНИЯ СХЕМЫ БАЗЫ ДАННЫХ DOYOBI DIARY TELEGRAM BOT
-- ================================================================================
-- Эта миграция объединяет все существующие миграции в одну комплексную схему
-- для полного воссоздания базы данных в тестовой или новой среде
-- 
-- Версия: 2.1.3
-- Создана: 2025-07-12
-- Автор: Claude Code Assistant
-- ================================================================================

-- ================================================================================
-- 1. БАЗОВЫЕ ТАБЛИЦЫ
-- ================================================================================

-- Таблица пользователей с полной структурой из всех миграций
CREATE TABLE users (
    tg_id BIGINT PRIMARY KEY,                           -- Telegram ID пользователя
    tg_username TEXT,                                    -- Telegram username (@username)
    tg_first_name TEXT,                                  -- Имя пользователя
    tg_last_name TEXT,                                   -- Фамилия пользователя
    enabled BOOLEAN DEFAULT true,                        -- Включены ли уведомления
    window_start TIME DEFAULT '09:00',                   -- Начало активного окна
    window_end TIME DEFAULT '22:00',                     -- Конец активного окна
    interval_min INTEGER DEFAULT 120,                    -- Интервал уведомлений в минутах
    language VARCHAR(5) DEFAULT 'ru'                     -- Язык интерфейса (ru/en/es)
        CHECK (language IN ('ru', 'en', 'es')),
    last_notification_sent TIMESTAMP DEFAULT NULL,       -- Время последнего уведомления
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()    -- Время создания записи
);

-- Таблица активностей пользователей
CREATE TABLE tg_jobs (
    id BIGSERIAL PRIMARY KEY,                            -- Уникальный ID активности
    tg_id BIGINT,                                        -- ID пользователя
    job_text TEXT NOT NULL,                              -- Текст активности
    jobs_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(), -- Время создания
    question_id BIGINT                                   -- Связь с кастомным вопросом
);

-- ================================================================================
-- 2. СОЦИАЛЬНЫЕ ФУНКЦИИ (ДРУЗЬЯ)
-- ================================================================================

-- Таблица дружеских отношений
CREATE TABLE friendships (
    friendship_id UUID NOT NULL DEFAULT gen_random_uuid(),
    requester_id BIGINT NOT NULL,                        -- Кто отправил запрос
    addressee_id BIGINT NOT NULL,                        -- Кому отправлен запрос
    status TEXT NOT NULL DEFAULT 'pending'               -- Статус: pending/accepted/declined
        CHECK (status IN ('pending', 'accepted', 'declined')),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    CONSTRAINT friendships_pkey PRIMARY KEY (friendship_id),
    CONSTRAINT friendships_requester_id_fkey 
        FOREIGN KEY (requester_id) REFERENCES users(tg_id) ON DELETE CASCADE,
    CONSTRAINT friendships_addressee_id_fkey 
        FOREIGN KEY (addressee_id) REFERENCES users(tg_id) ON DELETE CASCADE,
    CONSTRAINT friendships_unique UNIQUE (requester_id, addressee_id),
    CONSTRAINT friendships_no_self CHECK (requester_id != addressee_id)
);

-- ================================================================================
-- 3. СИСТЕМА КАСТОМНЫХ ВОПРОСОВ
-- ================================================================================

-- Основная таблица пользовательских вопросов
CREATE TABLE user_questions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    question_name VARCHAR(100) NOT NULL,                 -- "Основной", "Утренний чекин"
    question_text TEXT NOT NULL,                         -- Текст вопроса
    window_start TIME DEFAULT '09:00',                   -- Начало активного окна
    window_end TIME DEFAULT '22:00',                     -- Конец активного окна
    interval_minutes INTEGER DEFAULT 120,                -- Интервал уведомлений в минутах
    is_default BOOLEAN DEFAULT false,                    -- Маркер дефолтного вопроса
    active BOOLEAN DEFAULT true,                         -- Активен ли вопрос
    parent_question_id BIGINT REFERENCES user_questions(id), -- Ссылка на предыдущую версию
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Проверка валидности данных
    CONSTRAINT valid_interval CHECK (interval_minutes >= 30),
    CONSTRAINT valid_time_window CHECK (window_start < window_end),
    CONSTRAINT question_name_not_empty CHECK (LENGTH(TRIM(question_name)) > 0),
    CONSTRAINT question_text_not_empty CHECK (LENGTH(TRIM(question_text)) > 0)
);

-- Таблица для отслеживания отправленных уведомлений (для Telegram Reply)
CREATE TABLE question_notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    question_id BIGINT NOT NULL REFERENCES user_questions(id) ON DELETE CASCADE,
    telegram_message_id BIGINT NOT NULL,                 -- ID сообщения в Telegram для reply
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '3 months'), -- TTL = 3 месяца
    
    -- Проверка валидности TTL
    CONSTRAINT valid_expiry CHECK (expires_at > sent_at)
);

-- ================================================================================
-- 4. ИНДЕКСЫ ДЛЯ ПРОИЗВОДИТЕЛЬНОСТИ
-- ================================================================================

-- Индексы для таблицы пользователей
CREATE INDEX idx_users_last_notification_sent ON users(last_notification_sent);
CREATE INDEX idx_users_language ON users(language);
CREATE INDEX idx_users_username_lower ON users(LOWER(tg_username));

-- Индексы для таблицы активностей
CREATE INDEX idx_tg_jobs_tg_id ON tg_jobs(tg_id);
CREATE INDEX idx_tg_jobs_question ON tg_jobs(question_id);
CREATE INDEX idx_tg_jobs_user_question ON tg_jobs(tg_id, question_id);

-- Индексы для дружеских отношений
CREATE INDEX idx_friendships_requester ON friendships(requester_id);
CREATE INDEX idx_friendships_addressee ON friendships(addressee_id);
CREATE INDEX idx_friendships_status ON friendships(status);
CREATE INDEX idx_friendships_composite_status ON friendships(requester_id, addressee_id, status);
CREATE INDEX idx_friendships_addressee_status ON friendships(addressee_id, status);
CREATE INDEX idx_friendships_requester_status ON friendships(requester_id, status);

-- Индексы для системы кастомных вопросов
CREATE UNIQUE INDEX idx_user_questions_default 
    ON user_questions(user_id, is_default) 
    WHERE is_default = true AND active = true;

CREATE UNIQUE INDEX idx_user_questions_name_active 
    ON user_questions(user_id, question_name) 
    WHERE active = true;

CREATE INDEX idx_user_questions_user_active ON user_questions(user_id, active);
CREATE INDEX idx_user_questions_parent ON user_questions(parent_question_id);

-- Индексы для таблицы уведомлений
CREATE INDEX idx_question_notifications_lookup 
    ON question_notifications(user_id, telegram_message_id, expires_at);
CREATE INDEX idx_question_notifications_cleanup 
    ON question_notifications(expires_at);
CREATE INDEX idx_question_notifications_user_recent 
    ON question_notifications(user_id, sent_at DESC);

-- ================================================================================
-- 5. ВНЕШНИЕ КЛЮЧИ
-- ================================================================================

-- Добавляем связь активностей с вопросами
ALTER TABLE tg_jobs ADD CONSTRAINT fk_tg_jobs_question 
    FOREIGN KEY (question_id) REFERENCES user_questions(id);

-- ================================================================================
-- 6. RLS ПОЛИТИКИ БЕЗОПАСНОСТИ
-- ================================================================================

-- Включаем RLS для всех таблиц
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE tg_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE friendships ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE question_notifications ENABLE ROW LEVEL SECURITY;

-- Политики для анонимного доступа (для bot service role)
CREATE POLICY "Allow anonymous access to users" ON users
    FOR ALL TO anon USING (true);

CREATE POLICY "Allow anonymous access to tg_jobs" ON tg_jobs
    FOR ALL TO anon USING (true);

CREATE POLICY "Allow anonymous access to friendships" ON friendships
    FOR ALL TO anon USING (true);

CREATE POLICY "Allow anonymous access to user_questions" ON user_questions
    FOR ALL TO anon USING (true);

CREATE POLICY "Allow anonymous access to question_notifications" ON question_notifications
    FOR ALL TO anon USING (true);

-- ================================================================================
-- 7. ФУНКЦИИ ОПТИМИЗАЦИИ (УСТРАНЕНИЕ N+1 ЗАПРОСОВ)
-- ================================================================================

-- Функция для выполнения произвольных SQL запросов (для сложных оптимизированных запросов)
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

-- Оптимизированная функция получения запросов в друзья с информацией о пользователях
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

-- Оптимизированная функция получения списка друзей
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

-- Оптимизированная функция поиска друзей друзей
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

-- Функция получения статистики пользователей для админ панели
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

-- Функция для очистки истекших уведомлений
CREATE OR REPLACE FUNCTION cleanup_expired_notifications()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
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

-- ================================================================================
-- 8. ПРАВА ДОСТУПА К ФУНКЦИЯМ
-- ================================================================================

-- Предоставляем права на выполнение функций анонимному пользователю (для bot)
GRANT EXECUTE ON FUNCTION exec_sql(TEXT, JSONB) TO anon;
GRANT EXECUTE ON FUNCTION get_friend_requests_optimized(BIGINT) TO anon;
GRANT EXECUTE ON FUNCTION get_friends_list_optimized(BIGINT) TO anon;
GRANT EXECUTE ON FUNCTION get_friends_of_friends_optimized(BIGINT, INTEGER) TO anon;
GRANT EXECUTE ON FUNCTION get_user_stats() TO anon;
GRANT EXECUTE ON FUNCTION cleanup_expired_notifications() TO anon;

-- ================================================================================
-- 9. КОММЕНТАРИИ ДЛЯ ДОКУМЕНТАЦИИ
-- ================================================================================

-- Комментарии к таблицам
COMMENT ON TABLE users IS 'Пользователи бота с настройками уведомлений и языковыми предпочтениями';
COMMENT ON TABLE tg_jobs IS 'Активности пользователей с привязкой к кастомным вопросам';
COMMENT ON TABLE friendships IS 'Дружеские отношения между пользователями с поддержкой запросов';
COMMENT ON TABLE user_questions IS 'Пользовательские вопросы с поддержкой версионирования';
COMMENT ON TABLE question_notifications IS 'Отслеживание уведомлений для Telegram Reply (TTL = 3 месяца)';

-- Комментарии к важным столбцам
COMMENT ON COLUMN users.language IS 'Предпочитаемый язык интерфейса (ru/en/es)';
COMMENT ON COLUMN users.last_notification_sent IS 'Время последнего отправленного уведомления';
COMMENT ON COLUMN tg_jobs.question_id IS 'Привязка активности к конкретному вопросу';
COMMENT ON COLUMN user_questions.is_default IS 'Маркер дефолтного вопроса (только один активный на пользователя)';
COMMENT ON COLUMN user_questions.active IS 'Активен ли вопрос (false для старых версий)';
COMMENT ON COLUMN user_questions.parent_question_id IS 'Ссылка на предыдущую версию при изменении текста';
COMMENT ON COLUMN question_notifications.telegram_message_id IS 'ID сообщения в Telegram для определения reply';
COMMENT ON COLUMN question_notifications.expires_at IS 'Время истечения для автоматической очистки';

-- Комментарии к функциям
COMMENT ON FUNCTION get_friend_requests_optimized(BIGINT) IS 'Оптимизированная функция получения запросов в друзья, устраняющая N+1 запросы';
COMMENT ON FUNCTION get_friends_list_optimized(BIGINT) IS 'Оптимизированная функция получения списка друзей одним запросом';
COMMENT ON FUNCTION get_friends_of_friends_optimized(BIGINT, INTEGER) IS 'Оптимизированный алгоритм поиска друзей друзей';
COMMENT ON FUNCTION get_user_stats() IS 'Получение статистики пользователей для админ панели';
COMMENT ON FUNCTION cleanup_expired_notifications() IS 'Удаляет истекшие уведомления (вызывается по расписанию)';

-- ================================================================================
-- 10. ТЕСТОВЫЕ ДАННЫЕ ДЛЯ ПРОВЕРКИ
-- ================================================================================

-- Создаем тестовых пользователей
INSERT INTO users (tg_id, tg_username, tg_first_name, tg_last_name, language) VALUES
(123456789, 'test_user1', 'Тест', 'Пользователь1', 'ru'),
(123456790, 'test_user2', 'Test', 'User2', 'en'),
(123456791, 'usuario_prueba', 'Usuario', 'Prueba', 'es'),
(123456792, 'admin_user', 'Админ', 'Пользователь', 'ru');

-- Создаем дефолтные вопросы для тестовых пользователей
INSERT INTO user_questions (
    user_id,
    question_name, 
    question_text,
    window_start,
    window_end,
    interval_minutes,
    is_default,
    active
)
SELECT 
    tg_id,
    'Основной' as question_name,
    CASE 
        WHEN language = 'ru' THEN '⏰ Время отчёта! Что делаешь?'
        WHEN language = 'en' THEN '⏰ Report time! What are you doing?'
        WHEN language = 'es' THEN '⏰ ¡Hora del reporte! ¿Qué estás haciendo?'
    END as question_text,
    '09:00'::TIME as window_start,
    '22:00'::TIME as window_end,
    120 as interval_minutes,
    true as is_default,
    true as active
FROM users;

-- Создаем несколько тестовых активностей
INSERT INTO tg_jobs (tg_id, job_text, question_id) 
SELECT 
    u.tg_id,
    CASE 
        WHEN u.language = 'ru' THEN 'Работаю над проектом'
        WHEN u.language = 'en' THEN 'Working on project'
        WHEN u.language = 'es' THEN 'Trabajando en proyecto'
    END,
    uq.id
FROM users u
JOIN user_questions uq ON uq.user_id = u.tg_id AND uq.is_default = true;

-- Создаем тестовые дружеские отношения
INSERT INTO friendships (requester_id, addressee_id, status) VALUES
(123456789, 123456790, 'accepted'),  -- test_user1 и test_user2 друзья
(123456789, 123456791, 'pending'),   -- test_user1 отправил запрос usuario_prueba
(123456792, 123456789, 'pending');   -- admin_user отправил запрос test_user1

-- ================================================================================
-- 11. ПРОВЕРКА ЦЕЛОСТНОСТИ
-- ================================================================================

-- Проверяем, что все таблицы созданы
DO $$
DECLARE
    table_count INTEGER;
    function_count INTEGER;
    index_count INTEGER;
BEGIN
    -- Считаем созданные таблицы
    SELECT COUNT(*) INTO table_count 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_name IN ('users', 'tg_jobs', 'friendships', 'user_questions', 'question_notifications');
    
    -- Считаем созданные функции
    SELECT COUNT(*) INTO function_count 
    FROM information_schema.routines 
    WHERE routine_schema = 'public' 
    AND routine_name LIKE '%optimized%';
    
    -- Считаем созданные индексы
    SELECT COUNT(*) INTO index_count 
    FROM pg_indexes 
    WHERE schemaname = 'public';
    
    RAISE NOTICE '✅ Схема создана успешно:';
    RAISE NOTICE '   📊 Таблицы: %', table_count;
    RAISE NOTICE '   🚀 Функции оптимизации: %', function_count;
    RAISE NOTICE '   📈 Индексы: %', index_count;
    RAISE NOTICE '   👥 Тестовые пользователи: %', (SELECT COUNT(*) FROM users);
    RAISE NOTICE '   ❓ Дефолтные вопросы: %', (SELECT COUNT(*) FROM user_questions WHERE is_default = true);
    RAISE NOTICE '   🤝 Тестовые дружеские связи: %', (SELECT COUNT(*) FROM friendships);
    RAISE NOTICE '   📝 Тестовые активности: %', (SELECT COUNT(*) FROM tg_jobs);
END $$;

-- ================================================================================
-- КОНЕЦ МИГРАЦИИ
-- ================================================================================
-- 
-- Эта миграция создает полную рабочую схему базы данных для Doyobi Diary Bot
-- включая все функции, оптимизации и тестовые данные.
--
-- Для тестирования используйте:
-- SELECT * FROM get_user_stats();
-- SELECT * FROM get_friends_list_optimized(123456789);
-- SELECT * FROM get_friends_of_friends_optimized(123456789, 5);
-- 
-- ================================================================================
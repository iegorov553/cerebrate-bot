-- Миграция существующих пользователей на систему кастомных вопросов
-- Преобразование настроек из users.* в дефолтные вопросы

-- Создаём дефолтные вопросы для всех существующих пользователей
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
    'Основной'::VARCHAR(100) as question_name,
    '⏰ Время отчёта! Что делаешь?'::TEXT as question_text,
    COALESCE(window_start, '09:00'::TIME) as window_start,
    COALESCE(window_end, '22:00'::TIME) as window_end,
    COALESCE(interval_min, 120) as interval_minutes,
    true as is_default,
    true as active
FROM users
WHERE tg_id IS NOT NULL;

-- Привязываем все существующие активности к дефолтным вопросам пользователей
UPDATE tg_jobs 
SET question_id = uq.id
FROM user_questions uq
WHERE tg_jobs.tg_id = uq.user_id 
    AND uq.is_default = true 
    AND uq.active = true
    AND tg_jobs.question_id IS NULL;

-- Логирование результатов миграции
DO $$
DECLARE
    users_migrated INTEGER;
    activities_linked INTEGER;
BEGIN
    SELECT COUNT(*) INTO users_migrated 
    FROM user_questions 
    WHERE is_default = true AND active = true;
    
    SELECT COUNT(*) INTO activities_linked 
    FROM tg_jobs 
    WHERE question_id IS NOT NULL;
    
    RAISE NOTICE 'Migration completed: % users migrated, % activities linked', 
        users_migrated, activities_linked;
END $$;

-- Создаём функцию для очистки истекших уведомлений
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

-- Комментарий к функции
COMMENT ON FUNCTION cleanup_expired_notifications() IS 'Удаляет истекшие уведомления (вызывается по расписанию)';
-- Создание системы кастомных вопросов для Doyobi Diary Bot
-- Миграция добавляет поддержку множественных пользовательских вопросов с версионированием

-- Основная таблица пользовательских вопросов
CREATE TABLE user_questions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(tg_id) ON DELETE CASCADE,
    question_name VARCHAR(100) NOT NULL,           -- "Основной", "Утренний чекин"
    question_text TEXT NOT NULL,                   -- Текст вопроса
    window_start TIME DEFAULT '09:00',
    window_end TIME DEFAULT '22:00', 
    interval_minutes INTEGER DEFAULT 120,
    is_default BOOLEAN DEFAULT false,              -- Маркер дефолтного вопроса
    active BOOLEAN DEFAULT true,                   -- Активен ли вопрос
    parent_question_id BIGINT REFERENCES user_questions(id), -- Ссылка на предыдущую версию
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Проверка валидности данных
    CONSTRAINT valid_interval CHECK (interval_minutes >= 30),
    CONSTRAINT valid_time_window CHECK (window_start < window_end),
    CONSTRAINT question_name_not_empty CHECK (LENGTH(TRIM(question_name)) > 0),
    CONSTRAINT question_text_not_empty CHECK (LENGTH(TRIM(question_text)) > 0)
);

-- Уникальные индексы с условиями
CREATE UNIQUE INDEX idx_user_questions_default 
    ON user_questions(user_id, is_default) 
    WHERE is_default = true AND active = true;

CREATE UNIQUE INDEX idx_user_questions_name_active 
    ON user_questions(user_id, question_name) 
    WHERE active = true;

-- Обычные индексы для производительности
CREATE INDEX idx_user_questions_user_active ON user_questions(user_id, active);
CREATE INDEX idx_user_questions_parent ON user_questions(parent_question_id);

-- Таблица для отслеживания отправленных уведомлений (для Telegram Reply)
CREATE TABLE question_notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    question_id BIGINT NOT NULL REFERENCES user_questions(id) ON DELETE CASCADE,
    telegram_message_id BIGINT NOT NULL,           -- ID сообщения в Telegram для reply
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '3 months'), -- TTL = 3 месяца
    
    -- Проверка валидности TTL
    CONSTRAINT valid_expiry CHECK (expires_at > sent_at)
);

-- Индексы для таблицы уведомлений
CREATE INDEX idx_question_notifications_lookup 
    ON question_notifications(user_id, telegram_message_id, expires_at);
CREATE INDEX idx_question_notifications_cleanup 
    ON question_notifications(expires_at);
CREATE INDEX idx_question_notifications_user_recent 
    ON question_notifications(user_id, sent_at DESC);

-- Добавляем привязку активностей к вопросам
ALTER TABLE tg_jobs ADD COLUMN question_id BIGINT REFERENCES user_questions(id);

-- Индекс для быстрого поиска активностей по вопросам
CREATE INDEX idx_tg_jobs_question ON tg_jobs(question_id);
CREATE INDEX idx_tg_jobs_user_question ON tg_jobs(tg_id, question_id);

-- Комментарии для документации
COMMENT ON TABLE user_questions IS 'Пользовательские вопросы с поддержкой версионирования';
COMMENT ON COLUMN user_questions.is_default IS 'Маркер дефолтного вопроса (только один активный на пользователя)';
COMMENT ON COLUMN user_questions.active IS 'Активен ли вопрос (false для старых версий)';
COMMENT ON COLUMN user_questions.parent_question_id IS 'Ссылка на предыдущую версию при изменении текста';

COMMENT ON TABLE question_notifications IS 'Отслеживание уведомлений для Telegram Reply (TTL = 3 месяца)';
COMMENT ON COLUMN question_notifications.telegram_message_id IS 'ID сообщения в Telegram для определения reply';
COMMENT ON COLUMN question_notifications.expires_at IS 'Время истечения для автоматической очистки';

COMMENT ON COLUMN tg_jobs.question_id IS 'Привязка активности к конкретному вопросу';
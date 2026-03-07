-- Migration: Security Improvements
-- Description: Add password authentication, conversation history, and generated posts storage
-- Date: 2026-02-04
-- Dependencies: 001_add_multitenancy.sql

-- ====================
-- 1. ДОБАВЛЕНИЕ ПОЛЯ password_hash В tenants
-- ====================

-- Добавляем поле для хранения хэша пароля
ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) NULL;

COMMENT ON COLUMN tenants.password_hash IS 'Bcrypt hash пароля';


-- ====================
-- 2. ТАБЛИЦА ИСТОРИИ ДИАЛОГОВ
-- ====================

-- Таблица для хранения истории диалогов с пользователями
CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    bot_id UUID NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_conversation_tenant_id
ON conversation_messages(tenant_id);

CREATE INDEX IF NOT EXISTS idx_conversation_bot_id
ON conversation_messages(bot_id);

CREATE INDEX IF NOT EXISTS idx_conversation_user_id
ON conversation_messages(user_id);

CREATE INDEX IF NOT EXISTS idx_conversation_created_at
ON conversation_messages(created_at);

-- Составной индекс для получения истории диалога конкретного пользователя
CREATE INDEX IF NOT EXISTS idx_conversation_user_created
ON conversation_messages(tenant_id, bot_id, user_id, created_at);

-- Комментарии
COMMENT ON TABLE conversation_messages IS 'История диалогов с пользователями';
COMMENT ON COLUMN conversation_messages.tenant_id IS 'ID тенанта';
COMMENT ON COLUMN conversation_messages.bot_id IS 'ID бота';
COMMENT ON COLUMN conversation_messages.user_id IS 'ID пользователя в MAX';
COMMENT ON COLUMN conversation_messages.role IS 'Роль: user или assistant';
COMMENT ON COLUMN conversation_messages.content IS 'Текст сообщения';


-- ====================
-- 3. ТАБЛИЦА СГЕНЕРИРОВАННЫХ ПОСТОВ
-- ====================

-- Таблица для хранения сгенерированного контента
CREATE TABLE IF NOT EXISTS generated_posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    bot_id UUID NOT NULL,
    content TEXT NOT NULL,
    post_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'PUBLISHED')),
    admin_id VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    moderated_at TIMESTAMP NULL,
    published_at TIMESTAMP NULL
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_posts_tenant_id
ON generated_posts(tenant_id);

CREATE INDEX IF NOT EXISTS idx_posts_bot_id
ON generated_posts(bot_id);

CREATE INDEX IF NOT EXISTS idx_posts_status
ON generated_posts(status);

CREATE INDEX IF NOT EXISTS idx_posts_created_at
ON generated_posts(created_at);

-- Составной индекс для быстрой выборки постов на модерации
CREATE INDEX IF NOT EXISTS idx_posts_tenant_status_created
ON generated_posts(tenant_id, bot_id, status, created_at);

-- Комментарии
COMMENT ON TABLE generated_posts IS 'Сгенерированные посты';
COMMENT ON COLUMN generated_posts.tenant_id IS 'ID тенанта';
COMMENT ON COLUMN generated_posts.bot_id IS 'ID бота';
COMMENT ON COLUMN generated_posts.content IS 'Текст поста';
COMMENT ON COLUMN generated_posts.post_type IS 'Тип поста (product, motivation, news, etc.)';
COMMENT ON COLUMN generated_posts.status IS 'Статус поста';
COMMENT ON COLUMN generated_posts.admin_id IS 'ID админа, который модерировал';
COMMENT ON COLUMN generated_posts.moderated_at IS 'Время модерации';
COMMENT ON COLUMN generated_posts.published_at IS 'Время публикации';


-- ====================
-- 4. ВНЕШНИЕ КЛЮЧИ
-- ====================

-- Добавляем внешние ключи для обеспечения целостности данных
ALTER TABLE conversation_messages
ADD CONSTRAINT fk_conversation_tenant
FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;

ALTER TABLE conversation_messages
ADD CONSTRAINT fk_conversation_bot
FOREIGN KEY (bot_id) REFERENCES bot_configs(id) ON DELETE CASCADE;

ALTER TABLE generated_posts
ADD CONSTRAINT fk_posts_tenant
FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE;

ALTER TABLE generated_posts
ADD CONSTRAINT fk_posts_bot
FOREIGN KEY (bot_id) REFERENCES bot_configs(id) ON DELETE CASCADE;


-- ====================
-- 5. ПРАВИЛА АВТОМАТИЧЕСКОЙ ОЧИСТКИ (ОПЦИОНАЛЬНО)
-- ====================

-- Функция для автоматической очистки старых сообщений (старше 90 дней)
CREATE OR REPLACE FUNCTION cleanup_old_conversations() RETURNS void AS $$
BEGIN
    DELETE FROM conversation_messages
    WHERE created_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- Функция для автоматической очистки отклонённых постов (старше 30 дней)
CREATE OR REPLACE FUNCTION cleanup_rejected_posts() RETURNS void AS $$
BEGIN
    DELETE FROM generated_posts
    WHERE status = 'REJECTED'
    AND created_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Комментарии к функциям
COMMENT ON FUNCTION cleanup_old_conversations() IS 'Очистка старых сообщений (>90 дней)';
COMMENT ON FUNCTION cleanup_rejected_posts() IS 'Очистка отклонённых постов (>30 дней)';


-- ====================
-- 6. СТАТИСТИКА И МОНИТОРИНГ
-- ====================

-- View для статистики диалогов по тенантам
CREATE OR REPLACE VIEW conversation_stats AS
SELECT
    tenant_id,
    bot_id,
    COUNT(*) as total_messages,
    COUNT(DISTINCT user_id) as unique_users,
    DATE(created_at) as date
FROM conversation_messages
GROUP BY tenant_id, bot_id, DATE(created_at);

COMMENT ON VIEW conversation_stats IS 'Статистика диалогов по тенантам и ботам';


-- View для статистики постов
CREATE OR REPLACE VIEW posts_stats AS
SELECT
    tenant_id,
    bot_id,
    post_type,
    status,
    COUNT(*) as count,
    DATE(created_at) as date
FROM generated_posts
GROUP BY tenant_id, bot_id, post_type, status, DATE(created_at);

COMMENT ON VIEW posts_stats IS 'Статистика сгенерированных постов';


-- ====================
-- ROLLBACK (для отката миграции)
-- ====================

-- Раскомментируйте если нужно откатить миграцию:
-- DROP VIEW IF EXISTS conversation_stats CASCADE;
-- DROP VIEW IF EXISTS posts_stats CASCADE;
-- DROP FUNCTION IF EXISTS cleanup_old_conversations() CASCADE;
-- DROP FUNCTION IF EXISTS cleanup_rejected_posts() CASCADE;
-- DROP TABLE IF EXISTS conversation_messages CASCADE;
-- DROP TABLE IF EXISTS generated_posts CASCADE;
-- ALTER TABLE tenants DROP COLUMN IF EXISTS password_hash;

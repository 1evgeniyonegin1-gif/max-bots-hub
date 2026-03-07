-- Migration: Add Multitenancy Support
-- Description: Adds tenant_id to all tables, creates tenant management tables, enables Row-Level Security
-- Date: 2026-02-04

-- ====================
-- 1. СОЗДАНИЕ ТАБЛИЦ МУЛЬТИТЕНАНТНОСТИ
-- ====================

-- Таблица клиентов платформы (тенанты)
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'TRIAL' CHECK (status IN ('TRIAL', 'ACTIVE', 'PAUSED', 'BANNED')),
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_tenants_email ON tenants(email);
CREATE INDEX idx_tenants_status ON tenants(status);

-- Таблица конфигураций ботов
CREATE TABLE IF NOT EXISTS bot_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    bot_type VARCHAR(50) NOT NULL,
    bot_name VARCHAR(255) NOT NULL,
    bot_token VARCHAR(255) UNIQUE,
    bot_username VARCHAR(255),
    config JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'ACTIVE', 'PAUSED', 'DELETED')),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_bot_configs_tenant_id ON bot_configs(tenant_id);
CREATE INDEX idx_bot_configs_bot_token ON bot_configs(bot_token);
CREATE INDEX idx_bot_configs_status ON bot_configs(status);

-- Таблица подписок
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    plan VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'PAUSED', 'CANCELLED', 'EXPIRED')),
    started_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    auto_renew BOOLEAN DEFAULT TRUE,
    price NUMERIC(10, 2),
    currency VARCHAR(3) DEFAULT 'RUB',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_tenant_id ON subscriptions(tenant_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_expires_at ON subscriptions(expires_at);

-- Таблица статистики использования
CREATE TABLE IF NOT EXISTS usage_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    bot_id UUID REFERENCES bot_configs(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    messages_count INT DEFAULT 0,
    ai_api_calls INT DEFAULT 0,
    ai_tokens_used INT DEFAULT 0,
    active_users INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_usage_stats_tenant_id ON usage_stats(tenant_id);
CREATE INDEX idx_usage_stats_bot_id ON usage_stats(bot_id);
CREATE INDEX idx_usage_stats_date ON usage_stats(date);

-- ====================
-- 2. ДОБАВЛЕНИЕ tenant_id В СУЩЕСТВУЮЩИЕ ТАБЛИЦЫ (если они есть)
-- ====================

-- Users
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users') THEN
        ALTER TABLE users ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id);
        CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id);
    END IF;
END $$;

-- Conversation messages
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'conversation_messages') THEN
        ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id);
        CREATE INDEX IF NOT EXISTS idx_conversation_messages_tenant_id ON conversation_messages(tenant_id);
    END IF;
END $$;

-- Posts
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'posts') THEN
        ALTER TABLE posts ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id);
        CREATE INDEX IF NOT EXISTS idx_posts_tenant_id ON posts(tenant_id);
    END IF;
END $$;

-- Media assets
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'media_assets') THEN
        ALTER TABLE media_assets ADD COLUMN IF NOT EXISTS tenant_id UUID REFERENCES tenants(id);
        CREATE INDEX IF NOT EXISTS idx_media_assets_tenant_id ON media_assets(tenant_id);
    END IF;
END $$;

-- ====================
-- 3. ROW-LEVEL SECURITY (RLS)
-- ====================

-- Включаем RLS для bot_configs
ALTER TABLE bot_configs ENABLE ROW LEVEL SECURITY;

-- Политика изоляции по tenant_id
CREATE POLICY tenant_isolation_bot_configs ON bot_configs
    USING (tenant_id = current_setting('app.tenant_id', true)::UUID);

-- Включаем RLS для subscriptions
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_subscriptions ON subscriptions
    USING (tenant_id = current_setting('app.tenant_id', true)::UUID);

-- Включаем RLS для usage_stats
ALTER TABLE usage_stats ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_usage_stats ON usage_stats
    USING (tenant_id = current_setting('app.tenant_id', true)::UUID);

-- ====================
-- 4. ФУНКЦИИ И ТРИГГЕРЫ
-- ====================

-- Функция обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Триггеры для tenants
CREATE TRIGGER update_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Триггеры для bot_configs
CREATE TRIGGER update_bot_configs_updated_at
    BEFORE UPDATE ON bot_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Триггеры для subscriptions
CREATE TRIGGER update_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ====================
-- КОММЕНТАРИИ К ТАБЛИЦАМ
-- ====================

COMMENT ON TABLE tenants IS 'Клиенты платформы MAX BOTS HUB';
COMMENT ON TABLE bot_configs IS 'Конфигурации ботов клиентов';
COMMENT ON TABLE subscriptions IS 'Подписки клиентов на платформу';
COMMENT ON TABLE usage_stats IS 'Ежедневная статистика использования ботов';

COMMENT ON COLUMN tenants.slug IS 'Уникальный идентификатор клиента (например: zozh_club)';
COMMENT ON COLUMN tenants.status IS 'Статус: TRIAL (триал), ACTIVE (активен), PAUSED (приостановлен), BANNED (заблокирован)';
COMMENT ON COLUMN bot_configs.bot_type IS 'Тип бота: conversation, content_generator, gosuslugi, business_assistant и т.д.';
COMMENT ON COLUMN bot_configs.config IS 'JSONB с настройками бота (промпты, тексты, параметры)';

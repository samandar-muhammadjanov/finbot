-- ============================================================
-- FinanceBot — PostgreSQL Schema
-- Run this manually OR let SQLAlchemy create_all handle it.
-- ============================================================

-- Enum type for category/transaction types
DO $$ BEGIN
    CREATE TYPE category_type AS ENUM ('income', 'expense');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- -------------------------------------------------------
-- users: every Telegram user who has used the bot
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id          BIGINT PRIMARY KEY,           -- Telegram user ID
    username    VARCHAR(64),
    full_name   VARCHAR(128)    NOT NULL,
    is_admin    BOOLEAN         NOT NULL DEFAULT FALSE,
    is_active   BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    last_seen   TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- -------------------------------------------------------
-- categories: typed income/expense buckets
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS categories (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(64)     NOT NULL UNIQUE,
    type        category_type   NOT NULL,
    is_active   BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- -------------------------------------------------------
-- transactions: core financial ledger
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
    id              SERIAL PRIMARY KEY,
    type            category_type   NOT NULL,
    amount_cents    INTEGER         NOT NULL CHECK (amount_cents > 0),
    description     TEXT,
    category_id     INTEGER         NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
    created_by      BIGINT          REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    is_deleted      BOOLEAN         NOT NULL DEFAULT FALSE,
    deleted_at      TIMESTAMPTZ
);

-- -------------------------------------------------------
-- Indexes for common query patterns
-- -------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_transactions_type        ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at  ON transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_category_id ON transactions(category_id);
CREATE INDEX IF NOT EXISTS idx_transactions_created_by  ON transactions(created_by);
CREATE INDEX IF NOT EXISTS idx_transactions_is_deleted  ON transactions(is_deleted);

-- -------------------------------------------------------
-- Seed default categories
-- -------------------------------------------------------
INSERT INTO categories (name, type) VALUES
    ('Client Payment',      'income'),
    ('Service Payment',     'income'),
    ('Investment',          'income'),
    ('Other Income',        'income'),
    ('Office Supplies',     'expense'),
    ('Salaries',            'expense'),
    ('Rent',                'expense'),
    ('Software',            'expense'),
    ('Marketing',           'expense'),
    ('Travel',              'expense'),
    ('Utilities',           'expense'),
    ('Other Expense',       'expense')
ON CONFLICT (name) DO NOTHING;

-- =============================================================
-- AI Game Tool - Database Schema
-- SQLite 3.x
-- =============================================================

-- 1. games - 游戏配置
CREATE TABLE IF NOT EXISTS games (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    window_title    TEXT    NOT NULL DEFAULT '',
    window_class    TEXT    NOT NULL DEFAULT '',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_games_name ON games(name);
CREATE INDEX idx_games_updated_at ON games(updated_at);

-- 2. presets - 预设配置
CREATE TABLE IF NOT EXISTS presets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id         INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    name            TEXT    NOT NULL,
    description     TEXT    NOT NULL DEFAULT '',
    flow_data       TEXT    NOT NULL DEFAULT '{}',
    is_active       INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_presets_game_id ON presets(game_id);
CREATE INDEX idx_presets_name ON presets(name);
CREATE INDEX idx_presets_is_active ON presets(is_active);

-- 3. executions - 执行记录
CREATE TABLE IF NOT EXISTS executions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    preset_id       INTEGER NOT NULL REFERENCES presets(id) ON DELETE CASCADE,
    status          TEXT    NOT NULL DEFAULT 'pending'
                            CHECK(status IN ('pending','running','paused','completed','stopped','error')),
    started_at      TEXT,
    finished_at     TEXT,
    duration_ms     INTEGER,
    error_message   TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_executions_preset_id ON executions(preset_id);
CREATE INDEX idx_executions_status ON executions(status);
CREATE INDEX idx_executions_started_at ON executions(started_at);

-- 4. execution_steps - 执行步骤日志
CREATE TABLE IF NOT EXISTS execution_steps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id    INTEGER NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
    step_order      INTEGER NOT NULL DEFAULT 0,
    node_id         TEXT    NOT NULL DEFAULT '',
    node_type       TEXT    NOT NULL DEFAULT '',
    status          TEXT    NOT NULL DEFAULT 'pending'
                            CHECK(status IN ('pending','running','completed','error','skipped')),
    input_data      TEXT    NOT NULL DEFAULT '{}',
    output_data     TEXT    NOT NULL DEFAULT '{}',
    started_at      TEXT,
    finished_at     TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_execution_steps_execution_id ON execution_steps(execution_id);
CREATE INDEX idx_execution_steps_step_order ON execution_steps(execution_id, step_order);

-- 5. plugins - 插件
CREATE TABLE IF NOT EXISTS plugins (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    version         TEXT    NOT NULL DEFAULT '1.0.0',
    author          TEXT    NOT NULL DEFAULT '',
    description     TEXT    NOT NULL DEFAULT '',
    file_path       TEXT    NOT NULL DEFAULT '',
    enabled         INTEGER NOT NULL DEFAULT 1,
    installed_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_plugins_name ON plugins(name);
CREATE INDEX idx_plugins_enabled ON plugins(enabled);

-- 6. settings - 系统设置
CREATE TABLE IF NOT EXISTS settings (
    key             TEXT    PRIMARY KEY,
    value           TEXT    NOT NULL DEFAULT '',
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- AI Game Tool - Default Settings Seeds
-- 系统设置默认值

INSERT OR IGNORE INTO settings (key, value) VALUES
    ('theme', 'dark'),
    ('language', 'zh-CN'),
    ('backend_port', '8765'),
    ('log_level', 'INFO'),
    ('screenshot_quality', '90'),
    ('screenshot_format', 'png'),
    ('ocr_language', 'chi_sim'),
    ('ocr_engine', 'auto'),
    ('template_match_threshold', '0.8'),
    ('input_delay_ms', '50'),
    ('mouse_speed', '0.5'),
    ('websocket_heartbeat_interval', '30'),
    ('max_execution_logs', '1000'),
    ('auto_save_interval_sec', '30'),
    ('plugin_auto_load', 'true');

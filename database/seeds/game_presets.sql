-- =============================================================
-- AI Game Tool - 内置游戏预设种子数据
-- 原神 / 鸣潮 / 绝区零 三款游戏的预设配置
-- =============================================================

-- 1. 插入游戏记录
INSERT OR IGNORE INTO games (id, name, window_title, window_class) VALUES
    (1, '原神', '原神', 'UnityWndClass'),
    (2, '鸣潮', '鸣潮', 'UnrealWindow'),
    (3, '绝区零', '绝区零', 'UnityWndClass');

-- 2. 插入预设记录（flow_data 由 Python 导入脚本填充，此处仅做占位）
--    实际数据通过 seed_presets.py 从 JSON 文件读取后写入
--    如果直接运行此 SQL，flow_data 为空对象，需要再运行 seed_presets.py 补全数据

INSERT OR IGNORE INTO presets (id, game_id, name, description, flow_data, is_active) VALUES
    (1, 1, '原神每日委托', '自动完成原神每日委托流程：领取委托→传送→战斗→领取奖励→循环', '{}', 1),
    (2, 2, '鸣潮每日任务', '自动完成鸣潮每日任务流程：领取活跃度奖励→追踪任务→传送→战斗→领奖→循环', '{}', 1),
    (3, 3, '绝区零日常刷取', '自动完成绝区零日常流程：领取每日→VR训练→刷取材料→退出', '{}', 1);

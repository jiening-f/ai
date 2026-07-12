"""
内置游戏预设种子数据导入工具

从 presets/ 目录读取三款游戏的预设 JSON 文件，
将其写入 SQLite 数据库的 games 和 presets 表。

用法:
    cd ai/
    python scripts/seed_presets.py                    # 导入到默认数据库
    python scripts/seed_presets.py --db ./data/app.db # 指定数据库路径
    python scripts/seed_presets.py --dry-run           # 仅验证不写入
    python scripts/seed_presets.py --verify            # 验证已有数据格式
"""

import json
import sqlite3
import sys
import os
import argparse
from pathlib import Path

# 修复 Windows 控制台 GBK 编码问题
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ── 预设配置 ────────────────────────────────────────

PRESETS_DIR = Path(__file__).resolve().parent.parent / "presets"

GAME_PRESETS = [
    {
        "game": {
            "name": "原神",
            "window_title": "原神",
            "window_class": "UnityWndClass",
        },
        "presets": [
            {
                "name": "原神每日委托",
                "description": "自动完成原神每日委托流程：领取委托→传送→战斗→领取奖励→循环。需在游戏主界面启动。",
                "flow_file": "genshin/presets/daily_commission.json",
                "is_active": True,
            }
        ],
    },
    {
        "game": {
            "name": "鸣潮",
            "window_title": "鸣潮",
            "window_class": "UnrealWindow",
        },
        "presets": [
            {
                "name": "鸣潮每日任务",
                "description": "自动完成鸣潮每日任务流程：领取活跃度奖励→追踪任务→传送→战斗→领奖→循环。需在主城界面启动。",
                "flow_file": "wuthering_waves/presets/daily_mission.json",
                "is_active": True,
            }
        ],
    },
    {
        "game": {
            "name": "绝区零",
            "window_title": "绝区零",
            "window_class": "UnityWndClass",
        },
        "presets": [
            {
                "name": "绝区零日常刷取",
                "description": "自动完成绝区零日常流程：领取每日→VR训练→刷取材料→退出。需在录像店界面启动。",
                "flow_file": "zzz/presets/daily_farm.json",
                "is_active": True,
            }
        ],
    },
]


# ── 验证函数 ────────────────────────────────────────

def validate_flow_data(flow_data: dict) -> list[str]:
    """验证 flow_data 的结构是否正确，返回错误列表"""
    errors = []

    # 基础字段
    if "name" not in flow_data:
        errors.append("缺少 name 字段")
    if "mode" not in flow_data:
        errors.append("缺少 mode 字段（应为 'step'）")
    elif flow_data["mode"] not in ("step", "node", "loop"):
        errors.append(f"mode 值无效: {flow_data['mode']}")

    # 步骤验证（step 模式）
    if flow_data.get("mode") == "step":
        steps = flow_data.get("steps", [])
        if not steps:
            errors.append("steps 数组为空，至少需要 1 个步骤")
        for i, step in enumerate(steps):
            sid = step.get("id", f"step_{i}")
            # 必需字段
            for field in ("condition_type", "action_type"):
                if field not in step:
                    errors.append(f"步骤 {sid}: 缺少 {field} 字段")
            # 条件类型验证
            ct = step.get("condition_type", "")
            if ct not in ("text", "image", "none"):
                errors.append(f"步骤 {sid}: condition_type '{ct}' 无效")
            # 动作类型验证
            at = step.get("action_type", "")
            valid_actions = (
                "press_key", "key_hold", "mouse_click", "click_text",
                "click_image", "click_near_image", "wait",
            )
            if at not in valid_actions:
                errors.append(f"步骤 {sid}: action_type '{at}' 无效")
            # 数值验证
            duration = step.get("duration", 0)
            if not isinstance(duration, (int, float)) or duration < 0:
                errors.append(f"步骤 {sid}: duration 应为非负数")
            delay = step.get("delay", 0)
            if not isinstance(delay, (int, float)) or delay < 0:
                errors.append(f"步骤 {sid}: delay 应为非负数")

    # 节点验证（node 模式）
    nodes = flow_data.get("nodes", {})
    if nodes:
        has_start = any(n.get("node_type") == "start" for n in nodes.values())
        if not has_start:
            errors.append("nodes 中缺少 start 节点")
        has_end = any(n.get("node_type") == "end" for n in nodes.values())
        if not has_end:
            errors.append("nodes 中缺少 end 节点")

    return errors


# ── 导入函数 ────────────────────────────────────────

def import_presets(db_path: str, dry_run: bool = False) -> dict:
    """
    将预设导入数据库。
    返回 {"games": int, "presets": int, "errors": [str]}
    """
    result = {"games": 0, "presets": 0, "errors": []}

    if dry_run:
        print("🔍 干运行模式 — 仅验证不写入\n")
    else:
        print(f"📂 数据库: {db_path}\n")

    # 确保数据库目录存在
    if not dry_run:
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)

    conn = None if dry_run else sqlite3.connect(db_path)
    try:
        if conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")

        for entry in GAME_PRESETS:
            game_config = entry["game"]
            game_name = game_config["name"]

            # ── 插入游戏 ──
            if conn:
                cursor = conn.execute(
                    """INSERT OR IGNORE INTO games (name, window_title, window_class)
                       VALUES (?, ?, ?)""",
                    (game_config["name"], game_config["window_title"], game_config["window_class"]),
                )
                if cursor.rowcount > 0:
                    result["games"] += 1
                    print(f"  ✅ 游戏: {game_name} (新增)")
                else:
                    print(f"  ⏭  游戏: {game_name} (已存在)")

                # 获取 game_id
                row = conn.execute(
                    "SELECT id FROM games WHERE name = ?", (game_name,)
                ).fetchone()
                game_id = row[0] if row else None
            else:
                print(f"  🔍 游戏: {game_name} (验证通过)")
                game_id = 1  # dry-run 占位

            if game_id is None:
                result["errors"].append(f"获取游戏 {game_name} 的 ID 失败")
                continue

            # ── 插入预设 ──
            for preset_config in entry["presets"]:
                flow_file = PRESETS_DIR / preset_config["flow_file"]

                # 读取 flow_data
                try:
                    with open(flow_file, "r", encoding="utf-8") as f:
                        flow_data = json.load(f)
                except FileNotFoundError:
                    err = f"预设文件不存在: {flow_file}"
                    result["errors"].append(err)
                    print(f"    ❌ {err}")
                    continue
                except json.JSONDecodeError as e:
                    err = f"JSON 解析失败 {flow_file}: {e}"
                    result["errors"].append(err)
                    print(f"    ❌ {err}")
                    continue

                # 验证
                validation_errors = validate_flow_data(flow_data)
                if validation_errors:
                    for ve in validation_errors:
                        err = f"  {preset_config['name']}: {ve}"
                        result["errors"].append(err)
                        print(f"    ⚠️  {ve}")
                    if dry_run:
                        continue  # 干运行模式继续检查下一个

                flow_json = json.dumps(flow_data, ensure_ascii=False)

                if conn:
                    cursor = conn.execute(
                        """INSERT OR IGNORE INTO presets (game_id, name, description, flow_data, is_active)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            game_id,
                            preset_config["name"],
                            preset_config["description"],
                            flow_json,
                            1 if preset_config["is_active"] else 0,
                        ),
                    )
                    if cursor.rowcount > 0:
                        result["presets"] += 1
                        print(f"    ✅ 预设: {preset_config['name']} (新增)")
                    else:
                        # 更新已有的预设
                        conn.execute(
                            """UPDATE presets SET flow_data = ?, description = ?, is_active = ?
                               WHERE game_id = ? AND name = ?""",
                            (
                                flow_json,
                                preset_config["description"],
                                1 if preset_config["is_active"] else 0,
                                game_id,
                                preset_config["name"],
                            ),
                        )
                        print(f"    🔄 预设: {preset_config['name']} (已更新)")
                        result["presets"] += 1
                else:
                    print(f"    🔍 预设: {preset_config['name']} (JSON 格式验证通过)")
                    result["presets"] += 1

        if conn:
            conn.commit()
            print(f"\n✅ 导入完成: {result['games']} 个游戏, {result['presets']} 个预设")
        else:
            print(f"\n✅ 验证完成: {result['presets']} 个预设通过验证")

    except Exception as e:
        result["errors"].append(str(e))
        print(f"\n❌ 错误: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

    return result


def verify_existing(db_path: str) -> dict:
    """验证数据库中已有预设的 flow_data 格式"""
    result = {"total": 0, "valid": 0, "invalid": 0, "errors": []}

    if not os.path.exists(db_path):
        print(f"❌ 数据库不存在: {db_path}")
        result["errors"].append(f"数据库不存在: {db_path}")
        return result

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            """SELECT p.id, p.name, p.flow_data, g.name as game_name
               FROM presets p JOIN games g ON p.game_id = g.id"""
        ).fetchall()

        result["total"] = len(rows)

        for pid, name, flow_data_str, game_name in rows:
            try:
                flow_data = json.loads(flow_data_str)
            except json.JSONDecodeError as e:
                result["invalid"] += 1
                result["errors"].append(f"预设 #{pid} ({name}): JSON 解析失败 - {e}")
                continue

            validation_errors = validate_flow_data(flow_data)
            if validation_errors:
                result["invalid"] += 1
                for ve in validation_errors:
                    result["errors"].append(f"预设 #{pid} ({name}): {ve}")
            else:
                result["valid"] += 1
                print(f"  ✅ #{pid} {name} ({game_name}): 格式正确")

        print(f"\n📊 验证结果: {result['valid']}/{result['total']} 通过, {result['invalid']} 失败")

    finally:
        conn.close()

    return result


# ── CLI 入口 ────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="内置游戏预设种子数据导入工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--db", type=str, default="data/app.db",
        help="数据库路径 (默认: data/app.db)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="仅验证 JSON 文件，不写入数据库",
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="验证数据库中已有预设的数据格式",
    )
    args = parser.parse_args()

    print("═" * 55)
    print("  游戏预设种子数据导入工具")
    print("═" * 55)
    print()

    if args.verify:
        result = verify_existing(args.db)
    else:
        result = import_presets(args.db, dry_run=args.dry_run)

    if result["errors"]:
        print(f"\n⚠️  {len(result['errors'])} 个警告/错误:")
        for e in result["errors"]:
            print(f"   - {e}")
        sys.exit(1)
    else:
        print("\n🎉 全部通过!")
        sys.exit(0)


if __name__ == "__main__":
    main()

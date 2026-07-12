"""基础设施层 - 配置与预设管理（文件持久化 + 缓存）"""
import os, json
from core.constants import CONFIG_FILE, PRESET_FILE, _flog

# ─── 配置管理 ──────────────────────────────────
def load_config() -> dict:
    d = {"last_preset": "", "current_game": "二重螺旋",
         "games": ["二重螺旋", "鸣潮", "原神", "绝区零"]}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                d.update(json.load(f))
        except Exception:
            pass
    return d

def save_config(**kw) -> None:
    d = load_config()
    d.update(kw)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except OSError:
        pass

# ── 别名 ──
cfg_load = load_config
cfg_save = save_config

# ─── 预设管理（委托到 CacheManager）───────────
def get_presets():
    from core.cache import CacheManager
    return CacheManager.instance().get_presets()

def save_presets(data):
    from core.cache import CacheManager
    CacheManager.instance().set_presets(data)

def get_preset(name: str):
    for p in get_presets():
        if p["name"] == name:
            return p
    return None

def save_preset(preset: dict):
    data = [p for p in get_presets() if p["name"] != preset["name"]]
    data.append(preset)
    save_presets(data)

def del_preset(name: str):
    save_presets([p for p in get_presets() if p["name"] != name])

# ── 别名 ──
preset_load_all = get_presets
preset_save_all = save_presets
preset_get = get_preset
preset_save = save_preset
preset_del = del_preset

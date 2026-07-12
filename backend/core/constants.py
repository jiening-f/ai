"""基础设施层 - 路径常量 / 步骤常量 / 日志"""
import os, sys, time, json

# ─── 路径常量（后端专用，固定 DATA_DIR）──
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE_DIR)

# DATA_DIR 指向 全能脚本/data/
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
TEMPLATE_DIR = os.path.join(DATA_DIR, "templates")
SCREENSHOT_DIR = os.path.join(DATA_DIR, "screenshots")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
PRESET_FILE = os.path.join(DATA_DIR, "presets.json")
LOG_FILE = os.path.join(DATA_DIR, "debug.log")
os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


# ─── 日志 ──────────────────────────────────────
def _flog(msg: str) -> None:
    try:
        # 日志文件超过512KB时截断，保留后256KB
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 512 * 1024:
            with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                f.writelines(lines[-(len(lines)//2):])
                f.write(f"[{time.strftime('%H:%M:%S')}] [日志截断]\n")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except Exception:
        pass


# ─── 步骤常量 ─────────────────────────────────
class StepType:
    NONE = "none"; TEXT = "text"; IMAGE = "image"
    KEY = "press_key"; CLICK_TEXT = "click_text"
    CLICK_IMAGE = "click_image"; CLICK_NEAR = "click_near_image"; SWIPE = "mouse_swipe"

    COND_CN = {"直接执行": NONE, "文字识别": TEXT, "模板识别": IMAGE}
    COND_EN = {NONE: "直接执行", TEXT: "文字识别", IMAGE: "模板识别"}
    COND_LIST = list(COND_CN.keys())
    ACT_CN = {"按下按键": KEY, "点击识别文字": CLICK_TEXT,
              "点击识别图片": CLICK_IMAGE, "点击图片附近坐标": CLICK_NEAR, "鼠标滑动": SWIPE}
    ACT_EN = {KEY: "按下按键", CLICK_TEXT: "点击识别文字",
              CLICK_IMAGE: "点击识别图片", CLICK_NEAR: "点击图片附近坐标", SWIPE: "鼠标滑动"}
    ACT_LIST = list(ACT_CN.keys())

    @staticmethod
    def new_step(ct=NONE, cv="", at=KEY, av="", duration=0.2, delay=0, count=0, enabled=True, verify_text=""):
        return {"condition_type": ct, "condition_value": cv, "action_type": at,
                "action_value": av, "duration": duration, "delay": delay,
                "count": count, "enabled": enabled, "verify_text": verify_text}

    @staticmethod
    def new_preset(name="新建预设", game="二重螺旋"):
        return {"name": name, "game": game, "steps": [], "max_runs": 0, "round_interval": 0, "chain": True}

    @staticmethod
    def step_desc(s: dict) -> str:
        ct, cv, at, av, dur_raw, dly_raw = (s.get(k) for k in
            ("condition_type","condition_value","action_type","action_value","duration","delay"))
        try: dur = float(dur_raw or 0)
        except: dur = 0
        try: dly = float(dly_raw or 0)
        except: dly = 0
        en = "✓" if s.get("enabled", True) else "✗"
        cond = "直" if (ct in (None, StepType.NONE) or not cv) else (
            f"图«{cv}»" if ct == StepType.IMAGE else f"文«{cv}»")
        act_map = {StepType.KEY: f"按键«{av}»", StepType.CLICK_TEXT: f"点文字«{av}»",
                   StepType.CLICK_IMAGE: f"点图«{av}»", StepType.CLICK_NEAR: f"图偏移«{av}»",
                   StepType.SWIPE: f"滑动«{av}»"}
        act = act_map.get(at, av)
        extras = []
        if dly > 0: extras.append(f"延{dly}s")
        if dur >= 1: extras.append(f"按住{dur}s")
        elif dur > 0: extras.append(f"按{dur}s")
        result = f"[{en}] {cond} → {act}" + (f" ({' | '.join(extras)})" if extras else "")
        return result


# ── 向后兼容别名 ──
C_NONE = StepType.NONE; C_TEXT = StepType.TEXT; C_IMAGE = StepType.IMAGE
A_KEY = StepType.KEY; A_CLICK_TEXT = StepType.CLICK_TEXT
A_CLICK_IMAGE = StepType.CLICK_IMAGE; A_CLICK_NEAR = StepType.CLICK_NEAR
A_SWIPE = StepType.SWIPE
COND_CN, COND_EN, COND_LIST = StepType.COND_CN, StepType.COND_EN, StepType.COND_LIST
ACT_CN, ACT_EN, ACT_LIST = StepType.ACT_CN, StepType.ACT_EN, StepType.ACT_LIST
new_step, new_preset, step_desc = StepType.new_step, StepType.new_preset, StepType.step_desc

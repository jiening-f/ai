"""业务逻辑层 - 窗口管理 / 脚本执行引擎"""
import time, threading
from typing import Optional, Callable

from core.constants import StepType, _flog
from engine.vision import OCR, TemplateMatcher, Screenshot
from engine.input_sim import InputFront, InputBg, AntiDetect

try:
    import win32gui, win32con, win32api, win32process
    _HAS_W32 = True
except: _HAS_W32 = False

try:
    import pyautogui
except: pyautogui = None


# ══ 窗口管理 ══════════════════════════════════

class WindowMgr:
    @staticmethod
    def find(title=None):
        if not _HAS_W32: return None, None
        st = title or "二重螺旋"
        hwnd = win32gui.FindWindow(None, st)
        if hwnd:
            wt = win32gui.GetWindowText(hwnd)
            if "脚本" not in wt and "工作站" not in wt:
                rc = win32gui.GetWindowRect(hwnd)
                if rc[2]-rc[0] >= 400 and rc[3]-rc[1] >= 300:
                    return hwnd, rc
        st = st.lower(); results = []
        def cb(h,_):
            if win32gui.IsWindowVisible(h):
                wt = win32gui.GetWindowText(h)
                if st in wt.lower() and "脚本" not in wt and "工作站" not in wt:
                    rc = win32gui.GetWindowRect(h)
                    if rc[2]-rc[0] >= 400 and rc[3]-rc[1] >= 300:
                        results.append(h)
        win32gui.EnumWindows(cb, None)
        if results: return results[0], win32gui.GetWindowRect(results[0])
        return None, None

    @staticmethod
    def bring_to_top(hwnd):
        if not _HAS_W32 or not hwnd: return
        try:
            if not win32gui.IsWindow(hwnd): _flog("窗口句柄失效"); return
            if win32gui.IsIconic(hwnd): win32gui.ShowWindow(hwnd, win32con.SW_RESTORE); time.sleep(0.2)
            # 策略1: AttachThreadInput
            try:
                cur_tid = win32api.GetCurrentThreadId()
                target_tid = win32process.GetWindowThreadProcessId(hwnd)[0]
                win32process.AttachThreadInput(cur_tid, target_tid, True)
                win32gui.SetForegroundWindow(hwnd)
                win32gui.BringWindowToTop(hwnd)
                time.sleep(0.1)
                win32process.AttachThreadInput(cur_tid, target_tid, False)
                return
            except Exception:
                pass
            # 策略2: Alt键模拟（绕过前台锁最可靠的方式）
            try:
                win32api.keybd_event(0x12, 0, 0, 0)  # Alt 按下
                time.sleep(0.02)
                win32gui.SetForegroundWindow(hwnd)
                win32gui.BringWindowToTop(hwnd)
                time.sleep(0.02)
                win32api.keybd_event(0x12, 0, win32con.KEYEVENTF_KEYUP, 0)  # Alt 抬起
                return
            except Exception:
                pass
            # 策略3: 直接调用
            win32gui.SetForegroundWindow(hwnd)
            win32gui.BringWindowToTop(hwnd)
        except Exception as e: _flog(f"窗口置前异常: {e}")

    @staticmethod
    def enumerate():
        if not _HAS_W32: return []
        r = []
        def cb(h,p):
            if win32gui.IsWindowVisible(h):
                t = win32gui.GetWindowText(h); rc = win32gui.GetWindowRect(h)
                if t and rc[2]-rc[0] > 300 and rc[3]-rc[1] > 200:
                    p.append((t,h,rc))
        win32gui.EnumWindows(cb, r)
        return r


# ── 别名 ──
win_find = WindowMgr.find
win_top = WindowMgr.bring_to_top
win_enum = WindowMgr.enumerate


# ══ 脚本执行引擎 ══════════════════════════════

class ScriptEngine:
    def __init__(self):
        self.running = False
        self.stop_after = 0
        self._stop_ev = threading.Event()
        self._mon = {"step":0,"total":0,"action":"","error":"","status":"待命"}
        self.background_mode = False
        self._game_hwnd = None  # 当前游戏窗口句柄

    def stop(self): self._stop_ev.set(); self.running = False
    def is_stopped(self) -> bool: return self._stop_ev.is_set()
    def monitor(self): return dict(self._mon)
    def _sleep(self, sec): self._stop_ev.wait(timeout=sec)

    def _verify_game_window(self) -> bool:
        """检查游戏窗口是否仍然存在且有效，仅窗口完全关闭时停止"""
        hwnd = getattr(self, '_game_hwnd', None)
        if hwnd is None:
            return True  # 未指定窗口，不做检查
        try:
            return win32gui.IsWindow(hwnd)
        except Exception:
            return False

    def _exec_action(self, at, av, dur, bg, hwnd, on_log, region, s=None):
        _bgh = hwnd if bg else None
        if at == StepType.KEY:
            if bg and hwnd:
                if dur > 0: InputBg.hold(hwnd, av, dur)
                else: InputBg.press(hwnd, av)
            else:
                InputFront.hold(av, dur) if dur > 0 else InputFront.press(av)
            if on_log: on_log(f"    OK 按键«{av}»")
            return True

        if at == StepType.CLICK_TEXT:
            if on_log: on_log(f"    等文字«{av}»并点击...")
            pos = None
            while self.running and not self._stop_ev.is_set():
                pos = OCR.find_text(av, region, 0.5, hwnd=_bgh)
                if pos:
                    if bg and hwnd:
                        InputBg.click(hwnd, pos[0], pos[1])
                    else:
                        InputFront.click(pos[0], pos[1], fast=True)
                    if on_log: on_log(f"    OK 点击文字«{av}»")
                    return True
                self._sleep(0.3)
            # 走到这里说明被停止了
            return False

        if at == StepType.CLICK_IMAGE:
            pos = TemplateMatcher.find(av, region, hwnd=_bgh)
            if pos:
                verify = s.get("verify_text","").strip() if s else ""
                if verify:
                    vr = (pos[0]-60, pos[1]-20, 120, 40) if region else None
                    vp = OCR.find_text(verify, vr, 2, hwnd=_bgh)
                    if not vp:
                        if on_log: on_log(f"    BLOCK 安全拦截: «{verify}»")
                        self._mon["error"] = f"安全拦截: «{verify}»"
                        return True
                if bg and hwnd: InputBg.click(hwnd, pos[0], pos[1])
                else: InputFront.click(pos[0], pos[1], fast=True)
                if on_log: on_log(f"    OK 点图«{av}»")
                return True
            else:
                if on_log: on_log(f"    !! 未找到«{av}»")
                self._mon["error"] = f"未找到图片«{av}»"
                return False

        if at == StepType.CLICK_NEAR and "," in av:
            parts = av.replace("，",",").split(",")
            if len(parts) >= 3:
                dx, dy = int(parts[0]), int(parts[1])
                tn = ",".join(parts[2:]).strip()
                if tn:
                    pos = TemplateMatcher.find(tn, region, hwnd=_bgh)
                    if pos:
                        tx, ty = pos[0]-dx, pos[1]-dy
                        if bg and hwnd: InputBg.click(hwnd, tx, ty)
                        else: InputFront.click(tx, ty, fast=True)
                        return True
                    else:
                        if on_log: on_log(f"    !! 未找到参考图«{tn}»")
                        self._mon["error"] = f"未找到图片«{tn}»"
                        return False
                else:
                    if on_log: on_log(f"    !! 未指定参考图")
                    return False
            return True

        if at == StepType.SWIPE and "," in av:
            parts = av.replace("，",",").split(",")
            if len(parts) >= 2:
                dx, dy = int(parts[0]), int(parts[1])
                sd = float(parts[2]) if len(parts)>=3 and parts[2].strip() else 0.5
                tn = ",".join(parts[3:]).strip() if len(parts)>=4 else ""
                pos = TemplateMatcher.find(tn, region, hwnd=_bgh) if tn else None
                if tn and not pos:
                    if on_log: on_log(f"    !! 未找到起始图«{tn}»")
                    self._mon["error"] = f"未找到图片«{tn}»"
                    return False
                else:
                    if bg and hwnd:
                        if pos: InputBg.swipe(hwnd, pos[0], pos[1], dx, dy, sd)
                        else:
                            rc = win32gui.GetWindowRect(hwnd)
                            InputBg.swipe(hwnd, (rc[2]-rc[0])//2, (rc[3]-rc[1])//2, dx, dy, sd)
                    else:
                        if pos: AntiDetect.human_move(pos[0], pos[1]); time.sleep(AntiDetect.delay(0.04,0.06))
                        pyautogui.drag(dx, dy, duration=sd)
                    if on_log: on_log(f"    OK 滑动({dx},{dy}) {sd}s")
                    return True
            return True
        return True

    def run(self, preset, chain=True, on_log=None, on_done=None,
            region=None, hwnd=None, override_max_runs=None, override_ri=None,
            game_hwnd=None):
        """运行预设，game_hwnd 为游戏窗口句柄（用于检测窗口是否存活）"""
        bg = self.background_mode and hwnd is not None
        self._game_hwnd = game_hwnd
        steps = [s for s in preset.get("steps",[]) if s.get("enabled",True)]
        if not steps:
            if on_log: on_log("!! 流程为空")
            if on_done: on_done(); return
        max_runs = override_max_runs if override_max_runs is not None else preset.get("max_runs",0)
        ri = override_ri if override_ri is not None else preset.get("round_interval",0)
        need_ocr = any(s.get("condition_type")==StepType.TEXT or s.get("action_type")==StepType.CLICK_TEXT for s in steps)
        if need_ocr and not OCR.instance().init():
            if on_log: on_log("OCR初始化失败"); on_done and on_done(); return
        self.running = True; self._stop_ev.clear()
        n = 0; total = len(steps)
        while self.running and not self._stop_ev.is_set():
            n += 1
            if max_runs > 0 and n > max_runs: break
            if self.stop_after > 0 and n > self.stop_after: break
            # 检查游戏窗口是否仍在运行
            if not self._verify_game_window():
                if on_log: on_log("!! 游戏窗口已关闭或最小化，自动停止")
                break
            if on_log: on_log(f"\n{'─'*35}\n第 {n} 轮")
            ok = True
            for i, s in enumerate(steps):
                self._mon = {"step":i+1,"total":total,"action":s.get("action_value",""),"error":"","status":"执行中"}
                ct, cv, at, av, dur, dly = (s.get(k) for k in ("condition_type","condition_value","action_type","action_value","duration","delay"))
                if dly > 0: self._sleep(dly)
                if not self.running: break
                _bgh = hwnd if bg else None
                if ct and cv.strip():
                    if ct == StepType.TEXT:
                        if on_log: on_log(f"  [{i+1}/{total}] 等文字«{cv}»...")
                        pos = None
                        while self.running and not self._stop_ev.is_set():
                            pos = OCR.find_text(cv, region, 0.5, hwnd=_bgh)
                            if pos: break
                            self._sleep(0.3)
                        if not self.running: break
                    elif ct == StepType.IMAGE:
                        if on_log: on_log(f"  [{i+1}/{total}] 等图片«{cv}»...")
                        pos = None
                        while self.running and not self._stop_ev.is_set():
                            pos = TemplateMatcher.find(cv, region, conf=0.78, hwnd=_bgh)
                            if pos: break
                            self._sleep(0.3)
                        if not self.running: break
                cnt = s.get("count", 1)
                if cnt <= 0:
                    try:
                        if not self._exec_action(at, av, dur, bg, hwnd, on_log, region, s):
                            ok = False
                    except Exception as e:
                        if on_log: on_log(f"    X {e}"); self._mon["error"] = str(e); ok = False
                else:
                    for _ in range(cnt):
                        if not self.running: break
                        try:
                            if not self._exec_action(at, av, dur, bg, hwnd, on_log, region, s):
                                ok = False; break
                        except Exception as e:
                            if on_log: on_log(f"    X {e}"); self._mon["error"] = str(e); ok = False; break
                if chain and not ok: break
                if not self.running: break
            if chain and not ok:
                if on_log: on_log(f"STOP 步骤中断，停止执行")
                break
            if ri > 0 and self.running: self._sleep(ri)
        self.running = False; self._mon["status"] = "已停止"
        if on_log: on_log("\n--- 结束 ---")
        if on_done: on_done()

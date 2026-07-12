"""业务逻辑层 - 输入模拟：前台/后台/SendInput + 反检测"""
import time, random, math, ctypes
from typing import Optional
from core.constants import _flog

try:
    import pyautogui
except: pyautogui = None

try:
    import win32gui, win32con, win32api
    _HAS_W32 = True
except: _HAS_W32 = False


# ══ 反检测 ════════════════════════════════════

class AntiDetect:
    @staticmethod
    def delay(base=0.05, jitter=0.15):
        d = abs(random.gauss(base, jitter*0.4))
        return min(max(d, 0.01), base+jitter*3)

    @staticmethod
    def _bezier(t, pts):
        x = ((1-t)**3*pts[0][0] + 3*(1-t)**2*t*pts[1][0] + 3*(1-t)*t**2*pts[2][0] + t**3*pts[3][0])
        y = ((1-t)**3*pts[0][1] + 3*(1-t)**2*t*pts[1][1] + 3*(1-t)*t**2*pts[2][1] + t**3*pts[3][1])
        return x, y

    @staticmethod
    def human_move(x, y):
        if pyautogui is None: return
        cx, cy = pyautogui.position()
        dist = math.hypot(x-cx, y-cy)
        if dist < 3: return
        if dist < 30: pyautogui.moveTo(x, y, duration=0.05); return
        mx = (cx+x)/2 + random.uniform(-dist*0.1, dist*0.1)
        my = (cy+y)/2 + random.uniform(-dist*0.1, dist*0.1)
        pts = [(cx,cy), ((cx+mx)//2, (cy+my)//2), ((mx+x)//2, (my+y)//2), (x,y)]
        for i in range(max(int(dist/15), 3)+1):
            px, py = AntiDetect._bezier(i/max(int(dist/15), 3), pts)
            pyautogui.moveTo(px, py, duration=0.001)

    @staticmethod
    def fast_move(x, y):
        if pyautogui is None: return
        pyautogui.moveTo(x, y, duration=0.03)

    @staticmethod
    def jitter():
        if pyautogui is None or random.random() < 0.4: return
        dx, dy = random.randint(-2, 2), random.randint(-2, 2)
        if dx or dy: pyautogui.moveRel(dx, dy, duration=random.uniform(0.01, 0.04))


# ══ 按键映射 ══════════════════════════════════

class KeyMap:
    ALIAS = {' ': 'space', '空格': 'space', 'space': 'space', 'enter': 'enter', 'return': 'enter'}
    VK = {
        'backspace':0x08,'tab':0x09,'enter':0x0D,'esc':0x1B,'space':0x20,
        'pageup':0x21,'pagedown':0x22,'end':0x23,'home':0x24,
        'left':0x25,'up':0x26,'right':0x27,'down':0x28,
        'printscreen':0x2C,'prtsc':0x2C,'insert':0x2D,'delete':0x2E,
        '0':0x30,'1':0x31,'2':0x32,'3':0x33,'4':0x34,'5':0x35,
        '6':0x36,'7':0x37,'8':0x38,'9':0x39,
        'a':0x41,'b':0x42,'c':0x43,'d':0x44,'e':0x45,'f':0x46,
        'g':0x47,'h':0x48,'i':0x49,'j':0x4A,'k':0x4B,'l':0x4C,
        'm':0x4D,'n':0x4E,'o':0x4F,'p':0x50,'q':0x51,'r':0x52,
        's':0x53,'t':0x54,'u':0x55,'v':0x56,'w':0x57,'x':0x58,
        'y':0x59,'z':0x5A,
        'numpad0':0x60,'numpad1':0x61,'numpad2':0x62,'numpad3':0x63,
        'numpad4':0x64,'numpad5':0x65,'numpad6':0x66,'numpad7':0x67,
        'numpad8':0x68,'numpad9':0x69,'numpadadd':0x6B,'numpadminus':0x6D,
        'f1':0x70,'f2':0x71,'f3':0x72,'f4':0x73,'f5':0x74,'f6':0x75,
        'f7':0x76,'f8':0x77,'f9':0x78,'f10':0x79,'f11':0x7A,'f12':0x7B,
        ';':0xBA,'=':0xBB,',':0xBC,'-':0xBD,'.':0xBE,'/':0xBF,
        '`':0xC0,'[':0xDB,'\\\\':0xDC,']':0xDD,"'":0xDE,
    }

    @staticmethod
    def normalize(key):
        k = key.strip().lower()
        return KeyMap.ALIAS.get(k, k)

    @staticmethod
    def to_vk(key):
        return KeyMap.VK.get(KeyMap.normalize(key))


# ══ 前台输入 ══════════════════════════════════

class InputFront:
    @staticmethod
    def click(x, y, fast=False):
        if pyautogui is None: return
        for att in range(2):
            try:
                ox, oy = random.randint(-2,2), random.randint(-2,2)
                if fast: AntiDetect.fast_move(x+ox, y+oy)
                else: AntiDetect.human_move(x+ox, y+oy)
                time.sleep(AntiDetect.delay(0.02, 0.04))
                pyautogui.click(x+ox, y+oy)
                return
            except Exception as e:
                if att == 0: _flog(f"点击重试: {e}"); time.sleep(0.2)

    @staticmethod
    def press(key):
        if pyautogui is None: _flog("pyautogui未加载"); return
        key = KeyMap.normalize(key)
        time.sleep(AntiDetect.delay(0.04, 0.08))
        pyautogui.press(key)

    @staticmethod
    def hold(key, duration):
        if pyautogui is None: return
        key = KeyMap.normalize(key)
        pyautogui.keyDown(key); time.sleep(duration); pyautogui.keyUp(key)


# ══ 后台输入 ══════════════════════════════════

class InputBg:
    @staticmethod
    def click(hwnd, x, y):
        """后台点击：SendInput 模拟真实鼠标事件
        PostMessage 对现代游戏无效（DirectInput/Raw Input 不读消息队列）
        SendInput 走完整输入栈，游戏能识别
        """
        # 先移动鼠标到目标位置
        ctypes.windll.user32.SetCursorPos(x, y)
        time.sleep(random.uniform(0.01, 0.03))
        # 用 SendInput 发送按下/抬起
        try:
            class _M(ctypes.Structure):
                _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long),
                           ("mouseData", ctypes.c_ulong), ("dwFlags", ctypes.c_ulong),
                           ("time", ctypes.c_ulong), ("dwExtraInfo", ctypes.c_size_t)]
            class _U(ctypes.Union):
                _fields_ = [("mi", _M)]
            class _I(ctypes.Structure):
                _fields_ = [("type", ctypes.c_ulong), ("u", _U)]
            mi_down = _M(0, 0, 0, 0x0002, 0, 0); u_down = _U(); u_down.mi = mi_down
            inp_down = _I(0, u_down)
            ctypes.windll.user32.SendInput(1, ctypes.pointer(inp_down), ctypes.sizeof(inp_down))
            time.sleep(random.uniform(0.02, 0.05))
            mi_up = _M(0, 0, 0, 0x0004, 0, 0); u_up = _U(); u_up.mi = mi_up
            inp_up = _I(0, u_up)
            ctypes.windll.user32.SendInput(1, ctypes.pointer(inp_up), ctypes.sizeof(inp_up))
            return
        except Exception as e:
            _flog(f"SendInput 点击异常: {e}")
        # 降级：PostMessage（兼容旧程序）
        lp = win32api.MAKELONG(x, y)
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lp)
        time.sleep(random.uniform(0.02, 0.05))
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, lp)

    @staticmethod
    def _key(hwnd, key, down):
        vk = KeyMap.to_vk(key)
        if vk is None: _flog(f"后台按键: 未知 '{key}'"); return
        msg = win32con.WM_KEYDOWN if down else win32con.WM_KEYUP
        win32api.PostMessage(hwnd, msg, vk, vk|(0x01<<24))

    @staticmethod
    def press(hwnd, key):
        k = KeyMap.normalize(key)
        InputBg._key(hwnd, k, True); time.sleep(random.uniform(0.03,0.06))
        InputBg._key(hwnd, k, False)

    @staticmethod
    def hold(hwnd, key, duration):
        k = KeyMap.normalize(key)
        InputBg._key(hwnd, k, True); time.sleep(duration); InputBg._key(hwnd, k, False)

    @staticmethod
    def swipe(hwnd, cx, cy, dx, dy, duration):
        """后台滑动（缓入缓出，更自然的鼠标轨迹）"""
        ox, oy = cx, cy
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, win32api.MAKELONG(ox,oy))
        steps = max(int(duration * 20), 8)
        for i in range(1, steps + 1):
            t = i / steps
            # 缓入缓出: easeInOutQuad
            if t < 0.5:
                ease = 2 * t * t
            else:
                ease = 1 - (-2 * t + 2) ** 2 / 2
            cur_x = ox + int(dx * ease)
            cur_y = oy + int(dy * ease)
            win32api.PostMessage(hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON,
                                 win32api.MAKELONG(cur_x, cur_y))
            time.sleep(duration / steps)
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, win32api.MAKELONG(ox+dx, oy+dy))

    @staticmethod
    def swipe_fast(hwnd, cx, cy, dx, dy):
        """快速后台滑动（少步数，适合短距离快速拖动）"""
        ox, oy = cx, cy
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, win32api.MAKELONG(ox,oy))
        steps = max(int(abs(dx + dy) / 30), 3)
        for i in range(1, steps + 1):
            t = i / steps
            if t < 0.5:
                ease = 2 * t * t
            else:
                ease = 1 - (-2 * t + 2) ** 2 / 2
            win32api.PostMessage(hwnd, win32con.WM_MOUSEMOVE, win32con.MK_LBUTTON,
                                 win32api.MAKELONG(ox + int(dx * ease), oy + int(dy * ease)))
            time.sleep(0.01)
        win32api.PostMessage(hwnd, win32con.WM_LBUTTONUP, 0, win32api.MAKELONG(ox+dx, oy+dy))


# ══ SendInput ══════════════════════════════════

class InputSend:
    @staticmethod
    def key(key, down):
        vk = KeyMap.to_vk(key)
        if vk is None: return False
        try:
            class _K(ctypes.Structure):
                _fields_ = [("wVk",ctypes.c_ushort),("wScan",ctypes.c_ushort),
                            ("dwFlags",ctypes.c_ulong),("time",ctypes.c_ulong),
                            ("dwExtraInfo",ctypes.c_size_t)]
            class _U(ctypes.Union):
                _fields_ = [("ki",_K),("mi",ctypes.c_byte*8),("hi",ctypes.c_byte*8)]
            class _I(ctypes.Structure):
                _fields_ = [("type",ctypes.c_ulong),("u",_U)]
            flags = 0 if down else 0x0002
            ki = _K(vk,0,flags,0,0); u = _U(); u.ki = ki; inp = _I(1, u)
            ctypes.windll.user32.SendInput(1, ctypes.pointer(inp), ctypes.sizeof(inp))
            return True
        except ctypes.ArgumentError as e: _flog(f"SendInput: {e}"); return False

    @staticmethod
    def press(key):
        InputSend.key(key, True); time.sleep(random.uniform(0.03,0.06)); InputSend.key(key, False)

    @staticmethod
    def hold(key, duration):
        InputSend.key(key, True); time.sleep(duration); InputSend.key(key, False)


# ── 旧接口别名 ──
_normalize_key = KeyMap.normalize
_key_to_vk = KeyMap.to_vk
_click_bg = InputBg.click
_swipe_bg = InputBg.swipe
_sendinput_key = InputSend.key
_human_move = AntiDetect.human_move
_human_jitter = AntiDetect.jitter
_natural_delay = AntiDetect.delay

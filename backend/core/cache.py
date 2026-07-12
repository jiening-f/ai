"""基础设施层 - 缓存系统（LRU图像/模板列表/缩放比例）"""
import os, json, threading
from collections import OrderedDict
from typing import Optional, Any

import cv2
import numpy as np

from core.constants import TEMPLATE_DIR, PRESET_FILE, _flog, StepType

# ─── 图像IO ───────────────────────────────────
def cv_read(path: str):
    try:
        if cv2 is None: return None
        return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    except Exception as e:
        _flog(f"图像读取失败 {os.path.basename(path)}: {e}")
        return None

def cv_write(path: str, img):
    try:
        if cv2 is None: return False
        ok, buf = cv2.imencode(os.path.splitext(path)[1], img)
        if ok: buf.tofile(path)
        return ok
    except Exception as e:
        _flog(f"图像写入失败: {e}")
        return False

_cv_read = cv_read
_cv_write = cv_write


class _LRU:
    """线程安全 LRU 缓存"""
    def __init__(self, maxsize=32):
        self._max = maxsize
        self._data: OrderedDict = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                return self._data[key]
        return None

    def put(self, key, value):
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
            else:
                if len(self._data) >= self._max:
                    self._data.popitem(last=False)
                self._data[key] = value

    def clear(self):
        with self._lock:
            self._data.clear()


class CacheManager:
    """统一缓存管理"""
    _inst: Optional['CacheManager'] = None

    def __init__(self):
        self._img_cache = _LRU(32)
        self._scale_cache = _LRU(64)
        self._presets: Optional[list] = None
        self._templates: Optional[list] = None
        self._tmpl_lock = threading.Lock()

    @classmethod
    def instance(cls):
        if cls._inst is None:
            cls._inst = cls()
        return cls._inst

    # ── 图像缓存 ──
    def get_image(self, path):
        img = self._img_cache.get(path)
        if img is not None: return img
        img = cv_read(path)
        if img is not None: self._img_cache.put(path, img)
        return img

    def clear_images(self):
        self._img_cache.clear()
        self._scale_cache.clear()

    # ── 缩放列表缓存 ──
    def get_scales(self, ref_w, tpl_w, tpl_h, fast=False):
        key = (ref_w, tpl_w, tpl_h, fast)
        scales = self._scale_cache.get(key)
        if scales: return scales
        scales = self._build_scales(ref_w, fast)
        self._scale_cache.put(key, scales)
        return scales

    @staticmethod
    def _build_scales(ref_w, fast=False):
        if fast:
            base = ref_w / 1920.0
            core = [0.7, 0.85, 1.0, 1.15, 1.3]
            s = [base * c for c in core]
            return sorted(s)
        base = ref_w / 1920.0
        s = set()
        for o in [-0.15,-0.10,-0.07,-0.05,-0.03,-0.02,-0.01,0,
                  0.01,0.02,0.03,0.05,0.07,0.10,0.15]:
            v = round(base + o, 2)
            if 0.3 <= v <= 3.0: s.add(v)
        for v in [0.5,0.6,0.7,0.8,0.9,1.0,1.2,1.5,1.7,2.0,2.5]:
            if 0.3 <= v <= 3.0: s.add(v)
        for v in [0.25,0.35,3.5]:
            if 0.25 <= v <= 3.5: s.add(v)
        return sorted(s)

    # ── 预设缓存 ──
    def get_presets(self):
        if self._presets is not None: return self._presets
        if os.path.exists(PRESET_FILE):
            try:
                with open(PRESET_FILE, "r", encoding="utf-8") as f:
                    self._presets = json.load(f)
                    return self._presets
            except json.JSONDecodeError:
                _flog("预设文件损坏，重置为默认")
        self._presets = [StepType.new_preset("默认预设", "二重螺旋")]
        return self._presets

    def set_presets(self, data):
        self._presets = data
        try:
            with open(PRESET_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            _flog(f"预设保存失败: {e}")

    # ── 模板列表缓存 ──
    def get_templates(self):
        if self._templates is not None: return self._templates
        if not os.path.isdir(TEMPLATE_DIR):
            self._templates = []; return []
        self._templates = sorted(f[:-4] for f in os.listdir(TEMPLATE_DIR) if f.endswith(".png"))
        return self._templates

    def clear_templates(self):
        with self._tmpl_lock:
            self._templates = None
        self.clear_images()

    def clear_all(self):
        self._presets = None; self._templates = None
        self.clear_images()

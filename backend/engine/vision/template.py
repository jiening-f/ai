"""视觉子系统 - 模板匹配

基于 OpenCV cv2.matchTemplate 的模板匹配，支持：
- 多种匹配方法（TM_CCOEFF_NORMED 默认）
- 多尺度匹配（可配置缩放范围和步长）
- 多目标匹配（threshold 以上的所有匹配点 + IoU NMS 去重）
- 形状 + 颜色双重验证（CLAHE + Canny 边缘 + HSV 色相）
- 灰度匹配加速（快速模式）
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

from core.constants import TEMPLATE_DIR, _flog

# ── 匹配方法映射 ──

MATCH_METHODS: Dict[str, int] = {
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED if cv2 else 5,
    "TM_CCOEFF": cv2.TM_CCOEFF if cv2 else 4,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED if cv2 else 3,
    "TM_CCORR": cv2.TM_CCORR if cv2 else 2,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED if cv2 else 1,
    "TM_SQDIFF": cv2.TM_SQDIFF if cv2 else 0,
}

# 默认缩放范围
DEFAULT_SCALE_RANGE = (0.8, 1.2, 0.05)

# ── 快速模式 ──
_FAST_MODE = False


def set_fast_mode(fast: bool) -> None:
    """切换快速模式/高精度模式"""
    global _FAST_MODE
    _FAST_MODE = fast
    _flog(f"模板匹配: {'快速模式' if fast else '高精度模式'}")


def _build_scales(
    t_w: int, t_h: int, s_w: int, s_h: int,
    scale_min: float, scale_max: float, scale_step: float,
    fast: bool = False,
) -> List[float]:
    """构建多尺度缩放列表"""
    if fast:
        # 快速模式：5 个关键缩放比例
        base = s_w / 1920.0
        cores = [0.7, 0.85, 1.0, 1.15, 1.3]
        scales = [base * c for c in cores]
        return sorted(s for s in scales if scale_min <= s <= scale_max)

    # 高精度模式：从步长生成
    scales = []
    s = scale_min
    while s <= scale_max + 1e-9:
        # 过滤无效缩放
        w, h = int(t_w * s), int(t_h * s)
        if w >= 8 and h >= 8 and w <= s_w and h <= s_h:
            scales.append(round(s, 4))
        s += scale_step
    return scales


# ══ 结果类型 ══


@dataclass
class MatchResult:
    """单次模板匹配结果"""

    position: Tuple[int, int]   # 匹配中心点 (x, y)
    confidence: float            # 匹配置信度 0.0~1.0
    scale: float = 1.0           # 匹配时的缩放比例
    method: str = "TM_CCOEFF_NORMED"  # 匹配方法
    bbox: Optional[Tuple[int, int, int, int]] = None  # 边界框 (x, y, w, h)

    def to_dict(self) -> dict:
        """转为字典，方便序列化"""
        return {
            "position": self.position,
            "confidence": self.confidence,
            "scale": self.scale,
            "method": self.method,
            "bbox": self.bbox,
        }


# ══ 模板匹配器 ══


class TemplateMatcher:
    """模板匹配服务

    形状 + 颜色双重验证：
    1. CLAHE 灰度匹配 → 找形状（TM_CCOEFF_NORMED）
    2. Canny 边缘二次确认 → 排除纹理误匹配
    3. HSV 色相一致度验证 → 区分不同颜色的相似形状

    用法:
        # 单目标匹配（向后兼容的简单接口）
        pos = TemplateMatcher.find("button", region=(0,0,500,500))
        # → (x, y) 或 None

        # 单目标匹配（完整结果）
        result = TemplateMatcher.match("button")
        # → MatchResult(position=(x,y), confidence=0.92, ...)

        # 多目标匹配
        results = TemplateMatcher.find_all("button", conf=0.8)
        # → [MatchResult, MatchResult, ...]
    """

    # ── 公共 API ──

    @staticmethod
    def find(
        name: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        conf: float = 0.72,
        hwnd: Optional[int] = None,
    ) -> Optional[Tuple[int, int]]:
        """查找模板位置（向后兼容的简化接口）

        返回:
            (x, y) 匹配中心点，未找到返回 None
        """
        result = TemplateMatcher.match(name, region=region, conf=conf, hwnd=hwnd)
        if result is not None:
            return result.position
        return None

    @staticmethod
    def match(
        name: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        conf: float = 0.72,
        hwnd: Optional[int] = None,
        method: str = "TM_CCOEFF_NORMED",
        scale_range: Optional[Tuple[float, float, float]] = None,
    ) -> Optional[MatchResult]:
        """单目标模板匹配（返回完整结果）

        参数:
            name:        模板名称（不含扩展名）或完整文件路径
            region:      (x, y, w, h) 搜索区域，None 为全屏
            conf:        最低置信度阈值
            hwnd:        目标窗口句柄（后台模式）
            method:      匹配方法，见 MATCH_METHODS
            scale_range: (min, max, step) 缩放范围

        返回:
            MatchResult 或 None
        """
        if cv2 is None:
            _flog("模板匹配失败: OpenCV 未安装")
            return None

        # 加载模板图像
        template = TemplateMatcher._load_template(name)
        if template is None:
            return None

        # 截图
        from engine.vision.screenshot import Screenshot
        screen = Screenshot.capture(region, hwnd)
        if screen is None:
            return None

        return TemplateMatcher._match_image(
            template, screen, conf, method, scale_range, region,
        )

    @staticmethod
    def find_all(
        name: str,
        region: Optional[Tuple[int, int, int, int]] = None,
        conf: float = 0.75,
        hwnd: Optional[int] = None,
        method: str = "TM_CCOEFF_NORMED",
        scale_range: Optional[Tuple[float, float, float]] = None,
    ) -> List[MatchResult]:
        """多目标模板匹配（找出所有匹配位置）

        参数同 match()，返回所有置信度 >= conf 的匹配结果。
        使用 IoU NMS 去重。
        """
        if cv2 is None:
            return []

        template = TemplateMatcher._load_template(name)
        if template is None:
            return []

        from engine.vision.screenshot import Screenshot
        screen = Screenshot.capture(region, hwnd)
        if screen is None:
            return []

        return TemplateMatcher._match_all(
            template, screen, conf, method, scale_range, region,
        )

    @staticmethod
    def to_dict_list(results: List[MatchResult]) -> List[dict]:
        """将 MatchResult 列表转为字典列表"""
        return [r.to_dict() for r in results]

    # ── 图像预处理 ──

    @staticmethod
    def _preprocess_gray(img: np.ndarray) -> np.ndarray:
        """灰度 + CLAHE 标准化光照"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(gray)

    @staticmethod
    def _canny_edge(img: np.ndarray) -> np.ndarray:
        """Canny 边缘检测"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (3, 3), 0)
        return cv2.Canny(blur, 50, 150)

    # ── 内部实现 ──

    @staticmethod
    def _load_template(name: str) -> Optional[np.ndarray]:
        """加载模板图像"""
        path = name if os.path.isfile(name) else os.path.join(TEMPLATE_DIR, f"{name}.png")
        if not os.path.isfile(path):
            _flog(f"模板文件不存在: {path}")
            return None

        try:
            from core.cache import CacheManager
            cache = CacheManager.instance()
            template = cache.get_image(path)
            if template is not None:
                return template
        except Exception:
            pass

        # 直接读取
        try:
            template = cv2.imdecode(
                np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR
            )
            return template
        except Exception as e:
            _flog(f"模板加载失败 {path}: {e}")
            return None

    @staticmethod
    def _match_image(
        template: np.ndarray,
        screen: np.ndarray,
        conf: float,
        method: str,
        scale_range: Optional[Tuple[float, float, float]],
        region: Optional[Tuple[int, int, int, int]],
    ) -> Optional[MatchResult]:
        """对截图执行单目标匹配"""
        t_h, t_w = template.shape[:2]
        s_h, s_w = screen.shape[:2]

        match_method = MATCH_METHODS.get(method, MATCH_METHODS["TM_CCOEFF_NORMED"])

        # 构建缩放列表
        sr = scale_range or DEFAULT_SCALE_RANGE
        scales = _build_scales(t_w, t_h, s_w, s_h, sr[0], sr[1], sr[2], _FAST_MODE)

        # 预处理
        tmpl_gray = TemplateMatcher._preprocess_gray(template)
        scr_gray = TemplateMatcher._preprocess_gray(screen)

        # 区域偏移
        ox = region[0] if region else 0
        oy = region[1] if region else 0

        best_confidence = 0.0
        best_result: Optional[MatchResult] = None

        for scale in scales:
            w, h = int(t_w * scale), int(t_h * scale)
            if w < 8 or h < 8 or w > s_w or h > s_h:
                continue

            rsz = cv2.resize(
                tmpl_gray, (w, h),
                interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC,
            )
            res = cv2.matchTemplate(scr_gray, rsz, match_method)
            _, v, _, loc = cv2.minMaxLoc(res)

            # 对 SQDIFF 方法取反（值越小越匹配）
            if match_method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
                v = 1.0 - v

            # 高精度模式：边缘 + 颜色双重验证
            if not _FAST_MODE and v > 0.65:
                v = TemplateMatcher._verify_shape_color(
                    template, screen, loc[0], loc[1], w, h, scale, v,
                )

            if v > best_confidence:
                best_confidence = v
                cx = loc[0] + w // 2 + ox
                cy = loc[1] + h // 2 + oy
                best_result = MatchResult(
                    position=(cx, cy),
                    confidence=round(v, 4),
                    scale=round(scale, 4),
                    method=method,
                    bbox=(loc[0] + ox, loc[1] + oy, w, h),
                )
                if best_confidence >= conf:
                    break

        if best_confidence >= conf and best_result is not None:
            return best_result
        return None

    @staticmethod
    def _verify_shape_color(
        template: np.ndarray,
        screen: np.ndarray,
        tx: int, ty: int,
        w: int, h: int,
        scale: float,
        base_confidence: float,
    ) -> float:
        """形状 + 颜色双重验证，返回综合置信度"""
        # Canny 边缘验证
        t_edge = TemplateMatcher._canny_edge(template)
        s_edge = TemplateMatcher._canny_edge(screen)
        rsz_edge = cv2.resize(
            t_edge, (w, h),
            interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC,
        )
        e_res = cv2.matchTemplate(s_edge, rsz_edge, cv2.TM_CCOEFF_NORMED)
        _, ev, _, _ = cv2.minMaxLoc(e_res)
        ev = max(0.0, ev)

        # HSV 颜色验证
        cs = TemplateMatcher._color_similarity(
            template, screen, tx, ty, w, h, scale,
        )

        # 综合评分：形状 50% + 边缘 20% + 颜色 30%
        return base_confidence * 0.5 + ev * 0.2 + cs * 0.3

    @staticmethod
    def _color_similarity(
        template_bgr: np.ndarray,
        screen_bgr: np.ndarray,
        tx: int, ty: int,
        tw: int, th: int,
        scale: float,
    ) -> float:
        """HSV 色相一致度比较（0.0~1.0）"""
        t_h, t_w = template_bgr.shape[:2]
        sw, sh = int(t_w * scale), int(t_h * scale)
        if sw < 4 or sh < 4:
            return 0.5

        tmpl_scaled = cv2.resize(
            template_bgr, (sw, sh),
            interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC,
        )

        h, w = screen_bgr.shape[:2]
        x1, y1 = max(0, tx), max(0, ty)
        x2, y2 = min(w, tx + sw), min(h, ty + sh)
        if x2 - x1 < 8 or y2 - y1 < 8:
            return 0.5

        screen_roi = screen_bgr[y1:y2, x1:x2]
        screen_roi = cv2.resize(screen_roi, (sw, sh))

        tmpl_hsv = cv2.cvtColor(tmpl_scaled, cv2.COLOR_BGR2HSV)
        roi_hsv = cv2.cvtColor(screen_roi, cv2.COLOR_BGR2HSV)

        # H 通道直方图比较
        h_bins = 30
        tmpl_hist = cv2.calcHist([tmpl_hsv], [0], None, [h_bins], [0, 180])
        roi_hist = cv2.calcHist([roi_hsv], [0], None, [h_bins], [0, 180])
        cv2.normalize(tmpl_hist, tmpl_hist, 0, 1, cv2.NORM_MINMAX)
        cv2.normalize(roi_hist, roi_hist, 0, 1, cv2.NORM_MINMAX)
        color_score = max(0.0, cv2.compareHist(tmpl_hist, roi_hist, cv2.HISTCMP_CORREL))

        # S、V 通道验证
        for ch in [1, 2]:
            th = cv2.calcHist([tmpl_hsv], [ch], None, [10], [0, 256])
            rh = cv2.calcHist([roi_hsv], [ch], None, [10], [0, 256])
            cv2.normalize(th, th, 0, 1, cv2.NORM_MINMAX)
            cv2.normalize(rh, rh, 0, 1, cv2.NORM_MINMAX)
            ch_corr = cv2.compareHist(th, rh, cv2.HISTCMP_CORREL)
            color_score = min(color_score, max(0.0, ch_corr))

        return color_score

    @staticmethod
    def _match_all(
        template: np.ndarray,
        screen: np.ndarray,
        conf: float,
        method: str,
        scale_range: Optional[Tuple[float, float, float]],
        region: Optional[Tuple[int, int, int, int]],
    ) -> List[MatchResult]:
        """多目标匹配"""
        t_h, t_w = template.shape[:2]
        s_h, s_w = screen.shape[:2]

        match_method = MATCH_METHODS.get(method, MATCH_METHODS["TM_CCOEFF_NORMED"])

        sr = scale_range or DEFAULT_SCALE_RANGE
        scales = _build_scales(t_w, t_h, s_w, s_h, sr[0], sr[1], sr[2], _FAST_MODE)

        ox = region[0] if region else 0
        oy = region[1] if region else 0

        tmpl_gray = TemplateMatcher._preprocess_gray(template)
        scr_gray = TemplateMatcher._preprocess_gray(screen)

        all_candidates: List[MatchResult] = []

        for scale in scales:
            w, h = int(t_w * scale), int(t_h * scale)
            if w < 8 or h < 8 or w > s_w or h > s_h:
                continue

            rsz = cv2.resize(
                tmpl_gray, (w, h),
                interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC,
            )
            res = cv2.matchTemplate(scr_gray, rsz, match_method)
            h_res, w_res = res.shape

            # 找所有超过阈值的点
            if match_method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
                threshold = 1.0 - conf
                ys, xs = np.where(res <= threshold)
                # 转为正向置信度
                scores = 1.0 - res[ys, xs]
            else:
                ys, xs = np.where(res >= conf)

            for xi, yi in zip(xs, ys):
                score = float(res[yi, xi])
                if match_method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
                    score = 1.0 - score

                cx = xi + w // 2 + ox
                cy = yi + h // 2 + oy
                all_candidates.append(MatchResult(
                    position=(cx, cy),
                    confidence=round(score, 4),
                    scale=round(scale, 4),
                    method=method,
                    bbox=(xi + ox, yi + oy, w, h),
                ))

        # IoU NMS 去重
        return TemplateMatcher._nms(all_candidates, iou_threshold=0.3)

    @staticmethod
    def _nms(
        results: List[MatchResult],
        iou_threshold: float = 0.3,
    ) -> List[MatchResult]:
        """IoU NMS 去重

        按置信度降序排列，保留高置信度结果，
        移除与已保留结果 IoU 过高的重复匹配。
        """
        if not results:
            return []

        # 按置信度降序排序（不修改原列表）
        sorted_results = sorted(results, key=lambda r: r.confidence, reverse=True)
        kept: List[MatchResult] = []

        for candidate in sorted_results:
            # 检查与已保留结果的 IoU
            overlap = False
            for existing in kept:
                iou = TemplateMatcher._compute_iou(candidate, existing)
                if iou > iou_threshold:
                    overlap = True
                    break

            if not overlap:
                kept.append(candidate)

        return kept

    @staticmethod
    def _compute_iou(a: MatchResult, b: MatchResult) -> float:
        """计算两个匹配结果的 IoU"""
        if a.bbox is None or b.bbox is None:
            return 0.0

        ax1, ay1, aw, ah = a.bbox
        bx1, by1, bw, bh = b.bbox
        ax2, ay2 = ax1 + aw, ay1 + ah
        bx2, by2 = bx1 + bw, by1 + bh

        # 交集
        ix1 = max(ax1, bx1)
        iy1 = max(ay1, by1)
        ix2 = min(ax2, bx2)
        iy2 = min(ay2, by2)

        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0

        inter_area = (ix2 - ix1) * (iy2 - iy1)
        a_area = aw * ah
        b_area = bw * bh
        union_area = a_area + b_area - inter_area

        if union_area <= 0:
            return 0.0

        return inter_area / union_area

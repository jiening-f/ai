"""
模板匹配服务

基于 OpenCV cv2.matchTemplate 实现，支持：
- 多匹配方法（默认 TM_CCOEFF_NORMED）
- 多尺度匹配（缩放 0.8x~1.2x，步长 0.05）
- 多目标匹配（threshold 以上所有匹配点）
- 灰度匹配加速
"""

import cv2
import numpy as np
from dataclasses import dataclass, field


@dataclass
class MatchResult:
    """单个匹配结果"""
    position: tuple[int, int, int, int]  # (x, y, width, height)
    confidence: float
    method: str = ""


class TemplateMatcher:
    """
    模板匹配器

    用法:
        matcher = TemplateMatcher()
        matches = matcher.match(screenshot, "template.png", threshold=0.8)
    """

    # 支持的匹配方法
    METHODS = {
        "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
        "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
        "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
    }

    def __init__(self, default_method: str = "TM_CCOEFF_NORMED"):
        self.default_method = default_method
        self._template_cache: dict[str, np.ndarray] = {}

    def match(
        self,
        screenshot: np.ndarray,
        template_path: str,
        threshold: float = 0.8,
        method: str = "",
        multi: bool = False,
        region: dict | None = None,
        multi_scale: bool = True,
    ) -> list[MatchResult]:
        """
        在截图中查找模板

        Args:
            screenshot: 截图 numpy array (BGR 或灰度)
            template_path: 模板图片文件路径
            threshold: 匹配置信度阈值 (0~1)
            method: 匹配方法名称，空=默认
            multi: True 返回所有超过阈值的匹配
            region: 搜索区域 {"x", "y", "w", "h"}，None=全图
            multi_scale: 是否启用多尺度匹配

        Returns:
            匹配结果列表，按置信度降序排列
        """
        method = method or self.default_method
        cv_method = self.METHODS.get(method, cv2.TM_CCOEFF_NORMED)

        # 读取模板（带缓存）
        template = self._load_template(template_path)
        if template is None:
            return []

        # 区域截取
        search_img = screenshot
        offset_x, offset_y = 0, 0
        if region and isinstance(region, dict):
            x, y, w, h = region.get("x", 0), region.get("y", 0), region.get("w", 0), region.get("h", 0)
            if w > 0 and h > 0:
                search_img = screenshot[y:y + h, x:x + w]
                offset_x, offset_y = x, y

        # 转为灰度
        if len(search_img.shape) == 3:
            search_gray = cv2.cvtColor(search_img, cv2.COLOR_BGR2GRAY)
        else:
            search_gray = search_img

        if len(template.shape) == 3:
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        else:
            template_gray = template

        matches: list[MatchResult] = []

        if multi_scale:
            # 多尺度匹配
            scales = np.arange(0.8, 1.25, 0.05)
            for scale in scales:
                scaled_w = int(template_gray.shape[1] * scale)
                scaled_h = int(template_gray.shape[0] * scale)
                if scaled_w < 5 or scaled_h < 5:
                    continue
                if scaled_w > search_gray.shape[1] or scaled_h > search_gray.shape[0]:
                    continue

                scaled_template = cv2.resize(template_gray, (scaled_w, scaled_h))
                ms = self._match_one(search_gray, scaled_template, cv_method, threshold, multi, method)
                for m in ms:
                    matches.append(MatchResult(
                        position=(
                            m.position[0] + offset_x,
                            m.position[1] + offset_y,
                            m.position[2],
                            m.position[3],
                        ),
                        confidence=m.confidence,
                        method=method,
                    ))
        else:
            ms = self._match_one(search_gray, template_gray, cv_method, threshold, multi, method)
            for m in ms:
                matches.append(MatchResult(
                    position=(
                        m.position[0] + offset_x,
                        m.position[1] + offset_y,
                        m.position[2],
                        m.position[3],
                    ),
                    confidence=m.confidence,
                    method=method,
                ))

        # 去重 + 按置信度降序
        matches = self._deduplicate(matches)
        matches.sort(key=lambda m: m.confidence, reverse=True)
        return matches

    def _match_one(
        self,
        search: np.ndarray,
        template: np.ndarray,
        method: int,
        threshold: float,
        multi: bool,
        method_name: str,
    ) -> list[MatchResult]:
        """单尺度匹配"""
        if template.shape[0] > search.shape[0] or template.shape[1] > search.shape[1]:
            return []

        result = cv2.matchTemplate(search, template, method)
        th, tw = template.shape[1], template.shape[0]
        matches = []

        if multi:
            # 多目标匹配：找到所有超过阈值的位置
            if method in (cv2.TM_SQDIFF_NORMED, cv2.TM_SQDIFF):
                locs = np.where(result <= (1.0 - threshold))
            else:
                locs = np.where(result >= threshold)

            for pt in zip(*locs[::-1]):
                confidence = float(result[pt[1], pt[0]])
                if method in (cv2.TM_SQDIFF_NORMED, cv2.TM_SQDIFF):
                    confidence = 1.0 - confidence
                matches.append(MatchResult(
                    position=(pt[0], pt[1], tw, th),
                    confidence=confidence,
                    method=method_name,
                ))
        else:
            # 最佳匹配
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            if method in (cv2.TM_SQDIFF_NORMED, cv2.TM_SQDIFF):
                confidence = 1.0 - min_val
                loc = min_loc
            else:
                confidence = float(max_val)
                loc = max_loc

            if confidence >= threshold:
                matches.append(MatchResult(
                    position=(loc[0], loc[1], tw, th),
                    confidence=confidence,
                    method=method_name,
                ))

        return matches

    @staticmethod
    def _deduplicate(matches: list[MatchResult], distance: int = 10) -> list[MatchResult]:
        """去除距离过近的重复匹配"""
        if len(matches) <= 1:
            return matches
        matches.sort(key=lambda m: m.confidence, reverse=True)
        kept = []
        for m in matches:
            is_dup = False
            for k in kept:
                if (abs(m.position[0] - k.position[0]) < distance
                        and abs(m.position[1] - k.position[1]) < distance):
                    is_dup = True
                    break
            if not is_dup:
                kept.append(m)
        return kept

    def _load_template(self, path: str) -> np.ndarray | None:
        """加载模板图片（带缓存）"""
        if path in self._template_cache:
            return self._template_cache[path]
        try:
            img = cv2.imread(path)
            if img is not None:
                self._template_cache[path] = img
            return img
        except Exception:
            return None

    def to_dict_list(self, matches: list[MatchResult]) -> list[dict]:
        """将匹配结果转为字典列表"""
        return [
            {
                "position": {"x": m.position[0], "y": m.position[1], "w": m.position[2], "h": m.position[3]},
                "confidence": round(m.confidence, 4),
                "method": m.method,
            }
            for m in matches
        ]

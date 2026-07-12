"""
循环节点引擎 — 关卡地图特征检测与决策流程

核心模型：
  一个关卡 = 多张随机地图 → 每张地图 4 个特征节点 → 逐个检测
    全部匹配 → 继续执行下一张地图
    任意不匹配 → 重新进入本关（重开）
"""

from dataclasses import dataclass, field
from enum import Enum
import time


# ══ 枚举 ══════════════════════════════════════

class NodeType(Enum):
    MAP_SELECT = "map_select"       # 地图选择
    FEATURE_DETECT = "feature"      # 特征检测
    DECISION = "decision"           # 判定


class DetectType(Enum):
    TEXT = "text"                   # OCR 文字识别
    IMAGE = "image"                 # 模板匹配
    KEY = "key"                     # 按键检测（暂未实现）


class Decision(Enum):
    CONTINUE = "continue"           # 继续
    RESTART = "restart"             # 重开


# ══ 数据模型 ══════════════════════════════════

@dataclass
class FeatureNode:
    """单个特征节点"""
    id: str
    detect_type: DetectType                # text / image / key
    detect_value: str                      # 检测目标值
    on_match: Decision                     # 匹配时的决策
    on_mismatch: Decision                  # 不匹配时的决策
    map_id: str = ""                       # 所属地图 id
    enabled: bool = True


@dataclass
class MapConfig:
    """地图配置（每张地图 4 个特征节点）"""
    id: str
    name: str
    features: list = field(default_factory=list)
    enabled: bool = True


@dataclass
class NodeFlow:
    """完整节点流程"""
    maps: list = field(default_factory=list)
    loop_enabled: bool = True              # 全部通过后是否循环
    max_loops: int = 0                     # 0=无限循环


# ══ 引擎 ══════════════════════════════════════

class NodeEngine:
    """循环节点引擎：驱动地图→特征→判定流程"""

    def __init__(self, vision_engine=None, input_engine=None):
        self.running = False
        self._vision = vision_engine
        self._input = input_engine
        self._on_log = None
        self._current_map = None
        self._current_feature = None

    # ── 主循环 ──

    def run(self, flow: NodeFlow, on_log=None):
        """
        执行节点流程。
        参数：
          flow:   NodeFlow 配置对象
          on_log: 可选回调 func(msg: str)，用于实时日志输出
        """
        self.running = True
        self._on_log = on_log
        loop_count = 0

        while self.running:
            loop_count += 1
            if flow.max_loops > 0 and loop_count > flow.max_loops:
                self._log(f"⏹ 已达最大循环次数 {flow.max_loops}，退出")
                break
            self._log(f"--- 第 {loop_count} 轮 ---")

            restart_triggered = False

            for map_cfg in flow.maps:
                if not map_cfg.enabled:
                    continue
                self._current_map = map_cfg
                self._log(f"检测地图: {map_cfg.name}")

                all_match = True
                for node in map_cfg.features:
                    if not node.enabled:
                        continue
                    self._current_feature = node
                    result = self._detect_feature(node)
                    decision = node.on_match if result else node.on_mismatch
                    status = "✅" if result else "❌"
                    self._log(
                        f"  {status} 特征: [{node.detect_type.value}] "
                        f"{node.detect_value} → {decision.value}"
                    )
                    if decision == Decision.RESTART:
                        all_match = False
                        break

                if not all_match:
                    self._log(f"⏹ 地图 {map_cfg.name} 不匹配，重开本关")
                    restart_triggered = True
                    break

            if restart_triggered:
                continue  # 重开 → 重新从第一张地图开始

            # 所有地图都通过了（for-else）
            if not flow.loop_enabled:
                self._log("✅ 全图通过，循环已关闭，结束")
                break
            self._log("✅ 全图通过，进入下一轮")

        self.running = False
        self._log("--- 流程结束 ---")

    def stop(self):
        """停止当前执行的流程"""
        self.running = False

    # ── 特征检测 ──

    def _detect_feature(self, node: FeatureNode) -> bool:
        """
        检测一个特征节点是否匹配。
        根据 detect_type 调用对应的视觉/输入模块。
        """
        if node.detect_type == DetectType.TEXT:
            from engine.vision import OCR
            pos = OCR.find_text(node.detect_value, timeout=2)
            return pos is not None

        elif node.detect_type == DetectType.IMAGE:
            from engine.vision import TemplateMatcher
            pos = TemplateMatcher.find(node.detect_value)
            return pos is not None

        elif node.detect_type == DetectType.KEY:
            # 按键检测 — 暂不实现，默认通过
            return True

        return False

    # ── 日志 ──

    def _log(self, msg: str):
        if self._on_log:
            self._on_log(msg)

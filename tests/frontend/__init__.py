"""前端组件基础测试 — 使用 vitest + @testing-library/react

注意：这些测试在 Python 的 tests/frontend/ 目录下，但实际运行需要在
frontend/ 目录下用 `npm test` 执行。这里同时提供一份纯逻辑测试
（不依赖 DOM）用于 CI 环境。

前端节点类型汇总（来自 FlowEditor.tsx）：
  流程控制: start, end, wait, condition, loop
  键盘操作: key_press, key_combo, key_hold
  鼠标操作: mouse_click, mouse_dblclick, mouse_drag, mouse_scroll
  视觉识别: ocr_recognize, template_match, screenshot
  数据操作: variable_set, text_output
  共计 17 种 UI 节点类型
"""

---
description: 前端/体验设计 (UX/UI) 专项审查工作流
---

# 🎨 UX/UI 体验专项审查工作流

当你对我发出 `/ux-review` 指令时，我将化身为 **高级产品经理与 UX 设计专家**，针对 `Finance Alchemy` 进行 8 个维度的深度审计：

## 🔍 审计指标 (The 8 Dimensions)

1.  **理解程度 (Understanding)**: 用户是否能一眼看出这是一个“AI 驱动的量化分析系统”？术语（如 DDD, CrewAI）是否解释清晰？
2.  **操作路径 (User Flow)**: 从“输入关键词”到“看到报告”的点击次数是否最简？是否存在无效等待？
3.  **输出清晰度 (Output Clarity)**: Gradio 界面中的表格、图表、Markdown 渲染是否美观易读？
4.  **信息负荷 (Cognitive Load)**: 页面信息是否过杂？核心操作（“分析”）是否突出？
5.  **错误提示 (Error Handling)**: 当 API Key 缺失、代码无效、网络超时时，系统是否给出了“人话”提示而非 Python Traceback？
6.  **用户引导 (Onboarding)**: 第一次打开界面的用户知道该怎么做吗？是否有 Placeholder 或 Tooltip 引导？
7.  **默认值 (Defaults)**: 常用选项（如分析深度、K线限制）是否有合理的默认预设？
8.  **解释性 (Explainability)**: 为什么这个 Agent 建议“买入”？分析过程是否透明？

## 🛠️ 执行流程

1.  **代码扫描**: 审查 `src/interface/gui/main.py` 和 `report_formatter.py`。
2.  **视觉评估**: 结合代码逻辑模拟 UI 展示效果。
3.  **输出报告**:
    *   **❌ 问题点**: 列出违反以上指标的具体代码/UI 设计。
    *   **✅ 改进方案**: 提供具体的代码重构或 UI 文本修改建议。
4.  **自动修复**: 如果用户授权，直接应用修改。

## 🎯 目标
将系统从一个“开发者工具”提升为“金融极客产品”。

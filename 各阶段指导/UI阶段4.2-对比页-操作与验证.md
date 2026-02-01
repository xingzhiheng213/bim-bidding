# UI 阶段 4.2 对比页 — 操作与验证指南

本文档面向执行与验收，按「阶段要达成什么 → 需要准备什么 → 如何验证」说明 **UI 设计计划** 阶段 4.2（对比页）的完整流程。阶段 4.2 对对比页做布局整理（Tabs/分区不拥挤）、Diff 展示与设计系统统一、从任务加载区排版与加载/错误态反馈，使对比页与设置页等风格一致且可维护。

---

## 一、阶段 4.2 要达成什么

- **布局**：两段文本输入 + 「对比」按钮 + diff 结果展示区；「从任务加载」与手动输入以 **Tabs** 或分区并存，不拥挤；统一内容区宽度（如 maxWidth: 720）。
- **Diff 展示**：删除标红、新增标绿与设计系统语义色一致（colorError/colorSuccess 及浅色背景）；字体、行距、边距使用 designTokens。
- **从任务加载**：任务选择、类型（框架/章节）、章节号等控件排版清晰（Form 或 Space + 明确标签）；加载中与错误态有明确反馈（Spin、Alert type="error"）。
- **交付物**：对比页分区清晰、风格与设置页统一；diff 样式可维护且符合设计系统。

---

## 二、你需要提前准备的东西

| 项目 | 说明 | 如何确认 |
|------|------|----------|
| 阶段 0、1、4.1 已完成 | design token、主题；侧栏布局；设置页分区与对齐 | 见各 UI阶段0.x、1.x、4.1/4.1.1 指导 |
| 对比接口与任务列表 | POST /api/compare；GET 任务框架/章节 diff；GET /api/tasks | 能打开对比页并选择任务加载或手动输入对比 |

本阶段修改前端：`frontend/src/components/DiffView.tsx`（designTokens 语义色与 typography）；`frontend/src/pages/ComparePage.tsx`（外层容器、Tabs、designTokens、Alert、Spin、Form 排版）。

---

## 三、阶段 4.2 交付物说明

完成 4.2 后，应满足以下内容：

### 1. 布局与分区（ComparePage.tsx）

- **统一内容区宽度**：最外层包一层容器 `style={{ maxWidth: 720, width: '100%' }}`，主标题与各区块左右边界一致。
- **Tabs**：使用 Ant Design **Tabs**，Tab1「从任务加载」、Tab2「两段文本对比」，用户一次只操作一种方式，页面不拥挤。若采用分区（Card）而非 Tabs，则两个区块用 Card 包裹、间距使用 spacingTokens。

### 2. Diff 展示与设计系统统一（DiffView.tsx + ComparePage.tsx）

- **DiffView 组件**：
  - 删除（del）：背景色使用 `colorError` 的浅色（如 `${colorError}20`），文字色 `colorError`，可选 `textDecoration: 'line-through'`；字体、行高使用 typographyTokens。
  - 新增（add）：背景色使用 `colorSuccess` 的浅色（如 `${colorSuccess}20`），文字色 `colorSuccess`；字体、行高使用 typographyTokens。
  - 无差异提示：使用 `colorTextTertiary` 或 `colorTextQuaternary`，不写死 `#888`。
- **ComparePage 中的 diff 结果区**：边框、背景、圆角使用 designTokens（colorBorder、colorBgLayout、radiusTokens.borderRadius 等）；结果区标题使用 Typography Text/Title，字号与设计系统一致。

### 3. 对比页整体样式统一（ComparePage.tsx）

- **标题与间距**：主标题「文本对比」与区块标题的 marginBottom 等使用 `designTokens.marginLG`、`designTokens.margin`；所有 margin/padding/gap 使用 spacingTokens。
- **错误态**：接口失败时使用 Ant Design **Alert** `type="error"` 或 **Text** `type="danger"`，与设置页错误展示一致；不再使用内联 `color: '#cf1322'`。
- **加载态**：请求进行中按钮使用 `loading`；「从任务加载」在尚无结果时可显示 **Spin**。

### 4. 从任务加载区（ComparePage.tsx）

- **控件排版**：任务下拉、对比类型（框架/章节）、章节号、「加载对比」按钮采用 **Form** 水平布局（labelCol/wrapperCol）或 **Space** + 明确 Label，使标签与控件对齐。
- **加载中**：按钮 `loading`；可选在加载中且无结果时显示 Spin。
- **错误**：使用 **Alert** type="error" 展示 `errorTaskDiff`。

### 5. 「从任务加载」结果区与「再次对比」

- 保持现有功能：加载后展示「修改前/修改后」可折叠原文、DiffView、可编辑「修改后」再次对比。
- 样式统一：Collapse、TextArea、Button 及「修改前/修改后」的 pre 容器背景/边框/圆角均使用 designTokens（colorBgLayout、colorBorder、borderRadiusSM 等）。

---

## 四、如何验证阶段 4.2

### 1. 验证「布局与 Tabs」

1. 启动前端与后端（见 [开发前-服务启动顺序.md](开发前-服务启动顺序.md)）。
2. 打开对比页（如 `/compare`），应看到：主标题「文本对比」与内容区有统一最大宽度（如 720px）；**Tabs** 下有两个 Tab：「从任务加载」「两段文本对比」，切换后内容不拥挤。

### 2. 验证「Diff 展示与设计系统」

- 在「两段文本对比」中输入两段有差异的文本并点击「对比」：删除部分应为红系背景/文字（与 colorError 一致），新增部分为绿系（与 colorSuccess 一致）；字体、行距与设计系统一致。
- 打开 `DiffView.tsx`：无硬编码 `#ffcccc`、`#ccffcc`、`#888`，均使用 designTokens。

### 3. 验证「从任务加载」

- 选择「从任务加载」Tab：任务、对比类型、章节号（当类型为章节时）、「加载对比」按钮排版清晰，标签与控件对齐。
- 选择任务并点击「加载对比」：加载中按钮有 loading 态；若接口失败，错误以 **Alert** 形式展示。
- 加载成功后：折叠区「修改前/修改后」、Diff 结果区、可编辑「修改后」再次对比的样式使用 token（背景、边框、圆角与设置页风格一致）。

### 4. 验收标准汇总

| 项 | 标准 |
|----|------|
| 布局 | 对比页有统一内容宽度；「从任务加载」与「两段文本对比」以 Tabs（或分区）并存且不拥挤 |
| Diff 展示 | 删除标红、新增标绿与 designTokens 语义色一致；字体、行距、边距使用 token |
| 从任务加载 | 任务/类型/章节号等控件排版清晰，加载中与错误态有明确反馈（Spin、Alert） |
| 风格统一 | 设置页与对比页分区清晰、风格统一；diff 样式可维护且符合设计系统 |

---

## 五、与 4.1、4.1.1、阶段 5 的衔接

- **阶段 4.1 / 4.1.1**：对比页与设置页共用 designTokens、统一内容区宽度思路（设置页 640/720，对比页 720）；错误态、加载态与设置页一致（Alert、Spin）。
- **阶段 5**：4.2 完成后可进入阶段 5（细节与打磨）；加载/错误/空态统一、响应式与全站走查将覆盖对比页在内的所有页面。

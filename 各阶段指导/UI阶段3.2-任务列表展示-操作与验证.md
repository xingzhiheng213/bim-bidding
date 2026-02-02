# UI 阶段 3.2 任务列表展示 — 操作与验证指南

本文档面向执行与验收，按「阶段要达成什么 → 需要准备什么 → 如何验证」说明 **UI 设计计划** 阶段 3.2（任务列表展示）的完整流程。阶段 3.2 在首页任务列表中用设计系统状态标签展示状态、弱化任务 ID、保持进入与删除交互及二次确认，并统一使用 stepStatus 与 design token。

---

## 一、阶段 3.2 要达成什么

- **列表信息**：至少包含状态、创建时间、操作（进入、删除）；「任务 ID」弱化为次要信息（保留在列表中，用 secondary 样式展示）。
- **状态展示**：用设计系统约定的状态标签/色块（stepStatusDisplay 的 tagColor 与 getStepStatusLabel）展示 pending / running / completed / failed 等，便于扫一眼识别。
- **行点击或「进入」链接**：保持可进入任务详情；删除前二次确认保留。
- **交付物**：任务列表信息与状态展示符合设计系统；进入与删除交互不变且清晰。

---

## 二、你需要提前准备的东西

| 项目 | 说明 | 如何确认 |
|------|------|----------|
| 阶段 0、3.1 已完成 | stepStatus 约定（stepStatus.ts）；首页结构（主操作与列表区块） | 见 [UI阶段0.3-步骤状态与按钮约定-操作与验证.md](UI阶段0.3-步骤状态与按钮约定-操作与验证.md)、[UI阶段3.1-首页结构-操作与验证.md](UI阶段3.1-首页结构-操作与验证.md) |
| 首页与接口 | GET /api/tasks 返回任务列表（含 status、created_at、id）；创建、删除、进入详情已可用 | 能打开首页并看到任务列表 |

本阶段仅修改前端：`frontend/src/pages/HomePage.tsx`（引入 stepStatus 与 Tag、状态列 Tag 渲染、任务 ID 弱化、列顺序）。

---

## 三、阶段 3.2 交付物说明

完成 3.2 后，应满足以下内容：

### 1. 状态列改用设计系统标签（`HomePage.tsx`）

- **引入**：`import { getStepStatusLabel, stepStatusDisplay, type StepStatus } from '../theme/stepStatus'`，以及 Ant Design 的 `Tag`。
- **状态列**：状态列使用 `render`，根据 `record.status` 映射为 stepStatus：若为 pending / running / waiting_user / completed / failed，则用 `stepStatusDisplay[status].tagColor` 与 `getStepStatusLabel(status)` 渲染 `<Tag color={...}>{...}</Tag>`；其它值可用 `Tag color="default"` 显示原值或「待执行」。

### 2. 任务 ID 弱化

- **任务 ID 列**：保留在列表中，使用 `Typography.Text type="secondary"` 渲染 `record.id`，列宽可略减（如 80），视觉上次于「状态」「创建时间」。

### 3. 列顺序与操作列

- **列顺序**：**状态** → **创建时间** → **任务 ID**（次要）→ **操作**，便于先扫状态与时间。
- **操作列**：保持「进入」Link + Popconfirm「删除」；行点击跳转详情（onRow）；删除前二次确认保留。Link 与按钮间距可使用 `designTokens.marginXS`。

---

## 四、如何验证阶段 3.2

### 1. 验证「状态以 Tag 展示」

1. 启动前端与后端（见 [开发前-服务启动顺序.md](开发前-服务启动顺序.md)）。
2. 打开首页，任务列表中「状态」列应为 **Tag** 展示，颜色与文案与 stepStatus 一致（如待执行=灰、进行中=蓝、已完成=绿、失败=红、待确认=橙）。若后端当前仅返回 pending，则统一为「待执行」标签。

### 2. 验证「任务 ID 弱化」

- 「任务 ID」列仍存在，但为灰色/次要样式（`Text type="secondary"`），视觉上次于「状态」「创建时间」。

### 3. 验证「进入与删除」

- 点击行或「进入」链接可进入任务详情；点击「删除」弹出「确定删除该任务？」二次确认，确认后删除并刷新列表。

### 4. 验收标准汇总

| 项 | 标准 |
|----|------|
| 状态展示 | 状态列使用 Tag，颜色/文案与 stepStatus 一致 |
| 任务 ID | 任务 ID 列为次要样式（secondary），列顺序在创建时间之后 |
| 列顺序 | 状态 → 创建时间 → 任务 ID → 操作 |
| 进入与删除 | 行点击/「进入」进入详情；删除前二次确认保留 |

---

## 五、与 3.1、3.3 的衔接

- **阶段 3.1**：3.2 在 3.1 的首页结构与任务列表区块基础上，仅改表格列定义与状态展示，不改变主操作与列表区块布局。
- **阶段 3.3**：3.2 不修改 Table 的 `locale.emptyText` 或空态样式；3.3 将增强空态（图标/插画、引导文案、主按钮或入口）。

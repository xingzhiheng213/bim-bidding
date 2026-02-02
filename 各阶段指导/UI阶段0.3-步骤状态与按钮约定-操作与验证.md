# UI 阶段 0.3 步骤状态与按钮约定 — 操作与验证指南

本文档面向执行与验收，按「阶段要达成什么 → 需要准备什么 → 如何验证」说明 **UI 设计计划** 阶段 0.3（步骤状态与按钮约定）的完整流程。阶段 0.3 以**约定与文档**为主，在设计系统文档中固定五态步骤的展示形式与主/次按钮适用场景，便于阶段 2 任务详情页步骤条与分步卡片实现；不要求在本阶段改任务详情页的步骤条或按钮实现。

---

## 一、阶段 0.3 要达成什么

- **步骤状态约定**：为 pending / running / waiting_user / completed / failed 约定展示形式（标签色/语义色、图标可选、简短文案），并在设计系统文档中固定；与 Ant Design Steps 的映射（wait / process / finish / error）写明，语义色与 design token 一致。
- **主按钮/次按钮约定**：主流程操作用主按钮（Primary），次要操作用次按钮（Default）或链接（Link），在设计系统文档中固定适用场景，风格与 token 一致。
- **可选**：导出步骤状态展示配置（如 `theme/stepStatus.ts`），供阶段 2 直接引用。
- **交付物**：设计系统文档中新增「步骤状态约定」与「主按钮/次按钮约定」；阶段 2 实现步骤条/分步卡片时可据此实现。

---

## 二、你需要提前准备的东西

| 项目 | 说明 | 如何确认 |
|------|------|----------|
| 阶段 0.1、0.2 已完成 | 已有 design token、ConfigProvider 主题接入 | 见 [UI阶段0.1-设计token定义-操作与验证.md](UI阶段0.1-设计token定义-操作与验证.md)、[UI阶段0.2-Ant Design主题接入-操作与验证.md](UI阶段0.2-Ant Design主题接入-操作与验证.md) |
| 前端项目 | 已有 `frontend/` 目录，`theme/` 下有 tokens、config、README | 能正常 `npm run dev` |

本阶段不依赖后端服务，仅修改或新增 `theme/` 下文档与可选配置。

---

## 三、阶段 0.3 交付物说明

完成 0.3 后，应存在以下内容：

### 1. `frontend/src/theme/README.md`

- **「5. 步骤状态约定」**：表格列出五态（pending / running / waiting_user / completed / failed）的标签色/语义色、图标（可选）、简短文案、Ant Steps 映射；语义色与 tokens 一致。
- **「6. 主按钮/次按钮约定」**：主按钮用于创建任务、开始解析/分析/框架/按章生成、接受并继续、重新生成框架、下载 Word 等；次按钮或链接用于取消、添加要点、重试、重新生成本章等；同一区块内主操作仅一个主按钮。
- **「7. 与 0.2、0.3 的衔接」**：0.3 已落实，指向「步骤状态约定」与「主按钮/次按钮约定」。

### 2. `frontend/src/theme/stepStatus.ts`（可选）

- 导出 `StepStatus`、`StepsStatus` 类型与 `StepStatusDisplay` 接口。
- 导出 `stepStatusDisplay`：每状态对应 tagColor、label、stepsStatus、iconName（可选）。
- 导出 `getStepsStatus(stepStatus)`、`getStepStatusLabel(stepStatus)`，供阶段 2 步骤条与 Tag 引用。

---

## 四、如何验证阶段 0.3

### 1. 验证「文档完整」

- 打开 `frontend/src/theme/README.md`：
  - **步骤状态约定**：五态表格完整，含标签色、文案、Ant Steps 映射。
  - **主按钮/次按钮约定**：主按钮与次按钮/链接的适用场景已写明。
  - **0.3 衔接**：第 7 节中 0.3 已标记为已落实，并指向上述两节。

### 2. 验证「可选配置可引用」（若有 stepStatus.ts）

- 前端执行 `npm run dev`，确认无构建/类型报错。
- 可选：在任意组件中 `import { getStepStatusLabel, stepStatusDisplay } from '../theme/stepStatus'`，使用 `getStepStatusLabel('waiting_user')` 等，确认返回「待确认」且无报错。

### 3. 验收标准汇总

| 项 | 标准 |
|----|------|
| 步骤状态约定 | README 中五态展示形式（标签色、文案、Steps 映射）已固定，与 design token 语义色一致 |
| 主/次按钮约定 | README 中主按钮与次按钮/链接的适用场景已固定 |
| 0.3 衔接说明 | README 第 7 节 0.3 已落实，并指向步骤状态与按钮约定 |
| stepStatus.ts（可选） | 若存在：可正常 import，`getStepStatusLabel` 等与文档一致 |

---

## 五、与 0.1、0.2 和阶段 2 的衔接

- **0.1/0.2**：步骤状态使用的颜色与按钮风格均来自已有 token（colorPrimary、colorSuccess、colorError 等），不新增 token。
- **阶段 2**：任务详情页步骤条（Ant Design Steps）与分步卡片内的状态标签、操作按钮，按本约定实现；若有 `stepStatus.ts`，Steps 与 Tag 可引用其配置与辅助函数。参见 [UI设计计划-分阶段.md](../UI设计计划-分阶段.md) 阶段 2。

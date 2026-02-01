# UI 阶段 2.1 步骤条或时间线 — 操作与验证指南

本文档面向执行与验收，按「阶段要达成什么 → 需要准备什么 → 如何验证」说明 **UI 设计计划** 阶段 2.1（步骤条或时间线）的完整流程。阶段 2.1 在任务详情页顶部增加 **Ant Design Steps** 步骤条，展示「上传 → 解析 → 分析 → 参数 → 框架 → 按章生成 → 导出」七步，状态与后端同步；可选点击步骤滚动到对应内容区块。

---

## 一、阶段 2.1 要达成什么

- **步骤条位置与顺序**：在任务详情页顶部（任务 ID/状态/创建时间下方）增加步骤条，顺序为：上传 → 解析 → 分析 → 参数 → 框架 → 按章生成 → 导出。
- **状态与后端一致**：pending / running / waiting_user / completed / failed 映射到 Ant Design Steps 的 wait / process / finish / error；`waiting_user` 用「待确认」文案与 process 状态区分；`running` 可用 Loading 图标。
- **当前步高亮**：步骤条 `current` 指向当前进行中/待确认步骤，或第一个未完成步骤；全部完成时指向最后一步。
- **点击滚动（可选）**：点击某一步可平滑滚动到该步对应内容区块（通过 `id="step-{step_key}"` 与 `onChange` 调用 `scrollIntoView`）。
- **样式**：步骤条与上下间距使用 design token（如 `designTokens.marginLG`），符合设计系统。
- **交付物**：任务详情页具备步骤条；状态与后端同步；样式符合设计系统。

---

## 二、你需要提前准备的东西

| 项目 | 说明 | 如何确认 |
|------|------|----------|
| 阶段 0 已完成 | 已有 design token、ConfigProvider 主题、步骤状态与按钮约定（含 stepStatus.ts） | 见 [UI阶段0.1-设计token定义-操作与验证.md](UI阶段0.1-设计token定义-操作与验证.md)、[UI阶段0.2-Ant Design主题接入-操作与验证.md](UI阶段0.2-Ant Design主题接入-操作与验证.md)、[UI阶段0.3-步骤状态与按钮约定-操作与验证.md](UI阶段0.3-步骤状态与按钮约定-操作与验证.md) |
| 阶段 1 已完成 | 全站侧栏 + 主内容区布局，任务详情页在 Content 内正常显示 | 见 [UI阶段1.1-公共布局组件-操作与验证.md](UI阶段1.1-公共布局组件-操作与验证.md)、[UI阶段1.2-侧栏导航-操作与验证.md](UI阶段1.2-侧栏导航-操作与验证.md) |
| 任务详情页与接口 | `GET /api/tasks/{id}` 返回任务及 steps（step_key、status 等）；前端 TaskDetailPage 已展示各步骤内容 | 能进入 `/tasks/:id`，看到上传/解析/分析等区块；后端步骤可能按需创建（extract、params 在首次执行时创建） |

本阶段仅修改前端：`frontend/src/theme/stepStatus.ts`（可选导出步骤顺序与标题）、`frontend/src/pages/TaskDetailPage.tsx`（步骤条 + 区块 id）。

---

## 三、阶段 2.1 交付物说明

完成 2.1 后，应存在以下内容：

### 1. 步骤顺序与标题（`frontend/src/theme/stepStatus.ts` 或 TaskDetailPage 内）

- **固定顺序**：`TASK_STEP_ORDER` 为 `['upload','extract','analyze','params','framework','chapters','export']`。
- **标题**：`STEP_TITLES` 或等价映射：上传、解析、分析、参数、框架、按章生成、导出。
- 未在 `data.steps` 中出现的 step_key（如尚未创建的 extract/params）在步骤条中视为 pending（wait）。

### 2. 任务详情页步骤条（`frontend/src/pages/TaskDetailPage.tsx`）

- **Steps 组件**：在「任务详情」标题与任务 ID/状态/创建时间下方、各步骤内容区块上方，渲染 `<Steps current={...} items={...} onChange={...} />`。
- **items**：由 `data.steps` 与 `TASK_STEP_ORDER` 计算；每项含 title（STEP_TITLES）、description（getStepStatusLabel）、status（getStepsStatus）；running 时 icon 为 LoadingOutlined。
- **current**：当前进行中/待确认步骤索引，或第一个未完成步骤索引，或最后一步（全部完成时）。
- **onChange**：点击步骤时根据索引得到 step_key，对 `document.getElementById('step-' + step_key)` 执行 `scrollIntoView({ behavior: 'smooth' })`。
- **间距**：Steps 容器的 marginBottom 使用 `designTokens.marginLG`（或 useToken 的 token.marginLG），无硬编码数值。

### 3. 内容区块 id（便于滚动定位）

- 各逻辑步骤区块最外层（或代表该步的容器）增加 `id="step-{step_key}"`：step-upload、step-extract、step-analyze、step-params、step-framework、step-chapters、step-export。
- step-export 可落在「生成完成」+ 下载 Word 的包裹元素上；若某步尚未渲染（如 export 在按章未完成时无下载区），点击该步时 scrollIntoView 可能无效果，属预期。

---

## 四、如何验证阶段 2.1

### 1. 验证「步骤条可见且顺序正确」

1. 启动前端与后端（见 [开发前-服务启动顺序.md](开发前-服务启动顺序.md)）。
2. 打开 http://localhost:5173/ ，创建或进入一个任务，进入任务详情页（如 `/tasks/1`）。
3. 在「任务详情」标题与任务 ID/状态/创建时间下方，应看到 **步骤条**，从左到右顺序为：**上传 → 解析 → 分析 → 参数 → 框架 → 按章生成 → 导出**。
4. 新建任务时，上传为当前步（或待执行）；未创建的 extract/params 显示为待执行（wait）。

### 2. 验证「状态与后端同步」

1. 上传文件并触发解析：解析中时，步骤条「解析」应为进行中（process，可有 Loading 图标）。
2. 解析完成后，「解析」为已完成（finish），「分析」为待执行或可点击「开始分析」；执行分析后「分析」为进行中，依此类推。
3. 框架生成完成后若为等待用户确认：步骤条「框架」应为 process，描述为「待确认」。
4. 某步失败时：该步在步骤条中为 error 状态，描述为「失败」。

### 3. 验证「当前步高亮」

- 有步骤为 running 或 waiting_user 时，步骤条高亮（current）应指向该步。
- 无进行中/待确认时，current 指向第一个未完成步骤；全部完成时指向最后一步（导出）。

### 4. 验证「点击步骤滚动」（若已实现）

1. 在任务详情页向下滚动到页面中部或底部。
2. 点击步骤条中某一步（如「分析」或「框架」），页面应平滑滚动到该步对应内容区块（含 `id="step-analyze"` / `id="step-framework"` 等的区域）。

### 5. 验证「样式符合设计系统」

- 步骤条与下方内容区块的间距为 design token（如 24px / marginLG），无硬编码 `marginBottom: 24` 等；可在代码中确认使用 `designTokens.marginLG` 或主题 token。

### 6. 验收标准汇总

| 项 | 标准 |
|----|------|
| 步骤条位置与顺序 | 任务详情页顶部（元信息下）可见步骤条，顺序：上传 → 解析 → 分析 → 参数 → 框架 → 按章生成 → 导出 |
| 状态映射 | pending→wait、running→process、waiting_user→process+「待确认」、completed→finish、failed→error；running 可有 Loading 图标 |
| 当前步 | current 为进行中/待确认步或第一个未完成步或最后一步 |
| 点击滚动 | 点击某步可滚动到对应区块（id="step-{key}"） |
| 样式 | 间距使用 design token，无硬编码 |

---

## 五、与 2.2、2.3 的衔接

- **阶段 2.2**：2.1 仅增加步骤条与区块 id；2.2 将按步骤分块展示（每步一个卡片/区块、操作按钮、可折叠详情），可复用 `step-{key}` 作为卡片或区块 id，步骤条点击滚动仍有效。完成后参见后续「UI阶段2.2-按步骤分块展示-操作与验证.md」。
- **阶段 2.3**：2.3 在框架 waiting_user 时突出该步骤与对应卡片；2.1 的步骤条已能正确显示「待确认」状态，2.3 可在卡片样式与提示文案上加强。

若你希望从 2.1 细化到「步骤条横向/纵向」「响应式换行」，可在本指南或 UI 设计计划中补充说明。

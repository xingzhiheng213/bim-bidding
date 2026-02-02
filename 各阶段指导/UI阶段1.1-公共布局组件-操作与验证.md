# UI 阶段 1.1 公共布局组件（侧栏 + 主内容区）— 操作与验证指南

本文档面向执行与验收，按「阶段要达成什么 → 需要准备什么 → 如何验证」说明 **UI 设计计划** 阶段 1.1（公共布局组件）的完整流程。阶段 1.1 将全站布局改为**侧栏（Sider）+ 主内容区（Content）**，子页面通过 `Outlet` 在 Content 内渲染；侧栏内放置品牌与导航项（首页、设置、对比）。当前页高亮样式细化归属 1.2。

---

## 一、阶段 1.1 要达成什么

- **布局结构**：`AppLayout` 为 **侧栏（Sider）+ 主内容区（Content）**；左侧固定侧栏，右侧为内层 `Layout` 内仅 `Content`，`Content` 内渲染 `<Outlet />`。
- **侧栏内容**：侧栏顶部为品牌/标题「BIM 标书生成」；其下为主导航「首页」「对比」；「设置」固定在侧栏最底部（与主导航有分隔线，符合常见商业软件习惯）。点击可正确跳转；样式使用 design token（背景、边框、字号、间距）。
- **路由**：首页、设置、对比、任务详情仍作为 `AppLayout` 的子路由，路由结构不变；各页面只渲染内容区，由 AppLayout 的 Content 承载。
- **交付物**：`AppLayout` 组件（侧栏 + 主内容区）+ 路由结构；所有现有页面在统一布局下正常显示。

---

## 二、你需要提前准备的东西

| 项目 | 说明 | 如何确认 |
|------|------|----------|
| 阶段 0 已完成 | 已有 design token、ConfigProvider 主题、步骤状态与按钮约定 | 见 [UI阶段0.1-设计token定义-操作与验证.md](UI阶段0.1-设计token定义-操作与验证.md)、[UI阶段0.2-Ant Design主题接入-操作与验证.md](UI阶段0.2-Ant Design主题接入-操作与验证.md)、[UI阶段0.3-步骤状态与按钮约定-操作与验证.md](UI阶段0.3-步骤状态与按钮约定-操作与验证.md) |
| 前端项目 | 已有 `frontend/`，Vite + React + TypeScript + Ant Design 5，嵌套路由已使用 AppLayout | 能正常 `npm run dev`，访问 `/`、`/settings`、`/compare`、`/tasks/:id` 有页面 |

本阶段不依赖后端服务，仅修改前端 `components/AppLayout.tsx`（若原为顶栏版则改为侧栏版）。

---

## 三、阶段 1.1 交付物说明

完成 1.1 后，应存在以下内容：

### 1. `frontend/src/components/AppLayout.tsx`

- **结构**：最外层 `Layout`（minHeight: 100vh）内为 `Layout.Sider` + 内层 `Layout`；内层 `Layout` 内仅 `Layout.Content`，Content 内为 `<Outlet />`。
- **侧栏（Sider）**：
  - 固定宽度（如 220px），背景与边框使用 `designTokens.colorBgContainer`、`colorBorderSecondary`。
  - 顶部品牌区：标题「BIM 标书生成」，使用 design token 字号/字重/颜色（如 `fontSizeHeading5`、`fontWeightStrong`、`colorText`），上下间距（如 `marginLG`、`marginXS`）。
  - 其下导航：使用 Ant Design `Menu` 的 `mode="inline"`，或等价链接；主导航项为「首页」（`/`）、「对比」（`/compare`）；「设置」（`/settings`）单独在侧栏底部（通过 flex 布局使设置贴底，与主导航有分隔线）；点击跳转（如 `useNavigate` 或 `Link`）；可选根据当前路由设置 `selectedKeys` 以便 1.2 做高亮。
- **主内容区**：Content 的 padding 使用 `designTokens.marginLG`，内部仅 `<Outlet />`。
- **样式**：侧栏与 Content 均使用 design token，无新增硬编码色值或间距。

### 2. 路由结构（`frontend/src/App.tsx`）

- 父路由 `path="/"` 使用 `element={<AppLayout />}`，子路由为 index（HomePage）、settings、compare、tasks/:id；无需因 1.1 改动路由，仅保证布局在 AppLayout 内。

### 3. 各页面

- 首页、设置、对比、任务详情页只渲染内容区（无自带 Layout/Header/Content），由 AppLayout 的 Content 承载；1.1 不要求改页面文件。

---

## 四、如何验证阶段 1.1

### 1. 验证「布局为侧栏 + 主内容区」

1. 进入前端目录并启动开发服务器：
   ```powershell
   cd d:\标书工作流\frontend
   npm run dev
   ```
2. 在浏览器打开 http://localhost:5173/ 。
3. **左侧**应看到固定侧栏：顶部「BIM 标书生成」，其下「首页」「设置」「对比」；**右侧**为主内容区，显示当前页内容（首页为任务列表等）。
4. 点击侧栏「设置」「对比」应跳转到对应页面，主内容区切换为设置页、对比页内容；点击「首页」回到首页。
5. 在地址栏输入 `/tasks/1`（或任意任务 ID）进入任务详情，主内容区显示任务详情；侧栏仍可见，任务详情页无重复的顶栏或侧栏。

### 2. 验证「样式使用 design token」

- 侧栏背景、边框、标题与导航项字号/颜色来自 `designTokens`（可在 `AppLayout.tsx` 中确认无硬编码色值，如无 `#fff`、`#000` 等，仅使用 `designTokens.xxx`）。
- 主内容区 padding 为 `designTokens.marginLG`。

### 3. 验收标准汇总

| 项 | 标准 |
|----|------|
| 布局结构 | AppLayout 为侧栏（Sider）+ 主内容区（Content）；Content 内仅 `<Outlet />` |
| 侧栏内容 | 侧栏内可见「BIM 标书生成」及「首页」「设置」「对比」；点击可正确跳转 |
| 全站一致 | 访问 `/`、`/settings`、`/compare`、`/tasks/:id` 时均为同一套侧栏 + 主内容区，无布局错位、无重复导航 |
| 样式 | 侧栏与 Content 使用 design token，无新增硬编码色值/间距 |

---

## 五、与 0、1.2、1.3 的衔接

- **阶段 0**：直接使用 `designTokens` 做侧栏与 Content 的样式；0.1/0.2/0.3 的 token 与主题已就绪，1.1 不修改 theme 文件。
- **阶段 1.2**：1.1 已提供侧栏与 Menu（或链接），1.2 在侧栏内做「当前页高亮」（如 `selectedKeys` 与设计系统一致的选中样式）、品牌/标题位置可微调；若 1.1 已根据路由设置 `selectedKeys`，1.2 仅需统一高亮样式。1.2 完成后参见 [UI阶段1.2-侧栏导航-操作与验证.md](UI阶段1.2-侧栏导航-操作与验证.md)。
- **阶段 1.3**：在侧栏 + 主内容区布局下，移除或隐藏首页「后端状态」等开发向信息；1.1 不涉及 1.3 内容。1.3 完成后参见 [UI阶段1.3-开发向信息处理-操作与验证.md](UI阶段1.3-开发向信息处理-操作与验证.md)。

若你希望从 1.1 细化到「侧栏宽度/折叠策略」或「响应式断点」，可在本指南或 UI 设计计划中补充说明。

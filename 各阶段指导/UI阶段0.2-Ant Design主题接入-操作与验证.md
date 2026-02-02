# UI 阶段 0.2 Ant Design 主题接入 — 操作与验证指南

本文档面向执行与验收，按「阶段要达成什么 → 需要准备什么 → 如何验证」说明 **UI 设计计划** 阶段 0.2（Ant Design 主题接入）的完整流程。阶段 0.2 将 0.1 的设计 token 通过 ConfigProvider 应用到全局，使主色、圆角等在页面中生效；不要求大规模替换现有内联样式（留待阶段 1）。

---

## 一、阶段 0.2 要达成什么

- **主题配置**：提供供 ConfigProvider 使用的 theme 配置（如 `theme/config.ts` 导出 `themeConfig = { token: designTokens }`），将 0.1 的 `designTokens` 映射到 Ant 的 token。
- **根节点接入**：在应用根节点（如 `main.tsx`）包一层 `ConfigProvider`，传入 `theme={themeConfig}`，确保全站 Ant 组件继承主题。
- **约定**：新写样式优先使用 theme token（如 `useToken()`），避免硬编码色值与间距；0.2 不要求替换现有页面的内联 `style`。
- **交付物**：主题配置文件 + 根节点 ConfigProvider；本地运行可见主色、圆角等已应用。

---

## 二、你需要提前准备的东西

| 项目 | 说明 | 如何确认 |
|------|------|----------|
| 阶段 0.1 已完成 | 已有 `frontend/src/theme/tokens.ts` 与 `designTokens`、`frontend/src/theme/README.md` | 见 [UI阶段0.1-设计token定义-操作与验证.md](UI阶段0.1-设计token定义-操作与验证.md) |
| 前端项目 | 已有 `frontend/` 目录，Vite + React + TypeScript + Ant Design 5 | 能正常 `npm run dev` |
| Node.js 18+ | 本机已安装 Node.js 和 npm | 在终端输入 `node --version`、`npm --version` 能看到版本号 |

本阶段不依赖后端服务，仅修改前端 `theme/` 与根入口。

---

## 三、阶段 0.2 交付物说明

完成 0.2 后，应存在以下内容：

### 1. `frontend/src/theme/config.ts`

- 从 `./tokens` 引入 `designTokens`。
- 导出 `themeConfig = { token: designTokens }`，供 ConfigProvider 使用。
- 后续可在此扩展 `algorithm`（如暗色）、按组件覆盖 token 等。

### 2. `frontend/src/main.tsx`

- 引入 `ConfigProvider`（来自 `antd`）和 `themeConfig`（来自 `./theme/config`）。
- 在 `BrowserRouter` 内侧、`App` 外侧包裹 `<ConfigProvider theme={themeConfig}>`，使全部路由内的 Ant 组件继承主题。

### 3. 设计说明（可选）

- 在 `frontend/src/theme/README.md` 的「与 0.2、0.3 的衔接」中注明主题配置见 `theme/config.ts`，并补充「新写样式约定」：优先使用 theme token，避免硬编码色值与间距。

---

## 四、如何验证阶段 0.2

### 1. 验证「主题已接入且生效」

1. 进入前端目录：
   ```powershell
   cd d:\标书工作流\frontend
   ```
2. 启动开发服务器：
   ```powershell
   npm run dev
   ```
3. 在浏览器打开 http://localhost:5173/ ，进入首页、任务详情、设置等页。
4. **主色**：主按钮（Primary）、链接等应为 `designTokens.colorPrimary`（如 `#1677ff`）；若 0.1 未改主色，视觉与 Ant 默认一致，但需确认来自 token。
5. **圆角**：按钮、输入框、卡片等圆角应为 `designTokens.borderRadius`（6）、`borderRadiusSM`（4）、`borderRadiusLG`（8）等。
6. **可选**：临时修改 `frontend/src/theme/tokens.ts` 中的 `colorPrimary`（如改为 `#00b96b`）或 `borderRadius`（如改为 2），保存后刷新页面，确认主按钮颜色或圆角随之变化，即表示主题来自 token。

### 2. 验收标准汇总

| 项 | 标准 |
|----|------|
| 主题配置 | `frontend/src/theme/config.ts` 存在，导出 `themeConfig`，且 `token` 来自 0.1 的 `designTokens` |
| 根节点 | `main.tsx` 中已用 `ConfigProvider` 包裹 `App`，并传入 `theme={themeConfig}` |
| 视觉生效 | 本地运行前端，主按钮、链接、输入框、卡片等的主色与圆角与设计 token 一致（可经临时改 token 验证） |

---

## 五、与 0.1、0.3 的衔接

- **0.1**：直接使用 `designTokens`，不修改 token 定义；0.2 仅通过 `themeConfig` 注入。
- **0.3**：步骤状态与主/次按钮约定仍基于当前 token；0.2 完成后主色/圆角已全局生效，0.3 仅补充语义约定与文档。参见 [UI设计计划-分阶段.md](../UI设计计划-分阶段.md) 阶段 0.3。

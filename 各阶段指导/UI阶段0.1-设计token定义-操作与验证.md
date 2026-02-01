# UI 阶段 0.1 设计 token 定义 — 操作与验证指南

本文档面向执行与验收，按「阶段要达成什么 → 需要准备什么 → 如何验证」说明 **UI 设计计划** 阶段 0.1（设计 token 定义）的完整流程。阶段 0.1 只做**设计 token 的代码化与文档化**，不接入 ConfigProvider（属 0.2）、不约定步骤状态与按钮（属 0.3）。

---

## 一、阶段 0.1 要达成什么

- **代码**：在 `frontend/src/theme/` 下提供设计 token 定义文件（颜色、字体与层级、间距、圆角），命名与 Ant Design 5 Seed/Map Token 对齐，便于 0.2 直接传入 `ConfigProvider` 的 `theme.token`。
- **文档**：提供设计 token 说明（色板用途、字体层级与 Ant Typography 对应关系、间距尺度、圆角约定），团队可据此实现与后续改版。
- **交付物**：设计 token 已代码化于 `frontend/src/theme/tokens.ts`，已文档化于 `frontend/src/theme/README.md`；聚合导出 `designTokens` 可供 0.2 直接使用。

---

## 二、你需要提前准备的东西

| 项目 | 说明 | 如何确认 |
|------|------|----------|
| 前端项目 | 已有 `frontend/` 目录，Vite + React + TypeScript + Ant Design 5 | 打开 `标书工作流\frontend` 能看到 `src`、`package.json`、`vite.config.ts` 等 |
| Node.js 18+ | 本机已安装 Node.js 和 npm | 在终端输入 `node --version`、`npm --version` 能看到版本号 |

本阶段不依赖后端服务，仅在前端仓库内新增 `theme/` 目录与文件。

---

## 三、阶段 0.1 交付物说明

完成 0.1 后，应存在以下内容：

### 1. `frontend/src/theme/tokens.ts`

- **颜色**：`colorPrimary`、`colorSuccess`、`colorInfo`、`colorWarning`、`colorError`、`colorLink`；中性色 `colorBgLayout`、`colorBgContainer`、`colorBgElevated`、`colorBorder`、`colorBorderSecondary`、`colorText`、`colorTextSecondary`、`colorTextTertiary`、`colorTextQuaternary`。
- **字体与层级**：`fontFamily`、`fontFamilyCode`；`fontSize`、`lineHeight`；`fontSizeHeading1`～`fontSizeHeading5`、`lineHeightHeading1`～`lineHeightHeading5`；`fontSizeLG`、`fontSizeSM`、`lineHeightLG`、`lineHeightSM`；`fontWeightStrong`。
- **间距**：`marginXXS`～`marginXXL`、`paddingXXS`～`paddingXL`（尺度 4/8/12/16/20/24/32/48 px）。
- **圆角**：`borderRadius`、`borderRadiusXS`、`borderRadiusSM`、`borderRadiusLG`、`borderRadiusOuter`。
- **聚合导出**：`designTokens`（合并上述全部）、类型 `DesignTokens`；并导出 `colorTokens`、`typographyTokens`、`spacingTokens`、`radiusTokens` 便于按需引用。

### 2. `frontend/src/theme/README.md`

- 色板：主色与语义色用途；中性色（背景、边框、文字层级）用途。
- 字体与层级：H1–H5、正文、辅助说明的字号/字重/行高；与 Ant Design Typography 组件的对应关系（如 `Title level={1}` 对应 `fontSizeHeading1` 等）。
- 间距：尺度表及使用场景。
- 圆角：各组件类型的圆角约定。
- 与 0.2、0.3 的衔接说明（0.3 将补充步骤状态与主/次按钮约定）。

---

## 四、如何验证阶段 0.1

### 1. 验证「代码存在且可导入」

1. 进入前端目录：
   ```powershell
   cd d:\标书工作流\frontend
   ```
2. 启动开发服务器：
   ```powershell
   npm run dev
   ```
3. 确认**无构建/运行时报错**（说明 `theme/tokens.ts` 被正确识别）。
4. 可选：在任意组件中增加一行 `import { designTokens } from '../theme/tokens'` 并使用（如 `console.log(designTokens.colorPrimary)`），保存后刷新页面，控制台有输出且无报错即表示 token 模块可被正常引用。

**说明**：0.1 未接入 ConfigProvider，页面视觉不会变化；能正常启动且能导入 token 即表示 0.1 代码验收通过。

### 2. 验证「文档完整」

- 打开 `frontend/src/theme/README.md`，确认包含：
  - 色板（主色、语义色、中性色用途）；
  - 字体与层级（含与 Ant Design Typography 的对应关系）；
  - 间距尺度表及使用场景；
  - 圆角约定；
  - 与 0.2、0.3 的衔接说明。

### 3. 验收标准汇总

| 项 | 标准 |
|----|------|
| 代码化 | `frontend/src/theme/tokens.ts` 存在，包含颜色、字体、间距、圆角及聚合导出 `designTokens` |
| 文档化 | `frontend/src/theme/README.md` 存在，色板、字体层级与 Ant 对应、间距、圆角均有说明 |
| 可运行 | 前端 `npm run dev` 能正常启动，无报错；可选：能成功导入 `designTokens` |

---

## 五、与 0.2、0.3 的衔接

- **0.2**：将 `designTokens` 传入 `ConfigProvider` 的 `theme.token`，在根节点包裹应用；主色、圆角等在页面中生效。参见 [UI设计计划-分阶段.md](../UI设计计划-分阶段.md) 阶段 0.2。
- **0.3**：在设计说明中补充步骤状态（pending / running / waiting_user / completed / failed）的展示形式与主/次按钮约定；0.1 仅预留文档位置，不做实现。

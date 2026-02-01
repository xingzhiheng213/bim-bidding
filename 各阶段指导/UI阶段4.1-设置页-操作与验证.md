# UI 阶段 4.1 设置页 — 操作与验证指南

本文档面向执行与验收，按「阶段要达成什么 → 需要准备什么 → 如何验证」说明 **UI 设计计划** 阶段 4.1（设置页）的完整流程。阶段 4.1 用卡片分区「大模型 API」与「模型配置」、明确 API 已配置/未配置状态与子区块布局、统一间距与 design token，使设置页分区与状态清晰、样式符合设计系统。

---

## 一、阶段 4.1 要达成什么

- **分区**：用卡片或区块区分「大模型 API」「模型配置」等；每区标题与间距统一。
- **API 配置**：每个 provider（DeepSeek、智谱等）一个子区块；已配置/未配置有明确状态（如「已配置」+ 脱敏 key）；输入框、Base URL、保存按钮布局清晰。
- **模型配置**：默认模型与各步骤模型选择器排版清晰，与设计系统表单组件一致。
- **交付物**：设置页分区与状态清晰；样式符合设计系统。

---

## 二、你需要提前准备的东西

| 项目 | 说明 | 如何确认 |
|------|------|----------|
| 阶段 0、1 已完成 | design token、主题；侧栏 + 主内容区布局 | 见各 UI阶段0.x、1.x 指导 |
| 设置页与接口 | GET /api/settings/llm、GET /api/settings/models；POST 保存 API Key 与模型配置 | 能打开设置页并保存/读取配置 |

本阶段仅修改前端：`frontend/src/pages/SettingsPage.tsx`（引入 Card、Tag、designTokens；用 Card 分区；API 子区块与 Tag 状态；模型区间距）。

---

## 三、阶段 4.1 交付物说明

完成 4.1 后，应满足以下内容：

### 1. 用 Card 分区「大模型 API」与「模型配置」（`SettingsPage.tsx`）

- **主标题**：「设置」主标题（`Title level={2}`）与第一张 Card 的间距使用 `designTokens.marginLG`。
- **大模型 API 区块**：整块内容包在一张 **Card** 内，`title="大模型 API"`，`style={{ marginBottom: designTokens.marginLG, maxWidth: 560 }}`；卡片内 loading/error 与 provider 列表的间距使用 `designTokens.marginSM`。
- **模型配置区块**：整块内容包在一张 **Card** 内，`title="模型配置"`，`style={{ marginBottom: designTokens.marginLG, maxWidth: 560 }}`；卡片内说明文案、默认模型、各步骤 Select 的间距使用 `designTokens.marginSM`、`margin`。

### 2. API 配置：每个 provider 子区块与已配置/未配置状态

- **子区块**：每个 provider（DeepSeek、智谱）在一个清晰子区块内展示（如 `div` 带 `marginBottom`、`paddingBottom`、可选下边框分隔），区块内顺序：**标题/名称** + **状态**（Tag 已配置/未配置）+ 脱敏 key（已配置时）+ API Key 输入框 + Base URL 输入框 + 保存按钮。
- **已配置/未配置状态**：使用 **Tag** 明确展示——已配置时 `<Tag color="success">已配置</Tag>`，未配置时 `<Tag>未配置</Tag>`；已配置时在 Tag 旁或同行展示脱敏 key（`masked_key`），如 `Text type="secondary"` 显示 `masked_key`。
- **布局**：输入框、Base URL、保存按钮保持现有布局，间距使用 `designTokens`（如 marginXS、marginSM）。

### 3. 模型配置：排版与 design token

- **说明文案**：保留「选择各步骤使用的大模型…」一段，使用 `Text type="secondary"`，下边距 `designTokens.marginSM`。
- **默认模型行**：标签「默认模型」+ Select，间距使用 `designTokens.margin` 或 `marginSM`。
- **各步骤行**：分析/参数/框架/按章生成每行标签 + Select + 可选「当前：xxx」，行间距统一（如 `designTokens.marginSM`），与设计系统表单组件一致。

### 4. 全页 design token

- 所有区块间距、标题边距、内边距使用 `designTokens.*`（如 marginLG、marginSM、marginXS、paddingBottom、colorBorderSecondary），无硬编码 16/12/28/8/32。

---

## 四、如何验证阶段 4.1

### 1. 验证「分区与 Card」

1. 启动前端与后端（见 [开发前-服务启动顺序.md](开发前-服务启动顺序.md)）。
2. 打开设置页（如 `/settings`），应看到：
   - 主标题「设置」；
   - **第一张 Card** 标题「大模型 API」，内容为各 provider 的 API Key、Base URL、保存按钮；
   - **第二张 Card** 标题「模型配置」，内容为说明文案、默认模型、各步骤模型选择器。
3. 两张 Card 之间有明确间距（如 marginLG），每区标题与内容间距统一。

### 2. 验证「API 配置子区块与状态」

- 每个 provider（DeepSeek、智谱）在一个子区块内，区块间有分隔（如下边框或间距）。
- 每个区块内：provider 名称 + **Tag**「已配置」或「未配置」；已配置时显示脱敏 key（如 sk-***xxx）；其下为 API Key 输入框、Base URL 输入框、保存按钮，布局清晰。
- 保存后该 provider 显示「已配置」Tag 及脱敏 key。

### 3. 验证「模型配置排版」

- 「模型配置」Card 内：说明文案 → 默认模型（标签 + Select）→ 各步骤（分析/参数/框架/按章生成）标签 + Select + 「当前：xxx」，行间距统一，与设计系统一致。

### 4. 验收标准汇总

| 项 | 标准 |
|----|------|
| 分区 | 两张 Card（大模型 API、模型配置），标题与间距统一 |
| API 子区块 | 每个 provider 有子区块，已配置/未配置以 Tag 明确，脱敏 key 可见 |
| 模型配置 | 默认模型与各步骤选择器排版清晰，间距使用 design token |
| 设计 token | 全页间距使用 designTokens，无硬编码 16/12/28/8/32 |

---

## 五、与阶段 4.2 的衔接

- **阶段 4.2**：4.1 不修改对比页；4.2 将处理对比页布局与 diff 样式。设置页与对比页分区清晰、风格统一由 4.1（设置页）与 4.2（对比页）共同完成。

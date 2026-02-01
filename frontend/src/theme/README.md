# 设计 Token 说明（阶段 0.1）

本目录为 BIM 标书生成 App 的设计 token 定义，供全局主题与页面改版使用。Token 命名与 Ant Design 5 的 Seed/Map Token 对齐，便于在 0.2 中通过 `ConfigProvider` 的 `theme.token` 注入。

---

## 1. 色板

### 主色与语义色

| Token | 用途 | 默认值 |
|-------|------|--------|
| `colorPrimary` | 主按钮、链接、当前步骤、品牌强调 | `#1677ff` |
| `colorSuccess` | 成功状态（如完成、成功提示） | `#52c41a` |
| `colorInfo` | 进行中/信息（如步骤进行中、提示信息） | `#1677ff` |
| `colorWarning` | 警告状态 | `#faad14` |
| `colorError` | 错误状态（如失败、校验错误） | `#ff4d4f` |
| `colorLink` | 超链接 | `#1677ff` |

### 中性色

**背景层级**

- `colorBgLayout`：页面整体背景（如 Layout 背景）
- `colorBgContainer`：容器背景（如卡片、输入框、按钮默认背景）
- `colorBgElevated`：浮层背景（如 Modal、Dropdown）

**边框**

- `colorBorder`：默认边框（表单、卡片分隔等）
- `colorBorderSecondary`：次要边框/分割线

**文字层级**

- `colorText`：主文字，最深
- `colorTextSecondary`：次要文字（如标签、列表辅助信息）
- `colorTextTertiary`：辅助/说明文字（如表单说明、描述）
- `colorTextQuaternary`：占位/禁用等最弱文字

---

## 2. 字体与层级

### 字体族

- `fontFamily`：正文/界面字体（与 body 一致）
- `fontFamilyCode`：等宽字体，用于代码、`pre`、`kbd`

### 字号与行高

| 用途 | Token（字号） | Token（行高） | 典型场景 |
|------|----------------|----------------|----------|
| 正文 | `fontSize` (14) | `lineHeight` | 默认正文 |
| 大正文 | `fontSizeLG` (16) | `lineHeightLG` | 强调段落 |
| 小正文 | `fontSizeSM` (12) | `lineHeightSM` | 辅助说明、时间戳 |
| 标题 H1 | `fontSizeHeading1` (38) | `lineHeightHeading1` | 页面主标题 |
| 标题 H2 | `fontSizeHeading2` (30) | `lineHeightHeading2` | 区块标题 |
| 标题 H3 | `fontSizeHeading3` (24) | `lineHeightHeading3` | 卡片/区块标题 |
| 标题 H4 | `fontSizeHeading4` (20) | `lineHeightHeading4` | 小节标题 |
| 标题 H5 | `fontSizeHeading5` (16) | `lineHeightHeading5` | 列表/表单区块标题 |

- **字重**：`fontWeightStrong` (600) 用于标题或强调。

### 与 Ant Design Typography 的对应关系

| Ant 组件用法 | 对应 Token |
|--------------|------------|
| `<Title level={1}>` | `fontSizeHeading1`, `lineHeightHeading1` |
| `<Title level={2}>` | `fontSizeHeading2`, `lineHeightHeading2` |
| `<Title level={3}>` | `fontSizeHeading3`, `lineHeightHeading3` |
| `<Title level={4}>` | `fontSizeHeading4`, `lineHeightHeading4` |
| `<Title level={5}>` | `fontSizeHeading5`, `lineHeightHeading5` |
| `<Text>` 默认 | `fontSize`, `lineHeight`, `colorText` |
| `<Text type="secondary">` | `colorTextSecondary` |
| `<Paragraph>` | 同上正文 + 段落间距（见下） |

**段落间距**：Ant 无单独「段落间距」token。建议段落之间使用间距 token（如 `marginBottom: token.margin` 或 `marginSM`），或 1em，与设计系统间距尺度一致。

---

## 3. 间距

统一尺度（4px 基准）：4 / 8 / 12 / 16 / 20 / 24 / 32 / 48 px。

| Token | 值 (px) | 典型场景 |
|-------|---------|----------|
| `marginXXS` / `paddingXXS` | 4 | 紧凑内边距、图标与文字间距 |
| `marginXS` / `paddingXS` | 8 | 小间距、表单项内边距 |
| `marginSM` / `paddingSM` | 12 | 表单项之间、小块间距 |
| `margin` / `padding` | 16 | 常规区块间距、内容内边距 |
| `marginMD` / `paddingMD` | 20 | 中等区块 |
| `marginLG` / `paddingLG` | 24 | 区块与区块、页面 Content 内边距 |
| `marginXL` / `paddingXL` | 32 | 大区块、分区间距 |
| `marginXXL` | 48 | 特大分区 |

后续页面改版时优先使用上述 token，避免魔法数字（如 `padding: 24` 改为 `token.paddingLG` 或通过主题注入）。

---

## 4. 圆角

| Token | 值 (px) | 组件/场景 |
|-------|---------|-----------|
| `borderRadius` | 6 | 基础圆角：按钮、输入框、Select 等 |
| `borderRadiusXS` | 2 | 小圆角：Tag、Segmented 等 |
| `borderRadiusSM` | 4 | 小尺寸按钮、输入框 |
| `borderRadiusLG` | 8 | 卡片、Modal 等大容器 |
| `borderRadiusOuter` | 4 | 外圈圆角 |

---

## 5. 步骤状态约定（阶段 0.3）

任务步骤的五种状态与展示形式、Ant Design Steps 映射如下；语义色与 [tokens.ts](tokens.ts) 一致（success → colorSuccess、error → colorError、warning → colorWarning、进行中/待确认 → colorPrimary 或 colorInfo）。

| 状态值 | 标签色/语义色 | 图标（可选） | 简短文案 | Ant Steps 映射 |
|--------|----------------|--------------|----------|----------------|
| `pending` | default（中性） | — | 待执行 | wait |
| `running` | primary / info | LoadingOutlined | 进行中 | process |
| `waiting_user` | warning 或 primary | ExclamationCircleOutlined / UserOutlined | 待确认 | process（文案「待确认」区分） |
| `completed` | success | CheckCircleOutlined | 已完成 | finish |
| `failed` | error | CloseCircleOutlined | 失败 | error |

阶段 2 任务详情页使用 Steps 或 Tag 时，按上表选用标签色与文案；若有 [stepStatus.ts](stepStatus.ts)，可直接引用其配置。

---

## 6. 主按钮/次按钮约定（阶段 0.3）

- **主按钮（Primary）**：用于主流程、关键确认。与 design token 主色一致。  
  示例：创建任务、开始解析、开始分析、开始参数提取、开始生成框架、接受并继续、重新生成框架、开始按章生成、下载 Word。
- **次按钮（Default）或链接（Link）**：用于次要或辅助操作，不抢主按钮视觉。  
  示例：取消、添加要点、重试、重新生成本章（若产品上不强调为主流程可放次要）。

同一区块内主操作仅一个主按钮，其余用次按钮或链接；风格与设计系统主色/次色 token 一致。

---

## 7. 与 0.2、0.3 的衔接

- **0.2**：将 `designTokens`（见 `tokens.ts`）传入 `ConfigProvider` 的 `theme.token`，主色、圆角、字体等即可全局生效。主题配置见 `theme/config.ts`。
- **0.3**：已落实。步骤状态展示形式与主/次按钮适用场景见上文「步骤状态约定」与「主按钮/次按钮约定」。

**新写样式约定**：新增或修改样式时优先使用 theme token（如组件内通过 `useToken()` 获取，或使用设计系统间距/颜色），避免硬编码色值与间距，便于后续换肤与统一改版。

**侧栏与导航（阶段 1.2）**：侧栏顶部品牌区使用 `fontSizeHeading5`、`fontWeightStrong`、`colorText`；侧栏 Menu 选中项与设计系统主色一致，由 `theme/config.ts` 的 `components.Menu.itemSelectedColor`、`itemSelectedBg` 控制。

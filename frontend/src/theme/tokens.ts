/**
 * BIM 标书生成 App — 设计 Token 定义（阶段 0.1）
 *
 * 命名与 Ant Design 5 Seed/Map Token 对齐，便于 0.2 直接传入 ConfigProvider theme.token。
 * 色值采用 Ant 默认或团队约定，后续可按品牌调整。
 */

// ========== 颜色 Token ==========
// 主色、语义色（Seed）；中性色背景/边框/文字（Map）

export const colorTokens = {
  // Seed — 主色与语义色
  colorPrimary: '#1677ff',
  colorSuccess: '#52c41a',
  colorWarning: '#faad14',
  colorError: '#ff4d4f',
  colorInfo: '#1677ff',
  colorLink: '#1677ff',

  // Map — 中性色：背景层级
  colorBgLayout: '#f5f5f5',
  colorBgContainer: '#ffffff',
  colorBgElevated: '#ffffff',

  // Map — 中性色：边框
  colorBorder: '#d9d9d9',
  colorBorderSecondary: '#f0f0f0',

  // Map — 中性色：文字层级
  colorText: 'rgba(0, 0, 0, 0.88)',
  colorTextSecondary: 'rgba(0, 0, 0, 0.65)',
  colorTextTertiary: 'rgba(0, 0, 0, 0.45)',
  colorTextQuaternary: 'rgba(0, 0, 0, 0.25)',
} as const

// ========== 字体与层级（Typography）Token ==========
// 字体族、字号、行高、字重；与 Ant Design Typography 组件对应（见 theme/README.md）

export const typographyTokens = {
  fontFamily:
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif",
  fontFamilyCode:
    "'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace",

  fontSize: 14,
  lineHeight: 1.5714285714285714,

  fontSizeLG: 16,
  lineHeightLG: 1.5,
  fontSizeSM: 12,
  lineHeightSM: 1.6666666666666667,

  fontSizeHeading1: 38,
  lineHeightHeading1: 1.2105263157894737,
  fontSizeHeading2: 30,
  lineHeightHeading2: 1.2666666666666666,
  fontSizeHeading3: 24,
  lineHeightHeading3: 1.3333333333333333,
  fontSizeHeading4: 20,
  lineHeightHeading4: 1.4,
  fontSizeHeading5: 16,
  lineHeightHeading5: 1.5,

  fontWeightStrong: 600,
} as const

// ========== 间距 Token ==========
// 统一尺度 4 / 8 / 16 / 24 / 32 px，对应 Ant margin/padding 命名

export const spacingTokens = {
  marginXXS: 4,
  marginXS: 8,
  marginSM: 12,
  margin: 16,
  marginMD: 20,
  marginLG: 24,
  marginXL: 32,
  marginXXL: 48,

  paddingXXS: 4,
  paddingXS: 8,
  paddingSM: 12,
  padding: 16,
  paddingMD: 20,
  paddingLG: 24,
  paddingXL: 32,
} as const

// ========== 圆角 Token ==========
// 按钮、卡片、输入框等组件圆角约定

export const radiusTokens = {
  borderRadius: 6,
  borderRadiusXS: 2,
  borderRadiusSM: 4,
  borderRadiusLG: 8,
  borderRadiusOuter: 4,
} as const

// ========== 聚合导出（供 0.2 ConfigProvider theme.token 使用）==========

export const designTokens = {
  ...colorTokens,
  ...typographyTokens,
  ...spacingTokens,
  ...radiusTokens,
} as const

export type DesignTokens = typeof designTokens

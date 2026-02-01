/**
 * BIM 标书生成 App — 主题配置（阶段 0.2）
 *
 * 供 ConfigProvider 使用；后续可在此扩展 algorithm（如暗色）、按组件覆盖 token 等。
 * 阶段 1.2：侧栏 Menu 选中项与设计系统主色一致，显式设置 itemSelectedColor。
 */

import { designTokens } from './tokens'

export const themeConfig = {
  token: designTokens,
  components: {
    Menu: {
      itemSelectedColor: designTokens.colorPrimary,
      itemSelectedBg: `${designTokens.colorPrimary}14`,
    },
  },
}

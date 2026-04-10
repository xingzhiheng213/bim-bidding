import '@testing-library/jest-dom/vitest'

/** Ant Design / rc-table 在 jsdom 中依赖的浏览器 API 补齐 */
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  configurable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

const _stubStyle = {
  width: '1024px',
  height: '768px',
  getPropertyValue: () => '',
} as unknown as CSSStyleDeclaration

window.getComputedStyle = () => _stubStyle

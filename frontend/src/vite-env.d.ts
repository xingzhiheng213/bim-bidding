/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 若未设置，则使用当前页面协议 + hostname + :8001（局域网可访问） */
  readonly VITE_API_BASE?: string
  /** 与后端 ADMIN_API_KEY 一致；后端启用鉴权时必填 */
  readonly VITE_API_KEY?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

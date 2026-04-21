import axios from 'axios'

/** 与页面同主机、8001 端口，便于局域网用 IP 访问时无需写死 VITE_API_BASE */
function resolveApiBase(): string {
  const fromEnv = import.meta.env.VITE_API_BASE?.trim()
  if (fromEnv) return fromEnv
  if (typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.hostname}:8001`
  }
  return 'http://localhost:8001'
}

const baseURL = resolveApiBase()

export const api = axios.create({ baseURL })

const apiKey = import.meta.env.VITE_API_KEY?.trim()
if (apiKey) {
  api.defaults.headers.common['X-API-Key'] = apiKey
}

const DEBUG_USER_STORAGE_KEY = 'bim_debug_user_id'
const DEBUG_TENANT_STORAGE_KEY = 'bim_debug_tenant_id'

function readStorageValue(key: string): string | null {
  if (typeof window === 'undefined') return null
  try {
    const v = window.localStorage.getItem(key)?.trim()
    return v ? v : null
  } catch {
    return null
  }
}

export function getIdentityScope(): { tenantId: string; userId: string } {
  const userId =
    import.meta.env.VITE_DEBUG_USER_ID?.trim() ||
    readStorageValue(DEBUG_USER_STORAGE_KEY) ||
    'dev-user'
  const tenantId =
    import.meta.env.VITE_DEBUG_TENANT_ID?.trim() ||
    readStorageValue(DEBUG_TENANT_STORAGE_KEY) ||
    'default'
  return { tenantId, userId }
}

export function setIdentityScope(scope: { tenantId: string; userId: string }): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(
      DEBUG_TENANT_STORAGE_KEY,
      scope.tenantId.trim() || 'default',
    )
    window.localStorage.setItem(
      DEBUG_USER_STORAGE_KEY,
      scope.userId.trim() || 'dev-user',
    )
  } catch {
    // ignore quota/private mode
  }
}

export function getIdentityScopeKey(): string {
  const { tenantId, userId } = getIdentityScope()
  return `${tenantId}:${userId}`
}

api.interceptors.request.use((cfg) => {
  const accessToken =
    import.meta.env.VITE_ACCESS_TOKEN?.trim() ||
    readStorageValue('bim_access_token') ||
    ''
  if (accessToken) {
    cfg.headers.Authorization = `Bearer ${accessToken}`
  }
  const { tenantId, userId } = getIdentityScope()
  cfg.headers['X-Debug-User-Id'] = userId
  cfg.headers['X-Debug-Tenant-Id'] = tenantId
  return cfg
})

export interface HealthResponse {
  status: string
}

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>('/health')
  return data
}

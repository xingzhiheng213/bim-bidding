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

export interface HealthResponse {
  status: string
}

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>('/health')
  return data
}

import { api } from './client'

export interface LlmProviderStatus {
  provider: string
  configured: boolean
  masked_key: string | null
  base_url: string | null
}

export interface GetSettingsLlmResponse {
  providers: LlmProviderStatus[]
}

export async function getSettingsLlm(): Promise<GetSettingsLlmResponse> {
  const { data } = await api.get<GetSettingsLlmResponse>('/api/settings/llm')
  return data
}

export interface PostSettingsLlmResponse {
  provider: string
  configured: boolean
  masked_key: string | null
  base_url: string | null
}

export async function postSettingsLlm(
  provider: string,
  apiKey: string | undefined,
  baseUrl: string | undefined,
): Promise<PostSettingsLlmResponse> {
  const body: { provider: string; api_key?: string; base_url?: string } = { provider }
  if (apiKey != null && apiKey.trim() !== '') body.api_key = apiKey.trim()
  if (baseUrl !== undefined) body.base_url = baseUrl
  const { data } = await api.post<PostSettingsLlmResponse>('/api/settings/llm', body)
  return data
}

// --- Model config (default + per-step) ---

export interface SupportedModel {
  id: string
  name: string
  provider: string
}

export interface GetSettingsModelsResponse {
  default_model: string
  steps: {
    analyze: string | null
    params: string | null
    framework: string | null
    chapters: string | null
  }
  supported_models: SupportedModel[]
}

export async function getSettingsModels(): Promise<GetSettingsModelsResponse> {
  const { data } = await api.get<GetSettingsModelsResponse>('/api/settings/models')
  return data
}

export interface PostSettingsModelsBody {
  default_model?: string | null
  analyze_model?: string | null
  params_model?: string | null
  framework_model?: string | null
  chapters_model?: string | null
}

export async function postSettingsModels(body: PostSettingsModelsBody): Promise<GetSettingsModelsResponse> {
  const { data } = await api.post<GetSettingsModelsResponse>('/api/settings/models', body)
  return data
}

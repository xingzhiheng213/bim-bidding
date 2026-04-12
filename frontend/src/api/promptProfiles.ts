import { api } from './client'

export interface PromptProfileSummary {
  id: number
  name: string
  slug: string | null
  discipline: string
  is_builtin: boolean
  created_at: string
  updated_at: string
}

export interface PromptProfileDetail extends PromptProfileSummary {
  semantic_overrides: Record<string, string> | null
  user_id: string | null
}

export interface PromptProfileCreateBody {
  name: string
  discipline: string
  slug?: string | null
  semantic_overrides?: Record<string, string> | null
}

export interface PromptProfileUpdateBody {
  name?: string
  discipline?: string
  slug?: string | null
  semantic_overrides?: Record<string, string> | null
}

export interface GenerateSemanticResponse {
  slot_key?: string | null
  text?: string | null
  overrides?: Record<string, string> | null
}

export async function listPromptProfiles(): Promise<PromptProfileSummary[]> {
  const { data } = await api.get<PromptProfileSummary[]>('/api/prompt-profiles')
  return data
}

export async function getPromptProfile(id: number): Promise<PromptProfileDetail> {
  const { data } = await api.get<PromptProfileDetail>(`/api/prompt-profiles/${id}`)
  return data
}

export async function createPromptProfile(body: PromptProfileCreateBody): Promise<PromptProfileDetail> {
  const { data } = await api.post<PromptProfileDetail>('/api/prompt-profiles', body)
  return data
}

export async function updatePromptProfile(
  id: number,
  body: PromptProfileUpdateBody
): Promise<PromptProfileDetail> {
  const { data } = await api.patch<PromptProfileDetail>(`/api/prompt-profiles/${id}`, body)
  return data
}

export async function deletePromptProfile(id: number): Promise<void> {
  await api.delete(`/api/prompt-profiles/${id}`)
}

export async function fetchPromptProfileDisciplines(): Promise<{ items: string[] }> {
  const { data } = await api.get<{ items: string[] }>('/api/prompt-profiles/disciplines')
  return data
}

export async function generatePromptProfileSemantic(body: {
  profile_name: string
  discipline: string
  slot_key?: string | null
}): Promise<GenerateSemanticResponse> {
  const { data } = await api.post<GenerateSemanticResponse>(
    '/api/prompt-profiles/generate-semantic',
    body
  )
  return data
}

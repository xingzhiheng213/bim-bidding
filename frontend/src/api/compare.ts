import { api } from './client'

export interface DiffItem {
  type: 'equal' | 'add' | 'del'
  text: string
}

export interface CompareResponse {
  diff: DiffItem[]
}

export interface DiffResponse {
  original: string
  modified: string
  diff: DiffItem[]
}

export interface CompareMetaFramework {
  has_diff: boolean
}

export interface CompareMetaChapterItem {
  number: number
  has_diff: boolean
  label: string
}

export interface CompareMetaResponse {
  has_any: boolean
  framework: CompareMetaFramework
  chapters: CompareMetaChapterItem[]
}

export async function postCompare(
  original: string,
  modified: string,
): Promise<CompareResponse> {
  const { data } = await api.post<CompareResponse>('/api/compare', {
    original,
    modified,
  })
  return data
}

export async function getFrameworkDiff(taskId: string): Promise<DiffResponse> {
  const { data } = await api.get<DiffResponse>(
    `/api/tasks/${taskId}/steps/framework/diff`,
  )
  return data
}

export async function getChaptersDiff(
  taskId: string,
  chapterNumber: number,
): Promise<DiffResponse> {
  const { data } = await api.get<DiffResponse>(
    `/api/tasks/${taskId}/steps/chapters/diff`,
    { params: { chapter_number: chapterNumber } },
  )
  return data
}

export async function getTaskCompareMeta(taskId: string): Promise<CompareMetaResponse> {
  const { data } = await api.get<CompareMetaResponse>(`/api/tasks/${taskId}/compare-meta`)
  return data
}

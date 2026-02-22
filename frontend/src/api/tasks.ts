import { api } from './client'

export interface TaskStep {
  id: number
  task_id: number
  step_key: string
  status: string
  input_snapshot: string | null
  output_snapshot: string | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface TaskDetail {
  id: number
  user_id: string | null
  name: string | null
  status: string
  created_at: string
  updated_at: string
  steps: TaskStep[]
}

export interface CreateTaskResponse {
  id: number
  name: string | null
  status: string
  created_at: string
}

export interface TaskSummary {
  id: number
  name: string | null
  status: string
  created_at: string
}

export async function createTask(args?: { initialSteps?: string[]; name?: string }): Promise<CreateTaskResponse> {
  const { data } = await api.post<CreateTaskResponse>('/api/tasks', {
    initial_steps: args?.initialSteps ?? undefined,
    name: args?.name ?? undefined,
  })
  return data
}

export async function getTask(id: string): Promise<TaskDetail> {
  const { data } = await api.get<TaskDetail>(`/api/tasks/${id}`)
  return data
}

export async function getTasks(): Promise<TaskSummary[]> {
  const { data } = await api.get<TaskSummary[]>('/api/tasks')
  return data
}

export async function deleteTask(id: string): Promise<void> {
  await api.delete(`/api/tasks/${id}`)
}

export interface CancelTaskResponse {
  message: string
  revoked: boolean
  step_key?: string
}

export async function cancelTask(taskId: string): Promise<CancelTaskResponse> {
  const { data } = await api.post<CancelTaskResponse>(`/api/tasks/${taskId}/cancel`)
  return data
}

export interface UploadTaskFileResponse {
  step_key: string
  status: string
  message?: string
  stored_path?: string
}

export async function uploadTaskFile(taskId: string, file: File): Promise<UploadTaskFileResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post<UploadTaskFileResponse>(`/api/tasks/${taskId}/upload`, formData)
  return data
}

export interface RunExtractStepResponse {
  message: string
  step_key: string
}

export async function runExtractStep(taskId: string): Promise<RunExtractStepResponse> {
  const { data } = await api.post<RunExtractStepResponse>(`/api/tasks/${taskId}/steps/extract/run`)
  return data
}

export interface RunAnalyzeStepResponse {
  message: string
  step_key: string
}

export async function runAnalyzeStep(taskId: string): Promise<RunAnalyzeStepResponse> {
  const { data } = await api.post<RunAnalyzeStepResponse>(`/api/tasks/${taskId}/steps/analyze/run`)
  return data
}

export interface RunParamsStepResponse {
  message: string
  step_key: string
}

export async function runParamsStep(taskId: string): Promise<RunParamsStepResponse> {
  const { data } = await api.post<RunParamsStepResponse>(`/api/tasks/${taskId}/steps/params/run`)
  return data
}

export interface RunFrameworkStepResponse {
  message: string
  step_key: string
}

export async function runFrameworkStep(taskId: string): Promise<RunFrameworkStepResponse> {
  const { data } = await api.post<RunFrameworkStepResponse>(`/api/tasks/${taskId}/steps/framework/run`)
  return data
}

export async function regenerateFrameworkStep(taskId: string): Promise<RunFrameworkStepResponse> {
  const { data } = await api.post<RunFrameworkStepResponse>(`/api/tasks/${taskId}/steps/framework/regenerate`)
  return data
}

export interface AcceptFrameworkStepResponse {
  message: string
  step_key: string
}

export async function saveFrameworkPoints(
  taskId: string,
  added_points: string[],
): Promise<AcceptFrameworkStepResponse> {
  const { data } = await api.post<AcceptFrameworkStepResponse>(
    `/api/tasks/${taskId}/steps/framework/save-points`,
    { added_points },
  )
  return data
}

export async function acceptFrameworkStep(
  taskId: string,
  added_points: string[],
): Promise<AcceptFrameworkStepResponse> {
  const { data } = await api.post<AcceptFrameworkStepResponse>(
    `/api/tasks/${taskId}/steps/framework/accept`,
    { added_points },
  )
  return data
}

export interface RunChaptersStepResponse {
  message: string
  step_key: string
}

export async function runChaptersStep(
  taskId: string,
  chapterNumbers?: number[],
): Promise<RunChaptersStepResponse> {
  const { data } = await api.post<RunChaptersStepResponse>(
    `/api/tasks/${taskId}/steps/chapters/run`,
    chapterNumbers != null && chapterNumbers.length > 0 ? { chapter_numbers: chapterNumbers } : {},
  )
  return data
}

export interface SaveChapterPointsResponse {
  message: string
  step_key: string
}

export async function saveChapterPoints(
  taskId: string,
  chapterNumber: number,
  addedPoints: string[],
): Promise<SaveChapterPointsResponse> {
  const { data } = await api.post<SaveChapterPointsResponse>(
    `/api/tasks/${taskId}/steps/chapters/save-points`,
    { chapter_number: chapterNumber, added_points: addedPoints },
  )
  return data
}

export interface RegenerateChapterResponse {
  message: string
  step_key: string
}

export async function regenerateChapter(
  taskId: string,
  chapterNumber: number,
  addedPoints?: string[],
): Promise<RegenerateChapterResponse> {
  const { data } = await api.post<RegenerateChapterResponse>(
    `/api/tasks/${taskId}/steps/chapters/regenerate`,
    addedPoints != null && addedPoints.length > 0
      ? { chapter_number: chapterNumber, added_points: addedPoints }
      : { chapter_number: chapterNumber },
  )
  return data
}

export interface RunReviewStepResponse {
  message: string
  step_key: string
}

export async function runReview(
  taskId: string,
  chapterNumber?: number,
): Promise<RunReviewStepResponse> {
  const url =
    chapterNumber != null
      ? `/api/tasks/${taskId}/steps/review/run?chapter_number=${chapterNumber}`
      : `/api/tasks/${taskId}/steps/review/run`
  const { data } = await api.post<RunReviewStepResponse>(url)
  return data
}

export interface AcceptReviewResponse {
  message: string
  step_key: string
}

export async function acceptReview(
  taskId: string,
  chapterNumber: number,
  acceptedItems: string[],
): Promise<AcceptReviewResponse> {
  const { data } = await api.post<AcceptReviewResponse>(
    `/api/tasks/${taskId}/steps/review/accept`,
    { chapter_number: chapterNumber, accepted_items: acceptedItems },
  )
  return data
}

export interface RegenerateAllFromReviewResponse {
  message: string
  step_key: string
}

export async function regenerateAllChaptersFromReview(
  taskId: string,
): Promise<RegenerateAllFromReviewResponse> {
  const { data } = await api.post<RegenerateAllFromReviewResponse>(
    `/api/tasks/${taskId}/steps/review/regenerate-all`,
  )
  return data
}

/** Download task DOCX. Returns blob for programmatic download. */
export async function downloadTaskDocx(taskId: string): Promise<Blob> {
  const { data } = await api.get(`/api/tasks/${taskId}/download`, {
    responseType: 'blob',
  })
  return data
}

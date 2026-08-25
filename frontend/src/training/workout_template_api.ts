import { apiDelete, apiGet, apiPost, apiPut } from '../shared/http'
import type { CreateWorkoutTemplatePayload, UpdateWorkoutTemplatePayload, WorkoutTemplate } from '../shared/types'

export function fetchWorkoutTemplates(userId: number): Promise<WorkoutTemplate[]> {
  return apiGet<WorkoutTemplate[]>('/workout-templates', { user_id: userId })
}

export function createWorkoutTemplate(payload: CreateWorkoutTemplatePayload): Promise<WorkoutTemplate> {
  return apiPost<WorkoutTemplate>('/workout-templates', payload)
}

export function fetchWorkoutTemplate(templateId: number): Promise<WorkoutTemplate> {
  return apiGet<WorkoutTemplate>(`/workout-templates/${templateId}`)
}

export function updateWorkoutTemplate(templateId: number, payload: UpdateWorkoutTemplatePayload): Promise<WorkoutTemplate> {
  return apiPut<WorkoutTemplate>(`/workout-templates/${templateId}`, payload)
}

export function deleteWorkoutTemplate(templateId: number): Promise<void> {
  return apiDelete<void>(`/workout-templates/${templateId}`)
}

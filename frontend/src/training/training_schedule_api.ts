import { apiDelete, apiGet, apiPost, apiPut } from '../shared/http'
import type { CreateTrainingSchedulePayload, TrainingScheduleEntry, UpdateTrainingSchedulePayload } from '../shared/types'

export function createTrainingSchedule(payload: CreateTrainingSchedulePayload): Promise<TrainingScheduleEntry> {
  return apiPost<TrainingScheduleEntry>('/training-schedule', payload)
}

export function updateTrainingSchedule(id: number, payload: UpdateTrainingSchedulePayload): Promise<TrainingScheduleEntry> {
  return apiPut<TrainingScheduleEntry>(`/training-schedule/${id}`, payload)
}

export function deleteTrainingSchedule(id: number): Promise<void> {
  return apiDelete<void>(`/training-schedule/${id}`)
}

export function fetchTrainingSchedule(userId: number, month: string): Promise<TrainingScheduleEntry[]> {
  return apiGet<TrainingScheduleEntry[]>('/training-schedule', { user_id: userId, month })
}

export function fetchTrainingScheduleEntry(id: number): Promise<TrainingScheduleEntry> {
  return apiGet<TrainingScheduleEntry>(`/training-schedule/${id}`)
}

export function linkActualSchedule(id: number, exerciseSessionId: number): Promise<TrainingScheduleEntry> {
  return apiPut<TrainingScheduleEntry>(`/training-schedule/${id}/link-actual`, { exercise_session_id: exerciseSessionId })
}

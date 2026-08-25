import { apiGet, apiPost, apiPut } from '../shared/http'
import { toISODate } from '../shared/date_utils'
import type {
  CreateDailyStepsPayload,
  CreateExerciseSessionPayload,
  DailyStepsRecord,
  ExerciseSession,
  UpdateDailyStepsPayload,
} from '../shared/types'

export function fetchExerciseSessions(userId: number, dateStart: Date, dateEnd: Date): Promise<ExerciseSession[]> {
  return apiGet<ExerciseSession[]>('/exercise-sessions', {
    user_id: userId,
    date_start: toISODate(dateStart),
    date_end: toISODate(dateEnd),
  })
}

export function createExerciseSession(payload: CreateExerciseSessionPayload): Promise<ExerciseSession> {
  return apiPost<ExerciseSession>('/exercise-sessions', payload)
}

export function fetchDailySteps(userId: number, dateStart: Date, dateEnd: Date): Promise<DailyStepsRecord[]> {
  return apiGet<DailyStepsRecord[]>('/daily-steps', {
    user_id: userId,
    date_start: toISODate(dateStart),
    date_end: toISODate(dateEnd),
  })
}

export function createDailyStepsRecord(payload: CreateDailyStepsPayload): Promise<{ success: boolean; record_id: number }> {
  return apiPost('/daily-steps', payload)
}

export function updateDailyStepsRecord(recordId: number, payload: UpdateDailyStepsPayload): Promise<DailyStepsRecord> {
  return apiPut<DailyStepsRecord>(`/daily-steps/${recordId}`, payload)
}

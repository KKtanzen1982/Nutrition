import { apiDelete, apiGet, apiPost } from '../shared/http'
import type { CreateTrainingProgramPayload, TrainingProgram } from '../shared/types'

export function createTrainingProgram(payload: CreateTrainingProgramPayload): Promise<TrainingProgram> {
  return apiPost<TrainingProgram>('/training-programs', payload)
}

export function fetchTrainingPrograms(userId: number): Promise<TrainingProgram[]> {
  return apiGet<TrainingProgram[]>('/training-programs', { user_id: userId })
}

export function deleteTrainingProgram(programId: number): Promise<void> {
  return apiDelete<void>(`/training-programs/${programId}`)
}

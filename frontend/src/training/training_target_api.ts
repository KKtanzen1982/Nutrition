import { apiGet, apiPut } from '../shared/http'
import type { TrainingTarget } from '../shared/types'

export function fetchTrainingTargets(userId: number): Promise<TrainingTarget[]> {
  return apiGet<TrainingTarget[]>('/training-targets', { user_id: userId })
}

export function updateTrainingTargets(userId: number, targets: TrainingTarget[]): Promise<TrainingTarget[]> {
  return apiPut<TrainingTarget[]>(`/training-targets?user_id=${userId}`, { targets })
}

import { apiGet, apiPut } from '../shared/http'
import type { GoalHistoryEntry, UpdateUserPayload, UserProfile } from '../shared/types'

export function fetchUser(userId: number): Promise<UserProfile> {
  return apiGet<UserProfile>(`/users/${userId}`)
}

export function updateUser(userId: number, payload: UpdateUserPayload): Promise<UserProfile> {
  return apiPut<UserProfile>(`/users/${userId}`, payload)
}

export function fetchUserGoalHistory(userId: number): Promise<GoalHistoryEntry[]> {
  return apiGet<GoalHistoryEntry[]>(`/users/${userId}/history`)
}

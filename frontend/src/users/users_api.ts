import { apiGet, apiPut } from '../shared/http'
import type { GoalHistoryEntry, NutritionTargets, UpdateUserPayload, UpdateWeightGoalPayload, UserProfile, WeightGoal } from '../shared/types'

export function fetchUser(userId: number): Promise<UserProfile> {
  return apiGet<UserProfile>(`/users/${userId}`)
}

export function updateUser(userId: number, payload: UpdateUserPayload): Promise<UserProfile> {
  return apiPut<UserProfile>(`/users/${userId}`, payload)
}

export function fetchUserGoalHistory(userId: number): Promise<GoalHistoryEntry[]> {
  return apiGet<GoalHistoryEntry[]>(`/users/${userId}/history`)
}

export function fetchNutritionTargets(userId: number): Promise<NutritionTargets> {
  return apiGet<NutritionTargets>(`/users/${userId}/nutrition-targets`)
}

export function fetchWeightGoal(userId: number): Promise<WeightGoal> {
  return apiGet<WeightGoal>(`/users/${userId}/weight-goal`)
}

export function updateWeightGoal(userId: number, payload: UpdateWeightGoalPayload): Promise<WeightGoal> {
  return apiPut<WeightGoal>(`/users/${userId}/weight-goal`, payload)
}

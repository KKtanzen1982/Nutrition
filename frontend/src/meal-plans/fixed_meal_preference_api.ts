import { apiDelete, apiGet, apiPut } from '../shared/http'
import type { FixedMealPreference, FixedMealType, SharedFixedMealType } from '../shared/types'

export function fetchFixedMealPreferences(userId: number): Promise<FixedMealPreference[]> {
  return apiGet<FixedMealPreference[]>('/fixed-meal-preferences', { user_id: userId })
}

export function fetchSharedFixedMealPreferences(): Promise<FixedMealPreference[]> {
  return apiGet<FixedMealPreference[]>('/fixed-meal-preferences/shared')
}

export function setFixedMealPreference(
  userId: number,
  mealType: FixedMealType,
  recipeId: number,
  durationDays?: number | null,
): Promise<FixedMealPreference> {
  return apiPut<FixedMealPreference>('/fixed-meal-preferences', {
    user_id: userId,
    meal_type: mealType,
    recipe_id: recipeId,
    duration_days: durationDays ?? null,
  })
}

export function setSharedFixedMealPreference(
  mealType: SharedFixedMealType,
  recipeId: number,
  durationDays?: number | null,
): Promise<FixedMealPreference> {
  return apiPut<FixedMealPreference>('/fixed-meal-preferences', {
    meal_type: mealType,
    recipe_id: recipeId,
    duration_days: durationDays ?? null,
  })
}

export function deleteFixedMealPreference(id: number): Promise<void> {
  return apiDelete<void>(`/fixed-meal-preferences/${id}`)
}

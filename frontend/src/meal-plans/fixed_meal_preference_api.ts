import { apiDelete, apiGet, apiPut } from '../shared/http'
import type { FixedMealPreference, FixedMealType } from '../shared/types'

export function fetchFixedMealPreferences(userId: number): Promise<FixedMealPreference[]> {
  return apiGet<FixedMealPreference[]>('/fixed-meal-preferences', { user_id: userId })
}

export function setFixedMealPreference(
  userId: number,
  mealType: FixedMealType,
  recipeId: number,
): Promise<FixedMealPreference> {
  return apiPut<FixedMealPreference>('/fixed-meal-preferences', { user_id: userId, meal_type: mealType, recipe_id: recipeId })
}

export function deleteFixedMealPreference(id: number): Promise<void> {
  return apiDelete<void>(`/fixed-meal-preferences/${id}`)
}

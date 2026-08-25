import { apiGet, apiPost, apiPut } from '../shared/http'
import type {
  AdjustServingWeightPayload,
  ConfirmMealPlanResponse,
  GenerateMealPlanPayload,
  MealPlanDetail,
  RegenerateDayPayload,
  ReplaceMealPayload,
  SearchAndReplacePayload,
} from '../shared/types'

export function generateMealPlan(payload: GenerateMealPlanPayload): Promise<MealPlanDetail> {
  return apiPost('/meal-plans/generate', payload)
}

export function fetchMealPlan(planId: number): Promise<MealPlanDetail> {
  return apiGet<MealPlanDetail>(`/meal-plans/${planId}`)
}

export function confirmMealPlan(planId: number): Promise<ConfirmMealPlanResponse> {
  return apiPost(`/meal-plans/${planId}/confirm`, {})
}

export function replaceMeal(planId: number, payload: ReplaceMealPayload): Promise<MealPlanDetail> {
  return apiPost(`/meal-plans/${planId}/adjust/replace-meal`, payload)
}

export function regenerateDay(planId: number, payload: RegenerateDayPayload): Promise<MealPlanDetail> {
  return apiPost(`/meal-plans/${planId}/adjust/regenerate-day`, payload)
}

export function searchAndReplaceMeal(planId: number, payload: SearchAndReplacePayload): Promise<MealPlanDetail> {
  return apiPost(`/meal-plans/${planId}/adjust/search-replace`, payload)
}

export function adjustServingWeight(planId: number, payload: AdjustServingWeightPayload): Promise<MealPlanDetail> {
  return apiPut(`/meal-plans/${planId}/adjust/serving-weight`, payload)
}

import { apiGet, apiPut } from '../shared/http'
import type { IngredientLocationPreference, SetIngredientLocationPreferencePayload } from '../shared/types'

export function fetchIngredientLocationPreferences(ingredientId: number): Promise<IngredientLocationPreference[]> {
  return apiGet<IngredientLocationPreference[]>(`/ingredients/${ingredientId}/location-preference`)
}

export function setIngredientLocationPreferences(
  ingredientId: number,
  payload: SetIngredientLocationPreferencePayload,
): Promise<IngredientLocationPreference[]> {
  return apiPut(`/ingredients/${ingredientId}/location-preference`, payload)
}

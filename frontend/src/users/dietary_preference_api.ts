import { apiGet, apiPut } from '../shared/http'
import type { DietaryPreference, UpdateDietaryPreferencePayload } from '../shared/types'

export function fetchDietaryPreferences(userId: number): Promise<DietaryPreference> {
  return apiGet(`/users/${userId}/dietary-preferences`)
}

export function updateDietaryPreferences(userId: number, payload: UpdateDietaryPreferencePayload): Promise<DietaryPreference> {
  return apiPut(`/users/${userId}/dietary-preferences`, payload)
}

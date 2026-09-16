import { apiGet, apiPut } from '../shared/http'
import type { SoupDayPreference } from '../shared/types'

export function fetchSoupDays(): Promise<SoupDayPreference> {
  return apiGet<SoupDayPreference>('/soup-day-preferences')
}

export function setSoupDays(lunchDays: number[], dinnerDays: number[]): Promise<SoupDayPreference> {
  return apiPut<SoupDayPreference>('/soup-day-preferences', { lunch_days: lunchDays, dinner_days: dinnerDays })
}

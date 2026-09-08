import { apiGet } from '../shared/http'
import type { PrepPlan } from '../shared/types'

export function fetchPrepPlan(planId: number): Promise<PrepPlan> {
  return apiGet<PrepPlan>(`/meal-plans/${planId}/prep-plan`)
}

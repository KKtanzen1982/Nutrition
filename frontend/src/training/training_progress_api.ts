import { apiGet } from '../shared/http'
import type { WeeklyProgress } from '../shared/types'

export function fetchWeeklyProgress(userId: number, weekStart?: string): Promise<WeeklyProgress> {
  return apiGet<WeeklyProgress>('/training-progress', { user_id: userId, week_start: weekStart })
}

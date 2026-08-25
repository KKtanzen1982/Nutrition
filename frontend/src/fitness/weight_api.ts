import { apiDelete, apiGet, apiPost, apiPut } from '../shared/http'
import { toISODate } from '../shared/date_utils'
import type { CreateWeightRecordPayload, UpdateWeightRecordPayload, WeightRecord } from '../shared/types'

export function fetchWeightRecords(userId: number, dateStart: Date, dateEnd: Date): Promise<WeightRecord[]> {
  return apiGet<WeightRecord[]>('/weight-records', {
    user_id: userId,
    date_start: toISODate(dateStart),
    date_end: toISODate(dateEnd),
  })
}

export function createWeightRecord(payload: CreateWeightRecordPayload): Promise<{ success: boolean; record_id: number }> {
  return apiPost('/weight-records', payload)
}

export function updateWeightRecord(
  recordId: number,
  payload: UpdateWeightRecordPayload,
): Promise<{ success: boolean; record: WeightRecord }> {
  return apiPut(`/weight-records/${recordId}`, payload)
}

export function deleteWeightRecord(recordId: number): Promise<{ success: boolean }> {
  return apiDelete(`/weight-records/${recordId}`)
}

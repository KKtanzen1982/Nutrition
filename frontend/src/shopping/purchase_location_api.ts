import { apiDelete, apiGet, apiPost, apiPut } from '../shared/http'
import type { CreatePurchaseLocationPayload, PurchaseLocation, UpdatePurchaseLocationPayload } from '../shared/types'

export function listPurchaseLocations(activeOnly = true): Promise<PurchaseLocation[]> {
  return apiGet<PurchaseLocation[]>('/purchase-locations', { active_only: activeOnly })
}

export function createPurchaseLocation(payload: CreatePurchaseLocationPayload): Promise<PurchaseLocation> {
  return apiPost('/purchase-locations', payload)
}

export function updatePurchaseLocation(
  locationId: number,
  payload: UpdatePurchaseLocationPayload,
): Promise<PurchaseLocation> {
  return apiPut(`/purchase-locations/${locationId}`, payload)
}

export function deletePurchaseLocation(locationId: number): Promise<{ success: boolean; message?: string }> {
  return apiDelete(`/purchase-locations/${locationId}`)
}

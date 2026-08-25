import { apiDelete, apiGet, apiPost, apiPut } from '../shared/http'
import type {
  CreateShoppingListItemPayload,
  ShoppingListDetail,
  ShoppingListHistoryPage,
  ShoppingListItem,
  UpdateShoppingListItemPayload,
} from '../shared/types'

export function fetchShoppingList(listId: number): Promise<ShoppingListDetail> {
  return apiGet<ShoppingListDetail>(`/shopping-lists/${listId}`)
}

export function addShoppingListItem(listId: number, payload: CreateShoppingListItemPayload): Promise<ShoppingListItem> {
  return apiPost(`/shopping-lists/${listId}/items`, payload)
}

export function updateShoppingListItem(
  listId: number,
  itemId: number,
  payload: UpdateShoppingListItemPayload,
): Promise<{ success: boolean; message?: string }> {
  return apiPut(`/shopping-lists/${listId}/items/${itemId}`, payload)
}

export function deleteShoppingListItem(listId: number, itemId: number): Promise<{ success: boolean; message?: string }> {
  return apiDelete(`/shopping-lists/${listId}/items/${itemId}`)
}

export function markShoppingListItemPurchased(
  listId: number,
  itemId: number,
  isPurchased: boolean,
): Promise<{ success: boolean; message?: string }> {
  return apiPut(`/shopping-lists/${listId}/items/${itemId}/purchased`, { is_purchased: isPurchased })
}

export function updateShoppingListStatus(listId: number, status: string): Promise<{ success: boolean; message?: string }> {
  return apiPut(`/shopping-lists/${listId}/status`, { status })
}

export function fetchShoppingListHistory(page = 1, limit = 10): Promise<ShoppingListHistoryPage> {
  return apiGet<ShoppingListHistoryPage>('/shopping-lists/history', { page, limit })
}

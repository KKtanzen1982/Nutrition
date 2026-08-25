import { apiGet, apiPost, apiPut } from '../shared/http'
import type {
  CreateIngredientPayload,
  Ingredient,
  IngredientSearchResult,
  IngredientStock,
  LowStockIngredient,
  PaginatedResult,
  UpdateIngredientPayload,
  UpdateIngredientStockPayload,
} from '../shared/types'

export function listIngredients(
  category: string | undefined,
  page: number,
  limit: number,
): Promise<PaginatedResult<Ingredient>> {
  return apiGet('/ingredients', { category, page, limit })
}

export function searchIngredientsByName(query: string, category?: string): Promise<IngredientSearchResult[]> {
  return apiGet('/ingredients/search', { query, category })
}

export function fetchLowStockIngredients(): Promise<LowStockIngredient[]> {
  return apiGet('/ingredients/low-stock')
}

export function createIngredient(payload: CreateIngredientPayload): Promise<Ingredient> {
  return apiPost('/ingredients', payload)
}

export function updateIngredient(ingredientId: number, payload: UpdateIngredientPayload): Promise<Ingredient> {
  return apiPut(`/ingredients/${ingredientId}`, payload)
}

export function updateIngredientStock(
  ingredientId: number,
  payload: UpdateIngredientStockPayload,
): Promise<IngredientStock> {
  return apiPut(`/ingredients/${ingredientId}/stock`, payload)
}

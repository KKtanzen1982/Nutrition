import { apiDelete, apiGet, apiPost, apiPut } from '../shared/http'
import type {
  CreateRecipePayload,
  CreateRecipeStepPayload,
  NutritionCalculationResult,
  PaginatedResult,
  RecipeDetail,
  RecipeListEntry,
  RecipeSearchResult,
  UpdateRecipePayload,
} from '../shared/types'

export function searchRecipesByName(query: string): Promise<RecipeSearchResult[]> {
  return apiGet<RecipeSearchResult[]>('/recipes/search', { query, search_by: 'name' })
}

export function listRecipes(
  category: string | undefined,
  costLevel: string | undefined,
  page: number,
  limit: number,
): Promise<PaginatedResult<RecipeListEntry>> {
  return apiGet('/recipes', { category, cost_level: costLevel, page, limit })
}

export function fetchRecipe(recipeId: number): Promise<RecipeDetail> {
  return apiGet<RecipeDetail>(`/recipes/${recipeId}`)
}

export function createRecipe(payload: CreateRecipePayload): Promise<RecipeDetail> {
  return apiPost('/recipes', payload)
}

export function updateRecipe(recipeId: number, payload: UpdateRecipePayload): Promise<RecipeDetail> {
  return apiPut(`/recipes/${recipeId}`, payload)
}

export function deleteRecipe(recipeId: number): Promise<void> {
  return apiDelete(`/recipes/${recipeId}`)
}

export function recalculateRecipeNutrition(recipeId: number): Promise<NutritionCalculationResult> {
  return apiPost(`/recipes/${recipeId}/calculate-nutrition`, {})
}

export function addRecipeStepsVersion(
  recipeId: number,
  steps: CreateRecipeStepPayload[],
): Promise<{ success: boolean; recipe_id: number; new_version: number }> {
  return apiPost(`/recipes/${recipeId}/steps`, steps)
}

export function setRecipeStepsAsCurrent(
  recipeId: number,
  version: number,
): Promise<{ success: boolean; recipe_id: number; current_version: number }> {
  return apiPut(`/recipes/${recipeId}/steps/${version}/set-current`, {})
}

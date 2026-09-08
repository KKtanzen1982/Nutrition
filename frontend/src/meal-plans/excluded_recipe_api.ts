import { apiDelete, apiGet, apiPut } from '../shared/http'
import type { ExcludedRecipe } from '../shared/types'

export function fetchExcludedRecipes(): Promise<ExcludedRecipe[]> {
  return apiGet<ExcludedRecipe[]>('/excluded-recipes')
}

export function addExcludedRecipe(recipeId: number): Promise<ExcludedRecipe> {
  return apiPut<ExcludedRecipe>('/excluded-recipes', { recipe_id: recipeId })
}

export function removeExcludedRecipe(id: number): Promise<void> {
  return apiDelete<void>(`/excluded-recipes/${id}`)
}

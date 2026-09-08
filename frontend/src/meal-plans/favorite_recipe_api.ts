import { apiDelete, apiGet, apiPut } from '../shared/http'
import type { FavoriteRecipe } from '../shared/types'

export function fetchFavoriteRecipes(userId: number): Promise<FavoriteRecipe[]> {
  return apiGet<FavoriteRecipe[]>('/favorite-recipes', { user_id: userId })
}

export function addFavoriteRecipe(userId: number, recipeId: number): Promise<FavoriteRecipe> {
  return apiPut<FavoriteRecipe>('/favorite-recipes', { user_id: userId, recipe_id: recipeId })
}

export function removeFavoriteRecipe(id: number): Promise<void> {
  return apiDelete<void>(`/favorite-recipes/${id}`)
}

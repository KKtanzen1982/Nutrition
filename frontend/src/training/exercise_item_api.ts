import { apiGet, apiPost, apiPut } from '../shared/http'
import type {
  CreateExerciseLibraryItemPayload,
  ExerciseItemLibraryEntry,
  ExerciseItemType,
  ExerciseItemVolumePoint,
  UpdateExerciseLibraryItemPayload,
} from '../shared/types'

export function listExerciseItems(
  itemType: ExerciseItemType,
  category?: string,
  userId?: number | null,
  muscleGroup?: string,
): Promise<ExerciseItemLibraryEntry[]> {
  return apiGet<ExerciseItemLibraryEntry[]>('/exercise-items', {
    type: itemType,
    category,
    muscle_group: muscleGroup,
    user_id: userId ?? undefined,
  })
}

export function searchExerciseItems(params: {
  itemType: ExerciseItemType
  q: string
  category?: string
  userId?: number | null
  limit?: number
}): Promise<ExerciseItemLibraryEntry[]> {
  return apiGet<ExerciseItemLibraryEntry[]>('/exercise-items/search', {
    type: params.itemType,
    q: params.q,
    category: params.category,
    user_id: params.userId ?? undefined,
    limit: params.limit,
  })
}

export function createExerciseItem(payload: CreateExerciseLibraryItemPayload): Promise<ExerciseItemLibraryEntry> {
  return apiPost<ExerciseItemLibraryEntry>('/exercise-items', payload)
}

export function getExerciseItem(itemType: ExerciseItemType, itemId: number): Promise<ExerciseItemLibraryEntry> {
  return apiGet<ExerciseItemLibraryEntry>(`/exercise-items/${itemType}/${itemId}`)
}

export function updateExerciseItem(
  itemType: ExerciseItemType,
  itemId: number,
  payload: UpdateExerciseLibraryItemPayload,
): Promise<ExerciseItemLibraryEntry> {
  return apiPut<ExerciseItemLibraryEntry>(`/exercise-items/${itemType}/${itemId}`, payload)
}

export function getExerciseItemHistory(
  itemType: ExerciseItemType,
  itemId: number,
  userId: number,
): Promise<ExerciseItemVolumePoint[]> {
  return apiGet<ExerciseItemVolumePoint[]>(`/exercise-items/${itemType}/${itemId}/history`, { user_id: userId })
}

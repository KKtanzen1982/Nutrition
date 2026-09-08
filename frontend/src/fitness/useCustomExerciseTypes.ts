import { useCustomOptionList } from '../shared/useCustomOptionList'


const STORAGE_KEY = 'nutrition_custom_exercise_types'

export function useCustomExerciseTypes(builtInTypes: string[]) {
  const { customOptions, allOptions, addOption, renameOption, removeOption } = useCustomOptionList(STORAGE_KEY, builtInTypes)
  return {
    customTypes: customOptions,
    allTypes: allOptions,
    addType: addOption,
    renameType: renameOption,
    removeType: removeOption,
  }
}

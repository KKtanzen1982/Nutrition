import { computed, type Ref } from 'vue'
import { useLocalStorage } from './useLocalStorage'

// 同一個 storageKey 共用同一份 ref，讓不同元件實例對自訂選項的新增/刪除即時互相反映，
// 不用等重新整理頁面或重新掛載元件。
const cache = new Map<string, Ref<string[]>>()

function getCustomOptionsRef(storageKey: string): Ref<string[]> {
  let ref = cache.get(storageKey)
  if (!ref) {
    ref = useLocalStorage<string[]>(storageKey, [])
    cache.set(storageKey, ref)
  }
  return ref
}

export function useCustomOptionList(storageKey: string, builtIns: string[] = []) {
  const customOptions = getCustomOptionsRef(storageKey)
  const allOptions = computed(() => [...builtIns, ...customOptions.value])

  function addOption(name: string): string | null {
    const trimmed = name.trim()
    if (!trimmed) return '請輸入名稱'
    if (allOptions.value.includes(trimmed)) return '已經存在這個選項'
    customOptions.value = [...customOptions.value, trimmed]
    return null
  }

  function renameOption(oldName: string, newName: string): string | null {
    const trimmed = newName.trim()
    if (!trimmed) return '請輸入名稱'
    if (trimmed !== oldName && allOptions.value.includes(trimmed)) return '已經存在這個選項'
    customOptions.value = customOptions.value.map((t) => (t === oldName ? trimmed : t))
    return null
  }

  function removeOption(name: string) {
    customOptions.value = customOptions.value.filter((t) => t !== name)
  }

  return { customOptions, allOptions, addOption, renameOption, removeOption }
}

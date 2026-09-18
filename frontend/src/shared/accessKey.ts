const STORAGE_KEY = 'app_access_key'

export function getAccessKey(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

export function setAccessKey(key: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, key)
  } catch {
    // 私密瀏覽模式等 localStorage 不可用的情況：這次連線期間還是能用，只是重整後要重新輸入
  }
}

export function clearAccessKey(): void {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // ignore
  }
}

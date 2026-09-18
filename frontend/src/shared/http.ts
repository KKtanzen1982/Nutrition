import { clearAccessKey, getAccessKey } from './accessKey'

const DEFAULT_BASE_URL = 'http://localhost:8000/api'

export function getBaseUrl(): string {
  const fromEnv = import.meta.env.VITE_API_BASE_URL as string | undefined
  return (fromEnv && fromEnv.trim()) || DEFAULT_BASE_URL
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const accessKey = getAccessKey()
  const res = await fetch(`${getBaseUrl()}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(accessKey ? { 'X-App-Key': accessKey } : {}),
      ...(init?.headers ?? {}),
    },
    ...init,
  })

  if (res.status === 401) {
    // 存的密碼已經失效（後端換了 APP_ACCESS_KEY，或本來就沒存對）：清掉重新整理，讓 AccessGate 重新跳出來
    clearAccessKey()
    window.location.reload()
    throw new ApiError(401, '存取密碼已失效，請重新輸入')
  }

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new ApiError(res.status, text || `請求失敗（HTTP ${res.status}）`)
  }

  if (res.status === 204) {
    return undefined as T
  }

  return (await res.json()) as T
}

export function apiGet<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const entries = Object.entries(params ?? {}).filter(([, v]) => v !== undefined && v !== '')
  const query = entries.length
    ? `?${entries.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`).join('&')}`
    : ''
  return request<T>(`${path}${query}`)
}

export function apiPut<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'PUT', body: JSON.stringify(body) })
}

export function apiPost<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body: JSON.stringify(body) })
}

export function apiDelete<T>(path: string): Promise<T> {
  return request<T>(path, { method: 'DELETE' })
}

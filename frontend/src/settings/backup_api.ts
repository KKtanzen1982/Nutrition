import { getBaseUrl } from '../shared/http'

export function backupExportUrl(): string {
  return `${getBaseUrl()}/backup/export`
}

export async function importBackup(file: File): Promise<{ success: boolean; message: string }> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${getBaseUrl()}/backup/import`, { method: 'POST', body: formData })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `匯入失敗（HTTP ${res.status}）`)
  }
  return res.json()
}

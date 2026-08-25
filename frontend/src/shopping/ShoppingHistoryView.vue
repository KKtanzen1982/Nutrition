<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { fetchShoppingListHistory } from './shopping_list_api'
import { useHouseholdConfig } from '../shared/useHouseholdConfig'
import type { ShoppingListHistoryEntry } from '../shared/types'

const LIMIT = 10

const router = useRouter()
const { setCurrentShoppingListId } = useHouseholdConfig()

const page = ref(1)
const total = ref(0)
const entries = ref<ShoppingListHistoryEntry[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

async function load(p: number) {
  loading.value = true
  error.value = null
  try {
    const result = await fetchShoppingListHistory(p, LIMIT)
    entries.value = result.history
    total.value = result.total
    page.value = p
  } catch (e) {
    error.value = e instanceof Error ? e.message : '讀取採購歷史失敗'
  } finally {
    loading.value = false
  }
}
load(1)

const totalPages = () => Math.max(1, Math.ceil(total.value / LIMIT))

function formatDateTime(iso: string): string {
  return iso.replace('T', ' ').slice(0, 16)
}

// item_changes / status_log 是後端存的不透明字串（可能是 JSON，也可能不是），
// 這裡只嘗試美化成 JSON，解析失敗就照原樣顯示，不對格式做任何假設。
function prettyPrint(raw: string | null): string | null {
  if (!raw) return null
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
}

function viewList(listId: number) {
  setCurrentShoppingListId(listId)
  router.push('/shopping-list')
}
</script>

<template>
  <div class="mx-auto max-w-2xl px-4 py-8">
    <h1 class="font-serif text-2xl text-ink">採購歷史</h1>
    <p class="mt-1 text-sm text-tea">已歸檔的購物清單快照（`GET /shopping-lists/history`）</p>

    <p v-if="loading" class="mt-6 text-center text-sm text-tea">載入中…</p>
    <p v-else-if="error" class="mt-6 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ error }}</p>
    <p v-else-if="entries.length === 0" class="mt-6 text-center text-sm text-tea">尚無歸檔紀錄</p>

    <ul v-else class="mt-4 space-y-3">
      <li v-for="entry in entries" :key="entry.id" class="rounded-2xl border border-ink/10 bg-surface p-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p class="text-sm text-ink">清單 #{{ entry.shopping_list_id }}</p>
            <p class="text-xs text-tea">歸檔於 {{ formatDateTime(entry.archived_at) }}</p>
          </div>
          <button
            type="button"
            class="shrink-0 rounded-full border border-ink/15 px-3 py-1.5 text-xs font-semibold text-ink hover:bg-bg"
            @click="viewList(entry.shopping_list_id)"
          >
            查看這份清單
          </button>
        </div>

        <p v-if="entry.notes" class="mt-2 text-sm text-tea">{{ entry.notes }}</p>

        <details v-if="entry.status_log" class="mt-2">
          <summary class="cursor-pointer text-xs font-semibold uppercase tracking-wide text-muted">狀態紀錄</summary>
          <pre class="mt-1 overflow-x-auto rounded-lg bg-bg p-2 text-xs text-ink">{{ prettyPrint(entry.status_log) }}</pre>
        </details>

        <details v-if="entry.item_changes" class="mt-2">
          <summary class="cursor-pointer text-xs font-semibold uppercase tracking-wide text-muted">項目異動</summary>
          <pre class="mt-1 overflow-x-auto rounded-lg bg-bg p-2 text-xs text-ink">{{ prettyPrint(entry.item_changes) }}</pre>
        </details>
      </li>
    </ul>

    <div v-if="!loading && !error && total > LIMIT" class="mt-4 flex items-center justify-center gap-3">
      <button
        type="button"
        class="rounded-full border border-ink/15 px-3 py-1.5 text-xs font-semibold text-ink hover:bg-bg disabled:opacity-40"
        :disabled="page <= 1"
        @click="load(page - 1)"
      >
        上一頁
      </button>
      <span class="text-xs text-tea">{{ page }} / {{ totalPages() }}</span>
      <button
        type="button"
        class="rounded-full border border-ink/15 px-3 py-1.5 text-xs font-semibold text-ink hover:bg-bg disabled:opacity-40"
        :disabled="page >= totalPages()"
        @click="load(page + 1)"
      >
        下一頁
      </button>
    </div>
  </div>
</template>

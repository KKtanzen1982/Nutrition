<script setup lang="ts">
import { computed, reactive, ref, watch, watchEffect } from 'vue'
import { fetchUserGoalHistory } from '../users/users_api'
import {
  createWeightRecord,
  deleteWeightRecord,
  fetchWeightRecords,
  updateWeightRecord,
} from './weight_api'
import DateRangeButton from '../trends/DateRangeButton.vue'
import { useConfirmDialog } from '../shared/useConfirmDialog'
import { useHouseholdConfig } from '../shared/useHouseholdConfig'
import { daysAgo, toISODate, today } from '../shared/date_utils'
import type { WeightRecord } from '../shared/types'

const HISTORY_FETCH_DAYS = 365

const { activeUser } = useHouseholdConfig()
const { confirmDialog } = useConfirmDialog()

const todayStr = toISODate(today())
const selectedDate = ref(todayStr)

const loading = ref(true)
const error = ref<string | null>(null)
const records = ref<WeightRecord[]>([])
const targetWeight = ref<number | null>(null)

const saving = ref(false)
const saveError = ref<string | null>(null)

const form = reactive<{ weight_kg: number | null; body_fat_percent: number | null; notes: string }>({
  weight_kg: null,
  body_fat_percent: null,
  notes: '',
})
const showExtra = ref(false)

async function load(userId: number) {
  loading.value = true
  error.value = null
  try {
    const [weightRecords, goalHistory] = await Promise.all([
      fetchWeightRecords(userId, daysAgo(HISTORY_FETCH_DAYS), today()),
      fetchUserGoalHistory(userId),
    ])
    records.value = weightRecords
    const latestWeightGoal = goalHistory
      .filter((g) => g.goal_type === 'weight')
      .sort((a, b) => b.set_date.localeCompare(a.set_date))[0]
    targetWeight.value = latestWeightGoal?.target_value ?? null
  } catch (e) {
    error.value = e instanceof Error ? e.message : '讀取體重資料失敗'
  } finally {
    loading.value = false
  }
}

watchEffect(() => {
  if (activeUser.value) load(activeUser.value.id)
})

const sortedDesc = computed(() => [...records.value].sort((a, b) => b.date.localeCompare(a.date)))
const sortedAsc = computed(() => [...records.value].sort((a, b) => a.date.localeCompare(b.date)))

const existingRecordForDate = computed(() => records.value.find((r) => r.date === selectedDate.value) ?? null)
const isUpdating = computed(() => existingRecordForDate.value !== null)

const latestWeightHint = computed(() => {
  const before = sortedDesc.value.find((r) => r.date < selectedDate.value)
  return before ? `上次 ${before.weight_kg}kg` : '例如 58.4'
})

const lastBodyFatDate = computed(() => {
  const withBodyFat = sortedDesc.value.filter((r) => r.body_fat_percent !== null)
  return withBodyFat[0]?.date ?? null
})
const daysSinceLastBodyFat = computed(() => {
  if (!lastBodyFatDate.value) return null
  const diffMs = new Date(selectedDate.value).getTime() - new Date(lastBodyFatDate.value).getTime()
  return Math.round(diffMs / 86400000)
})
const showExtraNudge = computed(() => !isUpdating.value && (daysSinceLastBodyFat.value === null || daysSinceLastBodyFat.value >= 7))

watch(
  [selectedDate, records],
  () => {
    const existing = existingRecordForDate.value
    form.weight_kg = existing?.weight_kg ?? null
    form.body_fat_percent = existing?.body_fat_percent ?? null
    form.notes = existing?.notes ?? ''
    showExtra.value = Boolean(existing?.body_fat_percent !== null && existing?.body_fat_percent !== undefined) ||
      Boolean(existing?.notes) ||
      showExtraNudge.value
  },
  { immediate: true },
)

async function submit() {
  if (!activeUser.value || form.weight_kg === null) return
  saving.value = true
  saveError.value = null
  try {
    if (existingRecordForDate.value) {
      await updateWeightRecord(existingRecordForDate.value.id, {
        weight_kg: form.weight_kg,
        body_fat_percent: form.body_fat_percent,
        notes: form.notes || null,
      })
    } else {
      await createWeightRecord({
        user_id: activeUser.value.id,
        date: selectedDate.value,
        weight_kg: form.weight_kg,
        body_fat_percent: form.body_fat_percent,
        notes: form.notes || null,
      })
    }
    await load(activeUser.value.id)
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : '儲存失敗，請稍後再試'
  } finally {
    saving.value = false
  }
}

// ---- 歷史紀錄：編輯模式（多選 + 區間篩選），一般瀏覽時不可點選/刪除 ----

const historyFrom = ref(toISODate(daysAgo(90)))
const historyTo = ref(todayStr)

const filteredHistory = computed(() =>
  sortedDesc.value.filter((r) => r.date >= historyFrom.value && r.date <= historyTo.value),
)

const editMode = ref(false)
const selectedIds = ref<Set<number>>(new Set())
const bulkDeleting = ref(false)
const bulkDeleteError = ref<string | null>(null)

function toggleEditMode() {
  editMode.value = !editMode.value
  selectedIds.value = new Set()
  bulkDeleteError.value = null
}

function toggleSelect(id: number) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}

const allVisibleSelected = computed(
  () => filteredHistory.value.length > 0 && filteredHistory.value.every((r) => selectedIds.value.has(r.id)),
)

function toggleSelectAll() {
  selectedIds.value = allVisibleSelected.value
    ? new Set()
    : new Set(filteredHistory.value.map((r) => r.id))
}

function onRowClick(record: WeightRecord) {
  if (!editMode.value) return
  selectedDate.value = record.date
}

async function bulkDelete() {
  if (!activeUser.value || selectedIds.value.size === 0) return
  if (!(await confirmDialog(`刪除選取的 ${selectedIds.value.size} 筆體重紀錄？`))) return
  bulkDeleting.value = true
  bulkDeleteError.value = null
  try {
    await Promise.all([...selectedIds.value].map((id) => deleteWeightRecord(id)))
    selectedIds.value = new Set()
    await load(activeUser.value.id)
  } catch (e) {
    bulkDeleteError.value = e instanceof Error ? e.message : '刪除失敗，請稍後再試'
  } finally {
    bulkDeleting.value = false
  }
}

const latest = computed(() => sortedAsc.value[sortedAsc.value.length - 1] ?? null)
const gapToTarget = computed(() => {
  if (!latest.value || targetWeight.value === null) return null
  return Number((latest.value.weight_kg - targetWeight.value).toFixed(1))
})
</script>

<template>
  <div class="mx-auto max-w-2xl px-4 py-8">
    <div v-if="!activeUser" class="rounded-2xl border border-dashed border-ink/20 p-6 text-center text-tea">
      請先在上方完成使用者設定
    </div>

    <template v-else>
      <section class="rounded-2xl border border-ink/10 bg-surface p-6">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1.5">
            <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-ink" aria-hidden="true" />
            <h1 class="border-b-[1.5px] border-accent pb-1 text-[11.5px] font-semibold uppercase tracking-wide text-muted">
              {{ isUpdating ? '更新這天的紀錄' : '新增體重紀錄' }}
            </h1>
          </div>
          <input
            v-model="selectedDate"
            type="date"
            :max="todayStr"
            class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink"
          />
        </div>

        <p v-if="gapToTarget !== null" class="mt-3 text-xs text-tea">
          目前 {{ latest?.weight_kg }}kg · 距目標 {{ targetWeight }}kg 還差 {{ Math.abs(gapToTarget) }}kg
        </p>

        <div class="mt-4">
          <label class="mb-1 block text-xs text-tea">體重 (kg)</label>
          <input
            v-model.number="form.weight_kg"
            type="number"
            step="0.1"
            min="1"
            :placeholder="latestWeightHint"
            class="w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-2xl font-semibold text-ink"
          />
        </div>

        <button type="button" class="mt-3 text-xs font-semibold text-tea hover:text-ink" @click="showExtra = !showExtra">
          {{ showExtra ? '− 收起體脂率／備註' : '+ 體脂率／備註（建議每週記一次）' }}
        </button>

        <p v-if="showExtraNudge" class="mt-2 text-xs text-accent">
          {{ lastBodyFatDate ? `已經 ${daysSinceLastBodyFat} 天沒記體脂率了` : '還沒記錄過體脂率' }}
        </p>

        <div v-if="showExtra" class="mt-3 grid grid-cols-2 gap-3">
          <div>
            <label class="mb-1 block text-xs text-tea">體脂率 (%)</label>
            <input
              v-model.number="form.body_fat_percent"
              type="number"
              step="0.1"
              min="0"
              max="100"
              class="w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
            />
          </div>
          <div>
            <label class="mb-1 block text-xs text-tea">備註</label>
            <input v-model="form.notes" type="text" class="w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
          </div>
        </div>

        <p v-if="saveError" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ saveError }}</p>

        <button
          type="button"
          class="mt-4 w-full rounded-full bg-accent py-2.5 text-sm font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
          :disabled="saving || form.weight_kg === null"
          @click="submit"
        >
          {{ saving ? '儲存中…' : isUpdating ? '更新紀錄' : '新增紀錄' }}
        </button>
      </section>

      <section class="mt-8">
        <div class="flex items-center justify-between">
          <h2 class="font-serif text-xl text-ink">歷史紀錄</h2>
          <button type="button" class="text-xs font-semibold text-accent hover:text-accent-bright" @click="toggleEditMode">
            {{ editMode ? '完成' : '編輯' }}
          </button>
        </div>

        <div class="mt-3">
          <DateRangeButton v-model:from="historyFrom" v-model:to="historyTo" :max="todayStr" />
        </div>

        <div v-if="editMode && filteredHistory.length" class="mt-3 flex items-center justify-between rounded-lg bg-accent-tint px-3 py-2">
          <label class="flex items-center gap-2 text-xs text-ink">
            <input type="checkbox" :checked="allVisibleSelected" @change="toggleSelectAll" />
            全選（{{ selectedIds.size }} / {{ filteredHistory.length }}）
          </label>
          <button
            type="button"
            class="rounded-full border border-alert px-3 py-1 text-xs font-semibold text-alert hover:bg-alert/10 disabled:opacity-50"
            :disabled="selectedIds.size === 0 || bulkDeleting"
            @click="bulkDelete"
          >
            {{ bulkDeleting ? '刪除中…' : `刪除選取（${selectedIds.size}）` }}
          </button>
        </div>
        <p v-if="bulkDeleteError" class="mt-2 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ bulkDeleteError }}</p>

        <p v-if="loading" class="mt-3 text-sm text-tea">載入中…</p>
        <p v-else-if="error" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ error }}</p>
        <p v-else-if="filteredHistory.length === 0" class="mt-3 text-sm text-tea">尚無符合條件的紀錄</p>
        <ul v-else class="mt-3 divide-y divide-ink/10">
          <li v-for="r in filteredHistory" :key="r.id" class="flex items-center justify-between py-3">
            <div class="flex items-center gap-3">
              <input
                v-if="editMode"
                type="checkbox"
                :checked="selectedIds.has(r.id)"
                @change="toggleSelect(r.id)"
              />
              <button type="button" class="text-left" :class="{ 'cursor-default': !editMode }" @click="onRowClick(r)">
                <p class="text-sm text-ink">{{ r.date }}</p>
                <p v-if="r.body_fat_percent !== null" class="text-xs text-tea">體脂 {{ r.body_fat_percent }}%</p>
              </button>
            </div>
            <span class="font-serif text-lg text-ink">{{ r.weight_kg }}<small class="text-sm text-tea">kg</small></span>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

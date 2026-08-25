<script setup lang="ts">
import { computed, reactive, ref, watch, watchEffect } from 'vue'
import { fetchUserGoalHistory } from '../users/users_api'
import {
  createWeightRecord,
  deleteWeightRecord,
  fetchWeightRecords,
  updateWeightRecord,
} from './weight_api'
import { useConfirmDialog } from '../shared/useConfirmDialog'
import { useHouseholdConfig } from '../shared/useHouseholdConfig'
import { daysAgo, toISODate, today } from '../shared/date_utils'
import type { WeightRecord } from '../shared/types'

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
      fetchWeightRecords(userId, daysAgo(90), today()),
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

async function remove(record: WeightRecord) {
  if (!activeUser.value) return
  if (!(await confirmDialog(`刪除 ${record.date} 的體重紀錄？`))) return
  saveError.value = null
  try {
    await deleteWeightRecord(record.id)
    await load(activeUser.value.id)
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : '刪除失敗，請稍後再試'
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
        <h2 class="font-serif text-xl text-ink">歷史紀錄</h2>
        <p v-if="loading" class="mt-3 text-sm text-tea">載入中…</p>
        <p v-else-if="error" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ error }}</p>
        <p v-else-if="sortedDesc.length === 0" class="mt-3 text-sm text-tea">尚無紀錄</p>
        <ul v-else class="mt-3 divide-y divide-ink/10">
          <li v-for="r in sortedDesc" :key="r.id" class="flex items-center justify-between py-3">
            <button type="button" class="text-left" @click="selectedDate = r.date">
              <p class="text-sm text-ink">{{ r.date }}</p>
              <p v-if="r.body_fat_percent !== null" class="text-xs text-tea">體脂 {{ r.body_fat_percent }}%</p>
            </button>
            <div class="flex items-center gap-3">
              <span class="font-serif text-lg text-ink">{{ r.weight_kg }}<small class="text-sm text-tea">kg</small></span>
              <button type="button" class="text-xs text-tea hover:text-alert" @click="remove(r)">刪除</button>
            </div>
          </li>
        </ul>
      </section>
    </template>
  </div>
</template>

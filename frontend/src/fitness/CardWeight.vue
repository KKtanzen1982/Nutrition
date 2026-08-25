<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import CardShell from '../shared/CardShell.vue'
import TrendChart from '../trends/TrendChart.vue'
import { fetchWeightRecords } from './weight_api'
import { fetchUserGoalHistory } from '../users/users_api'
import { daysAgo, startOfWeekMonday, today } from '../shared/date_utils'
import type { WeightRecord } from '../shared/types'

const props = defineProps<{ userId: number }>()

const loading = ref(true)
const error = ref<string | null>(null)
const records = ref<WeightRecord[]>([])
const targetWeight = ref<number | null>(null)

async function load(userId: number) {
  loading.value = true
  error.value = null
  try {
    const [weightRecords, goalHistory] = await Promise.all([
      fetchWeightRecords(userId, daysAgo(30), today()),
      fetchUserGoalHistory(userId),
    ])
    records.value = [...weightRecords].sort((a, b) => a.date.localeCompare(b.date))
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
  load(props.userId)
})

const latest = computed(() => records.value[records.value.length - 1] ?? null)
const previous = computed(() => (records.value.length > 1 ? records.value[records.value.length - 2] : null))
const trend = computed(() => {
  if (!latest.value || !previous.value) return null
  return Number((latest.value.weight_kg - previous.value.weight_kg).toFixed(1))
})
const gapToTarget = computed(() => {
  if (!latest.value || targetWeight.value === null) return null
  return Number((latest.value.weight_kg - targetWeight.value).toFixed(1))
})

const weekPoints = computed(() => {
  const monday = startOfWeekMonday(today())
  const days: { label: string; value: number | null }[] = []
  for (let i = 0; i < 7; i++) {
    const d = new Date(monday)
    d.setDate(d.getDate() + i)
    const iso = d.toISOString().slice(0, 10)
    const record = records.value.find((r) => r.date === iso)
    days.push({ label: iso.slice(5), value: record ? record.weight_kg : null })
  }
  return days
})
const hasWeekData = computed(() => weekPoints.value.some((p) => p.value !== null))
</script>

<template>
  <CardShell
    title="體重"
    to="/weight"
    :loading="loading"
    :error="error"
    :is-empty="!loading && !error && !latest"
    empty-text="尚無體重紀錄"
  >
    <div v-if="latest">
      <p class="font-serif text-4xl leading-none text-ink">
        {{ latest.weight_kg }}<small class="text-base text-tea">kg</small>
      </p>
      <p class="mt-2 text-xs text-tea">
        <span v-if="trend !== null">{{ trend > 0 ? '↑' : trend < 0 ? '↓' : '→' }} {{ Math.abs(trend) }}kg 本週</span>
        <span v-if="trend !== null && gapToTarget !== null"> · </span>
        <span v-if="gapToTarget !== null">距目標 {{ targetWeight }}kg 還差 {{ Math.abs(gapToTarget) }}kg</span>
      </p>
      <TrendChart
        v-if="hasWeekData"
        class="mt-3"
        :points="weekPoints"
        :height="64"
        :filled="true"
        compact
      />
    </div>
  </CardShell>
</template>

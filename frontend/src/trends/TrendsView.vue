<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import CardShell from '../shared/CardShell.vue'
import TrendChart from './TrendChart.vue'
import UserSwitcher from '../shared/UserSwitcher.vue'
import { fetchUserGoalHistory } from '../users/users_api'
import { fetchWeightRecords } from '../fitness/weight_api'
import { fetchDailySteps, fetchExerciseSessions } from '../fitness/exercise_api'
import { daysAgo, startOfWeekMonday, today, toISODate } from '../shared/date_utils'
import { useHouseholdConfig } from '../shared/useHouseholdConfig'
import type { DailyStepsRecord, ExerciseSession, WeightRecord } from '../shared/types'

const RANGE_OPTIONS = [
  { days: 30, label: '30 天' },
  { days: 90, label: '90 天' },
  { days: 180, label: '180 天' },
]

const { activeUser } = useHouseholdConfig()

const rangeDays = ref(90)

const loading = ref(true)
const error = ref<string | null>(null)
const weightRecords = ref<WeightRecord[]>([])
const targetWeight = ref<number | null>(null)
const exerciseSessions = ref<ExerciseSession[]>([])
const stepsRecords = ref<DailyStepsRecord[]>([])

function shortDate(iso: string): string {
  return iso.slice(5).replace('-', '/')
}

async function load(userId: number, days: number) {
  loading.value = true
  error.value = null
  try {
    const start = daysAgo(days)
    const end = today()
    const [wRecords, goalHistory, sessions, steps] = await Promise.all([
      fetchWeightRecords(userId, start, end),
      fetchUserGoalHistory(userId),
      fetchExerciseSessions(userId, start, end),
      fetchDailySteps(userId, start, end),
    ])
    weightRecords.value = [...wRecords].sort((a, b) => a.date.localeCompare(b.date))
    const latestWeightGoal = goalHistory
      .filter((g) => g.goal_type === 'weight')
      .sort((a, b) => b.set_date.localeCompare(a.set_date))[0]
    targetWeight.value = latestWeightGoal?.target_value ?? null
    exerciseSessions.value = sessions
    stepsRecords.value = steps
  } catch (e) {
    error.value = e instanceof Error ? e.message : '讀取趨勢資料失敗'
  } finally {
    loading.value = false
  }
}

watchEffect(() => {
  if (activeUser.value) load(activeUser.value.id, rangeDays.value)
})

const weightPoints = computed(() => weightRecords.value.map((r) => ({ label: shortDate(r.date), value: r.weight_kg })))
const hasBodyFat = computed(() => weightRecords.value.some((r) => r.body_fat_percent !== null))
const bodyFatPoints = computed(() =>
  weightRecords.value.map((r) => ({ label: shortDate(r.date), value: r.body_fat_percent })),
)

const weekStarts = computed(() => {
  const result: Date[] = []
  let cursor = startOfWeekMonday(daysAgo(rangeDays.value))
  const lastWeek = startOfWeekMonday(today())
  while (cursor <= lastWeek) {
    result.push(new Date(cursor))
    cursor = new Date(cursor)
    cursor.setDate(cursor.getDate() + 7)
  }
  return result
})

function weekRangeIso(weekStart: Date): [string, string] {
  const weekEnd = new Date(weekStart)
  weekEnd.setDate(weekEnd.getDate() + 6)
  return [toISODate(weekStart), toISODate(weekEnd)]
}

const weeklyMinutesPoints = computed(() =>
  weekStarts.value.map((ws) => {
    const [start, end] = weekRangeIso(ws)
    const minutes = exerciseSessions.value
      .filter((s) => s.date >= start && s.date <= end)
      .reduce((sum, s) => sum + (s.duration_min ?? 0), 0)
    return { label: shortDate(start), value: minutes }
  }),
)

const weeklySessionsPoints = computed(() =>
  weekStarts.value.map((ws) => {
    const [start, end] = weekRangeIso(ws)
    const count = exerciseSessions.value.filter((s) => s.date >= start && s.date <= end).length
    return { label: shortDate(start), value: count }
  }),
)

const weeklyStepsPoints = computed(() =>
  weekStarts.value.map((ws) => {
    const [start, end] = weekRangeIso(ws)
    const steps = stepsRecords.value
      .filter((s) => s.date >= start && s.date <= end)
      .reduce((sum, s) => sum + s.step_count, 0)
    return { label: shortDate(start), value: steps }
  }),
)

const hasExerciseData = computed(() => exerciseSessions.value.length > 0)
const hasStepsData = computed(() => stepsRecords.value.length > 0)
</script>

<template>
  <div class="mx-auto max-w-3xl px-4 py-8">
    <div v-if="!activeUser" class="rounded-2xl border border-dashed border-ink/20 p-6 text-center text-tea">
      請先在上方完成使用者設定
    </div>

    <template v-else>
      <header class="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 class="font-serif text-2xl text-ink">趨勢圖表</h1>
          <p class="text-sm text-tea">目前檢視：{{ activeUser.name }}</p>
        </div>
        <div class="flex gap-1">
          <button
            v-for="opt in RANGE_OPTIONS"
            :key="opt.days"
            type="button"
            class="rounded-full px-3 py-1.5 text-xs font-semibold"
            :class="rangeDays === opt.days ? 'bg-accent text-on-accent' : 'bg-accent-tint text-tea hover:text-ink'"
            @click="rangeDays = opt.days"
          >
            {{ opt.label }}
          </button>
        </div>
      </header>

      <div class="mb-6">
        <UserSwitcher />
      </div>

      <div class="space-y-4">
        <CardShell
          title="體重趨勢"
          :loading="loading"
          :error="error"
          :is-empty="!loading && !error && weightRecords.length === 0"
          empty-text="這段期間尚無體重紀錄"
        >
          <TrendChart
            :points="weightPoints"
            unit="kg"
            :reference-value="targetWeight"
            reference-label="目標"
          />
        </CardShell>

        <CardShell
          v-if="!loading && !error && hasBodyFat"
          title="體脂率趨勢"
          :loading="loading"
          :error="error"
        >
          <TrendChart :points="bodyFatPoints" unit="%" variant="secondary" />
        </CardShell>

        <CardShell
          title="每週運動"
          :loading="loading"
          :error="error"
          :is-empty="!loading && !error && !hasExerciseData"
          empty-text="這段期間尚無運動紀錄"
        >
          <p class="mb-1 text-xs font-semibold uppercase tracking-wide text-muted">次數</p>
          <TrendChart :points="weeklySessionsPoints" mode="bar" unit="次" :decimals="0" />
          <p class="mb-1 mt-4 text-xs font-semibold uppercase tracking-wide text-muted">分鐘數</p>
          <TrendChart :points="weeklyMinutesPoints" mode="bar" unit="分" :decimals="0" variant="secondary" />
        </CardShell>

        <CardShell
          title="每週步數"
          :loading="loading"
          :error="error"
          :is-empty="!loading && !error && !hasStepsData"
          empty-text="這段期間尚無步數紀錄"
        >
          <TrendChart :points="weeklyStepsPoints" mode="bar" unit="步" :decimals="0" />
        </CardShell>
      </div>
    </template>
  </div>
</template>

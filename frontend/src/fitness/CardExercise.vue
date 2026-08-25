<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import CardShell from '../shared/CardShell.vue'
import TrendChart from '../trends/TrendChart.vue'
import { fetchDailySteps, fetchExerciseSessions } from './exercise_api'
import { startOfWeekMonday, today } from '../shared/date_utils'
import type { DailyStepsRecord, ExerciseSession } from '../shared/types'

const props = defineProps<{ userId: number }>()

const loading = ref(true)
const error = ref<string | null>(null)
const sessions = ref<ExerciseSession[]>([])
const steps = ref<DailyStepsRecord[]>([])

async function load(userId: number) {
  loading.value = true
  error.value = null
  try {
    const weekStart = startOfWeekMonday(today())
    const [sessionList, stepList] = await Promise.all([
      fetchExerciseSessions(userId, weekStart, today()),
      fetchDailySteps(userId, weekStart, today()),
    ])
    sessions.value = sessionList
    steps.value = stepList
  } catch (e) {
    error.value = e instanceof Error ? e.message : '讀取運動資料失敗'
  } finally {
    loading.value = false
  }
}

watchEffect(() => {
  load(props.userId)
})

const totalSessions = computed(() => sessions.value.length)
const totalMinutes = computed(() => sessions.value.reduce((sum, s) => sum + (s.duration_min ?? 0), 0))
const totalSteps = computed(() => steps.value.reduce((sum, s) => sum + s.step_count, 0))
const byType = computed(() => {
  const counts = new Map<string, number>()
  for (const s of sessions.value) {
    counts.set(s.exercise_type, (counts.get(s.exercise_type) ?? 0) + 1)
  }
  return [...counts.entries()]
})

const weekStepPoints = computed(() => {
  const monday = startOfWeekMonday(today())
  const days: { label: string; value: number | null }[] = []
  for (let i = 0; i < 7; i++) {
    const d = new Date(monday)
    d.setDate(d.getDate() + i)
    const iso = d.toISOString().slice(0, 10)
    const record = steps.value.find((s) => s.date === iso)
    days.push({ label: iso.slice(5), value: record ? record.step_count : null })
  }
  return days
})
const hasWeekStepData = computed(() => weekStepPoints.value.some((p) => p.value !== null))
</script>

<template>
  <CardShell
    title="本週運動"
    to="/exercise"
    :loading="loading"
    :error="error"
    :is-empty="!loading && !error && totalSessions === 0 && totalSteps === 0"
    empty-text="本週尚無運動紀錄"
  >
    <p class="font-serif text-4xl leading-none text-ink">
      {{ totalSessions }}<small class="text-base text-tea">次</small>
    </p>
    <p class="mt-2 text-xs text-tea">{{ totalMinutes }} 分鐘 · {{ totalSteps.toLocaleString() }} 步</p>
    <div v-if="byType.length" class="mt-3 flex flex-wrap gap-1.5">
      <span v-for="[type, count] in byType" :key="type" class="rounded-full bg-accent-tint px-2.5 py-1 text-xs text-ink">
        {{ type }} × {{ count }}
      </span>
    </div>
    <TrendChart
      v-if="hasWeekStepData"
      class="mt-3"
      :points="weekStepPoints"
      :height="64"
      :filled="true"
      compact
    />
  </CardShell>
</template>

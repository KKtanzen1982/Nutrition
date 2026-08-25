<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import CardShell from '../shared/CardShell.vue'
import { fetchMealPlan } from './meal_plan_api'
import { toISODate, today } from '../shared/date_utils'
import type { MealPlanDetail } from '../shared/types'

const MEAL_SLOTS_PER_DAY = 4
const MEAL_TYPE_LABELS: Record<string, string> = {
  breakfast: '早餐',
  lunch: '午餐',
  afternoon_snack: '下午茶',
  dinner: '晚餐',
}

const props = defineProps<{ planId: number | null; userId: number }>()

const loading = ref(false)
const error = ref<string | null>(null)
const plan = ref<MealPlanDetail | null>(null)

async function load(planId: number | null) {
  if (planId === null) {
    plan.value = null
    return
  }
  loading.value = true
  error.value = null
  try {
    plan.value = await fetchMealPlan(planId)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '讀取本週菜單失敗'
  } finally {
    loading.value = false
  }
}

watchEffect(() => {
  load(props.planId)
})

const todayMeals = computed(() => {
  if (!plan.value) return []
  const todayStr = toISODate(today())
  const day = plan.value.days.find((d) => d.date === todayStr)
  return day?.meals.filter((m) => m.assigned_user_id === props.userId) ?? []
})

// 午餐/晚餐每個分類槽位（主食/肉/菜）各佔一筆 DailyMealDetail，所以用「已安排的餐別種類數」而非筆數來對比 4 個餐別
const todayMealTypeCount = computed(() => new Set(todayMeals.value.map((m) => m.meal_type)).size)

const progressPct = computed(() => Math.min(100, Math.round((todayMealTypeCount.value / MEAL_SLOTS_PER_DAY) * 100)))
</script>

<template>
  <CardShell
    title="今日菜單"
    to="/meal-plan"
    :loading="loading"
    :error="error"
    :is-empty="props.planId === null || (!loading && !error && todayMeals.length === 0)"
    :empty-text="props.planId === null ? '尚未設定本週推薦，到「週推薦」頁生成一份' : '今天沒有安排菜色'"
  >
    <p class="font-serif text-4xl leading-none text-ink">
      {{ todayMealTypeCount }}<small class="text-base text-tea">/{{ MEAL_SLOTS_PER_DAY }} 餐</small>
    </p>
    <p class="mt-2 text-xs text-tea">
      {{ todayMeals.map((m) => `${MEAL_TYPE_LABELS[m.meal_type] ?? m.meal_type}．${m.recipe_name}`).join('、') || '尚未安排' }}
    </p>
    <div class="mt-3 h-[3px] overflow-hidden rounded-full bg-accent-tint">
      <span class="block h-full rounded-full bg-accent" :style="{ width: `${progressPct}%` }" />
    </div>
  </CardShell>
</template>

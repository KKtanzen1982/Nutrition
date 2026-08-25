<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import {
  adjustServingWeight,
  confirmMealPlan,
  fetchMealPlan,
  generateMealPlan,
  regenerateDay,
  replaceMeal,
  searchAndReplaceMeal,
} from './meal_plan_api'
import { searchRecipesByName } from '../recipes/recipe_api'
import { useHouseholdConfig } from '../shared/useHouseholdConfig'
import { startOfWeekMonday, toISODate, today } from '../shared/date_utils'
import type { DayMeals, MealDetail, MealPlanDetail, RecipeSearchResult } from '../shared/types'

const MEAL_TYPE_LABELS: Record<string, string> = {
  breakfast: '早餐',
  lunch: '午餐',
  afternoon_snack: '下午茶',
  dinner: '晚餐',
}
const WEEKDAY_LABELS = ['週日', '週一', '週二', '週三', '週四', '週五', '週六']

const { config, setCurrentMealPlanId, setCurrentShoppingListId } = useHouseholdConfig()
const users = computed(() => config.value.users)
const hasTwoUsers = computed(() => users.value.length >= 2)
const userA = computed(() => users.value[0] ?? null)
const userB = computed(() => users.value[1] ?? null)

function userName(userId: number): string {
  return users.value.find((u) => u.id === userId)?.name ?? `使用者 ${userId}`
}

const plan = ref<MealPlanDetail | null>(null)
const loadingPlan = ref(false)
const planError = ref<string | null>(null)

async function refetchPlan(planId: number) {
  loadingPlan.value = true
  planError.value = null
  try {
    plan.value = await fetchMealPlan(planId)
  } catch (e) {
    planError.value = e instanceof Error ? e.message : '讀取週推薦失敗'
  } finally {
    loadingPlan.value = false
  }
}

watchEffect(() => {
  const id = config.value.currentMealPlanId
  if (id !== null) refetchPlan(id)
  else plan.value = null
})

const weekStart = ref(toISODate(startOfWeekMonday(today())))
const generating = ref(false)
const generateError = ref<string | null>(null)

async function submitGenerate() {
  if (!userA.value || !userB.value) return
  generating.value = true
  generateError.value = null
  try {
    const result = await generateMealPlan({
      week_start_date: weekStart.value,
      user_id_a: userA.value.id,
      user_id_b: userB.value.id,
    })
    plan.value = result
    setCurrentMealPlanId(result.id)
  } catch (e) {
    generateError.value = e instanceof Error ? e.message : '推薦生成失敗，請稍後再試'
  } finally {
    generating.value = false
  }
}

const regeneratingDay = ref<string | null>(null)
const adjustError = ref<string | null>(null)

async function submitRegenerateDay(mealDate: string) {
  if (!plan.value?.id) return
  regeneratingDay.value = mealDate
  adjustError.value = null
  try {
    plan.value = await regenerateDay(plan.value.id, { meal_date: mealDate })
  } catch (e) {
    adjustError.value = e instanceof Error ? e.message : '重新推薦這天失敗'
  } finally {
    regeneratingDay.value = null
  }
}

const selectedMeal = ref<{ date: string; meal: MealDetail } | null>(null)
const weightInput = ref<number | null>(null)
const replaceIdInput = ref<number | null>(null)
const searchQuery = ref('')
const searchResults = ref<RecipeSearchResult[]>([])
const searching = ref(false)
const searchError = ref<string | null>(null)
const adjustingMeal = ref(false)

function openMealAdjust(date: string, meal: MealDetail) {
  selectedMeal.value = { date, meal }
  weightInput.value = meal.serving_weight_g
  replaceIdInput.value = null
  searchQuery.value = ''
  searchResults.value = []
  adjustError.value = null
}

function closeMealAdjust() {
  selectedMeal.value = null
}

async function submitAdjustWeight() {
  if (!plan.value?.id || !selectedMeal.value || weightInput.value === null) return
  adjustingMeal.value = true
  adjustError.value = null
  try {
    plan.value = await adjustServingWeight(plan.value.id, {
      meal_id: selectedMeal.value.meal.id,
      new_serving_weight_g: weightInput.value,
    })
    closeMealAdjust()
  } catch (e) {
    adjustError.value = e instanceof Error ? e.message : '調整分量失敗'
  } finally {
    adjustingMeal.value = false
  }
}

async function submitReplace() {
  if (!plan.value?.id || !selectedMeal.value || replaceIdInput.value === null) return
  adjustingMeal.value = true
  adjustError.value = null
  try {
    plan.value = await replaceMeal(plan.value.id, {
      meal_id: selectedMeal.value.meal.id,
      new_recipe_id: replaceIdInput.value,
    })
    closeMealAdjust()
  } catch (e) {
    adjustError.value = e instanceof Error ? e.message : '替換失敗'
  } finally {
    adjustingMeal.value = false
  }
}

async function runSearch() {
  if (!searchQuery.value.trim()) return
  searching.value = true
  searchError.value = null
  try {
    searchResults.value = await searchRecipesByName(searchQuery.value.trim())
  } catch (e) {
    searchError.value = e instanceof Error ? e.message : '搜尋失敗'
  } finally {
    searching.value = false
  }
}

async function submitSearchReplace(recipeId: number) {
  if (!plan.value?.id || !selectedMeal.value) return
  adjustingMeal.value = true
  adjustError.value = null
  try {
    plan.value = await searchAndReplaceMeal(plan.value.id, {
      meal_id: selectedMeal.value.meal.id,
      search_query: searchQuery.value,
      new_recipe_id: recipeId,
    })
    closeMealAdjust()
  } catch (e) {
    adjustError.value = e instanceof Error ? e.message : '替換失敗'
  } finally {
    adjustingMeal.value = false
  }
}

const confirming = ref(false)
const confirmError = ref<string | null>(null)
const confirmedListId = ref<number | null>(null)

async function submitConfirm() {
  if (!plan.value?.id) return
  confirming.value = true
  confirmError.value = null
  try {
    const res = await confirmMealPlan(plan.value.id)
    setCurrentShoppingListId(res.shopping_list_id)
    confirmedListId.value = res.shopping_list_id
    await refetchPlan(plan.value.id)
  } catch (e) {
    confirmError.value = e instanceof Error ? e.message : '確認失敗，請稍後再試'
  } finally {
    confirming.value = false
  }
}

function mealTypeLabel(type: string): string {
  return MEAL_TYPE_LABELS[type] ?? type
}
function dayLabel(day: DayMeals): string {
  const weekday = WEEKDAY_LABELS[new Date(`${day.date}T00:00:00`).getDay()]
  return weekday ?? day.date
}
</script>

<template>
  <div class="mx-auto max-w-5xl px-4 py-8">
    <div v-if="!hasTwoUsers" class="rounded-2xl border border-dashed border-ink/20 p-6 text-center text-tea">
      請先到「總覽」頁設定兩位使用者
    </div>

    <template v-else>
      <div v-if="!plan && !loadingPlan" class="rounded-2xl border border-ink/10 bg-surface p-6">
        <div class="flex items-center gap-1.5">
          <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-ink" aria-hidden="true" />
          <h1 class="border-b-[1.5px] border-accent pb-1 text-[11.5px] font-semibold uppercase tracking-wide text-muted">
            產生本週推薦
          </h1>
        </div>
        <p class="mt-3 text-sm text-tea">
          為 {{ userA?.name }} 和 {{ userB?.name }} 產生一週菜單，依雙方的目標熱量與食譜資料庫規則式安排。
        </p>
        <div class="mt-4">
          <label class="mb-1 block text-xs text-tea">週一日期</label>
          <input v-model="weekStart" type="date" class="rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
        </div>
        <p v-if="generateError" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ generateError }}</p>
        <button
          type="button"
          class="mt-4 w-full rounded-full bg-accent py-2.5 text-sm font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
          :disabled="generating"
          @click="submitGenerate"
        >
          {{ generating ? '產生中…' : '產生推薦' }}
        </button>
      </div>

      <p v-if="loadingPlan" class="text-sm text-tea">載入中…</p>
      <p v-if="planError" class="rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ planError }}</p>

      <template v-if="plan">
        <div class="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-ink/10 bg-surface p-4">
          <div>
            <h1 class="font-serif text-2xl text-ink">{{ plan.plan_date }} 那一週</h1>
            <p class="text-xs text-tea">
              狀態：{{ plan.plan_status }} · {{ userA?.name }} 目標 {{ plan.user_a_daily_calories_target }}kcal
              <span v-if="plan.user_a_menstrual_phase && plan.user_a_menstrual_phase !== '無'">
                （{{ plan.user_a_menstrual_phase }}）
              </span>
              · {{ userB?.name }} 目標 {{ plan.user_b_daily_calories_target }}kcal
            </p>
          </div>
          <div class="text-right">
            <button
              type="button"
              class="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
              :disabled="confirming"
              @click="submitConfirm"
            >
              {{ confirming ? '確認中…' : '確認推薦' }}
            </button>
            <p v-if="confirmedListId !== null" class="mt-1 text-xs text-accent">已生成購物清單（#{{ confirmedListId }}）</p>
          </div>
        </div>
        <p v-if="confirmError" class="mt-2 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ confirmError }}</p>
        <p v-if="adjustError" class="mt-2 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ adjustError }}</p>

        <div class="mt-4 flex gap-3 overflow-x-auto pb-2">
          <div
            v-for="day in plan.days"
            :key="day.date"
            class="w-[200px] shrink-0 rounded-2xl border border-ink/10 bg-surface p-3"
            :class="regeneratingDay === day.date && 'opacity-50'"
          >
            <div class="flex items-center justify-between">
              <p class="text-xs font-semibold uppercase tracking-wide text-muted">{{ dayLabel(day) }} · {{ day.date }}</p>
              <button
                type="button"
                class="text-[11px] font-semibold text-accent hover:text-accent-bright disabled:opacity-40"
                :disabled="regeneratingDay !== null"
                @click="submitRegenerateDay(day.date)"
              >
                {{ regeneratingDay === day.date ? '推薦中…' : '重新推薦' }}
              </button>
            </div>
            <ul class="mt-2 space-y-2">
              <li v-for="meal in day.meals" :key="meal.id" class="text-xs">
                <p class="text-tea">{{ mealTypeLabel(meal.meal_type) }} · {{ userName(meal.assigned_user_id) }}</p>
                <button type="button" class="text-left font-medium text-ink hover:text-accent" @click="openMealAdjust(day.date, meal)">
                  {{ meal.recipe_name }}
                </button>
                <p class="text-muted">{{ meal.calories }}kcal · {{ meal.serving_weight_g }}g</p>
              </li>
              <li v-if="day.meals.length === 0" class="text-xs text-tea">尚無安排</li>
            </ul>
          </div>
        </div>

        <section v-if="selectedMeal" class="mt-4 rounded-2xl border border-accent bg-accent-tint/50 p-4">
          <div class="flex items-center justify-between">
            <p class="text-sm text-ink">
              調整：{{ selectedMeal.date }} {{ mealTypeLabel(selectedMeal.meal.meal_type) }} · {{ userName(selectedMeal.meal.assigned_user_id) }} ·
              {{ selectedMeal.meal.recipe_name }}
            </p>
            <button type="button" class="text-xs text-tea hover:text-ink" @click="closeMealAdjust">關閉</button>
          </div>

          <div class="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <label class="mb-1 block text-xs text-tea">分量（g）</label>
              <div class="flex gap-2">
                <input v-model.number="weightInput" type="number" min="1" class="w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
                <button
                  type="button"
                  class="shrink-0 rounded-lg bg-accent px-3 py-2 text-xs font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
                  :disabled="adjustingMeal"
                  @click="submitAdjustWeight"
                >
                  更新
                </button>
              </div>
            </div>
            <div>
              <label class="mb-1 block text-xs text-tea">直接替換（食譜 ID）</label>
              <div class="flex gap-2">
                <input v-model.number="replaceIdInput" type="number" min="1" class="w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
                <button
                  type="button"
                  class="shrink-0 rounded-lg bg-accent px-3 py-2 text-xs font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
                  :disabled="adjustingMeal || replaceIdInput === null"
                  @click="submitReplace"
                >
                  替換
                </button>
              </div>
            </div>
          </div>

          <div class="mt-3">
            <label class="mb-1 block text-xs text-tea">搜尋替換</label>
            <div class="flex gap-2">
              <input
                v-model="searchQuery"
                type="text"
                placeholder="食譜名稱"
                class="w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
                @keydown.enter="runSearch"
              />
              <button
                type="button"
                class="shrink-0 rounded-lg border border-ink/15 px-3 py-2 text-xs font-semibold text-ink hover:bg-bg disabled:opacity-50"
                :disabled="searching"
                @click="runSearch"
              >
                {{ searching ? '搜尋中…' : '搜尋' }}
              </button>
            </div>
            <p v-if="searchError" class="mt-2 text-xs text-alert">{{ searchError }}</p>
            <ul v-if="searchResults.length" class="mt-2 divide-y divide-ink/10">
              <li v-for="r in searchResults" :key="r.id" class="flex items-center justify-between py-1.5 text-sm">
                <span class="text-ink">{{ r.recipe_name }}<span class="text-tea">（{{ r.category }}・{{ r.cost_level }}）</span></span>
                <button type="button" class="text-xs font-semibold text-accent hover:text-accent-bright" :disabled="adjustingMeal" @click="submitSearchReplace(r.id)">
                  選這個
                </button>
              </li>
            </ul>
          </div>
        </section>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import {
  addDish,
  confirmMealPlan,
  deleteMealPlan,
  fetchMealPlan,
  generateMealPlan,
  listMealPlans,
  rebalanceDay,
  regenerateDay,
  removeDish,
  replaceMeal,
} from './meal_plan_api'
import { deleteFixedMealPreference, fetchFixedMealPreferences, setFixedMealPreference } from './fixed_meal_preference_api'
import { addExcludedRecipe, fetchExcludedRecipes, removeExcludedRecipe } from './excluded_recipe_api'
import { addFavoriteRecipe, fetchFavoriteRecipes, removeFavoriteRecipe } from './favorite_recipe_api'
import { fetchSoupDays, setSoupDays } from './soup_day_preference_api'
import { fetchPrepPlan } from './prep_plan_api'
import { searchRecipesByName } from '../recipes/recipe_api'
import { useConfirmDialog } from '../shared/useConfirmDialog'
import { useHouseholdConfig } from '../shared/useHouseholdConfig'
import { useLocalStorage } from '../shared/useLocalStorage'
import { startOfWeekMonday, toISODate, today } from '../shared/date_utils'
import type {
  DayMeals, ExcludedRecipe, FavoriteRecipe, FixedMealPreference, FixedMealType,
  MealDetail, MealPlanDetail, MealPlanSummary, MealType, PrepDayMeal, PrepPlan, RecipeSearchResult,
} from '../shared/types'

const MEAL_TYPE_LABELS: Record<string, string> = {
  breakfast: '早餐',
  lunch: '午餐',
  afternoon_snack: '下午茶',
  dinner: '晚餐',
}
const WEEKDAY_LABELS = ['週日', '週一', '週二', '週三', '週四', '週五', '週六']
const SOUP_WEEKDAY_LABELS = ['週一', '週二', '週三', '週四', '週五', '週六', '週日'] // 對應後端 day_of_week 0-6

const { config, setCurrentMealPlanId, setCurrentShoppingListId } = useHouseholdConfig()
const { confirmDialog } = useConfirmDialog()
const users = computed(() => config.value.users)
const hasTwoUsers = computed(() => users.value.length >= 2)
const userA = computed(() => users.value[0] ?? null)
const userB = computed(() => users.value[1] ?? null)

function userName(userId: number): string {
  return users.value.find((u) => u.id === userId)?.name ?? `使用者 ${userId}`
}

// ---- 固定餐點：早餐/下午茶可以固定吃某個食譜，產生週菜單前先套用這個規則，之後只依熱量調整份量 ----

const FIXED_MEAL_TYPES: FixedMealType[] = ['breakfast', 'afternoon_snack']

const fixedMealPrefs = ref<FixedMealPreference[]>([])
const fixedMealsLoading = ref(false)
const fixedMealsError = ref<string | null>(null)
const showFixedMeals = ref(false)

async function loadFixedMeals() {
  if (!userA.value || !userB.value) return
  fixedMealsLoading.value = true
  fixedMealsError.value = null
  try {
    const [a, b] = await Promise.all([fetchFixedMealPreferences(userA.value.id), fetchFixedMealPreferences(userB.value.id)])
    fixedMealPrefs.value = [...a, ...b]
  } catch (e) {
    fixedMealsError.value = e instanceof Error ? e.message : '讀取固定餐點設定失敗'
  } finally {
    fixedMealsLoading.value = false
  }
}

watchEffect(() => {
  if (userA.value && userB.value) loadFixedMeals()
})

function fixedMealFor(userId: number, mealType: FixedMealType): FixedMealPreference | null {
  return fixedMealPrefs.value.find((p) => p.user_id === userId && p.meal_type === mealType) ?? null
}

const fixedMealPickerTarget = ref<{ userId: number; mealType: FixedMealType } | null>(null)
const fixedMealQuery = ref('')
const fixedMealResults = ref<RecipeSearchResult[]>([])
const fixedMealSearching = ref(false)
const fixedMealSaving = ref(false)

function openFixedMealPicker(userId: number, mealType: FixedMealType) {
  fixedMealPickerTarget.value = { userId, mealType }
  fixedMealQuery.value = ''
  fixedMealResults.value = []
  fixedMealsError.value = null
}
function closeFixedMealPicker() {
  fixedMealPickerTarget.value = null
}

async function runFixedMealSearch() {
  if (!fixedMealQuery.value.trim()) return
  fixedMealSearching.value = true
  fixedMealsError.value = null
  try {
    fixedMealResults.value = await searchRecipesByName(fixedMealQuery.value.trim())
  } catch (e) {
    fixedMealsError.value = e instanceof Error ? e.message : '搜尋失敗'
  } finally {
    fixedMealSearching.value = false
  }
}

async function chooseFixedMeal(recipeId: number) {
  if (!fixedMealPickerTarget.value) return
  fixedMealSaving.value = true
  fixedMealsError.value = null
  try {
    const { userId, mealType } = fixedMealPickerTarget.value
    const saved = await setFixedMealPreference(userId, mealType, recipeId)
    fixedMealPrefs.value = [...fixedMealPrefs.value.filter((p) => !(p.user_id === saved.user_id && p.meal_type === saved.meal_type)), saved]
    closeFixedMealPicker()
  } catch (e) {
    fixedMealsError.value = e instanceof Error ? e.message : '設定失敗，請稍後再試'
  } finally {
    fixedMealSaving.value = false
  }
}

async function removeFixedMeal(id: number) {
  fixedMealsError.value = null
  try {
    await deleteFixedMealPreference(id)
    fixedMealPrefs.value = fixedMealPrefs.value.filter((p) => p.id !== id)
  } catch (e) {
    fixedMealsError.value = e instanceof Error ? e.message : '取消失敗，請稍後再試'
  }
}

// ---- 湯品星期：兩人共用一份設定，勾選這天想在午餐/晚餐多喝一道湯，不分誰勾的 ----

const soupDays = ref<number[]>([])
const soupError = ref<string | null>(null)
const showRules = ref(false)

async function loadSoupDays() {
  soupError.value = null
  try {
    soupDays.value = (await fetchSoupDays()).days
  } catch (e) {
    soupError.value = e instanceof Error ? e.message : '讀取湯品設定失敗'
  }
}

function isSoupDay(dayOfWeek: number): boolean {
  return soupDays.value.includes(dayOfWeek)
}

async function toggleSoupDay(dayOfWeek: number) {
  const next = soupDays.value.includes(dayOfWeek) ? soupDays.value.filter((d) => d !== dayOfWeek) : [...soupDays.value, dayOfWeek]
  soupError.value = null
  try {
    soupDays.value = (await setSoupDays(next)).days
  } catch (e) {
    soupError.value = e instanceof Error ? e.message : '更新湯品設定失敗'
  }
}

// ---- 黑名單：兩人共用一份，標記「不要再推薦」，產生/重推菜單時直接從候選池排除（跟固定餐點相反） ----

const excludedRecipes = ref<ExcludedRecipe[]>([])
const excludedError = ref<string | null>(null)
const excludedQuery = ref('')
const excludedResults = ref<RecipeSearchResult[]>([])
const excludedSearching = ref(false)
const excludedSaving = ref(false)
const excludedPickerOpen = ref(false)

async function loadExcludedRecipes() {
  try {
    excludedRecipes.value = await fetchExcludedRecipes()
  } catch (e) {
    excludedError.value = e instanceof Error ? e.message : '讀取黑名單失敗'
  }
}

function openExcludedPicker() {
  excludedPickerOpen.value = true
  excludedQuery.value = ''
  excludedResults.value = []
  excludedError.value = null
}
function closeExcludedPicker() {
  excludedPickerOpen.value = false
}

async function runExcludedSearch() {
  if (!excludedQuery.value.trim()) return
  excludedSearching.value = true
  excludedError.value = null
  try {
    excludedResults.value = await searchRecipesByName(excludedQuery.value.trim())
  } catch (e) {
    excludedError.value = e instanceof Error ? e.message : '搜尋失敗'
  } finally {
    excludedSearching.value = false
  }
}

async function chooseExcludedRecipe(recipeId: number) {
  excludedSaving.value = true
  excludedError.value = null
  try {
    const saved = await addExcludedRecipe(recipeId)
    excludedRecipes.value = [...excludedRecipes.value.filter((r) => r.id !== saved.id), saved]
    closeExcludedPicker()
  } catch (e) {
    excludedError.value = e instanceof Error ? e.message : '加入黑名單失敗'
  } finally {
    excludedSaving.value = false
  }
}

async function removeExcluded(id: number) {
  excludedError.value = null
  try {
    await removeExcludedRecipe(id)
    excludedRecipes.value = excludedRecipes.value.filter((r) => r.id !== id)
  } catch (e) {
    excludedError.value = e instanceof Error ? e.message : '移除失敗，請稍後再試'
  }
}

// ---- 最愛清單：軟性加權，選餐評分時比較容易被選到，但不像固定餐點那樣鎖死 ----

const favoriteRecipes = ref<FavoriteRecipe[]>([])
const favoritesError = ref<string | null>(null)
const showFavorites = ref(false)
const favoriteQuery = ref('')
const favoriteResults = ref<RecipeSearchResult[]>([])
const favoriteSearching = ref(false)
const favoriteSaving = ref(false)
const favoritePickerUserId = ref<number | null>(null)

async function loadFavoriteRecipes() {
  if (!userA.value || !userB.value) return
  try {
    const [a, b] = await Promise.all([fetchFavoriteRecipes(userA.value.id), fetchFavoriteRecipes(userB.value.id)])
    favoriteRecipes.value = [...a, ...b]
  } catch (e) {
    favoritesError.value = e instanceof Error ? e.message : '讀取最愛清單失敗'
  }
}

function openFavoritePicker(userId: number) {
  favoritePickerUserId.value = userId
  favoriteQuery.value = ''
  favoriteResults.value = []
  favoritesError.value = null
}
function closeFavoritePicker() {
  favoritePickerUserId.value = null
}

async function runFavoriteSearch() {
  if (!favoriteQuery.value.trim()) return
  favoriteSearching.value = true
  favoritesError.value = null
  try {
    favoriteResults.value = await searchRecipesByName(favoriteQuery.value.trim())
  } catch (e) {
    favoritesError.value = e instanceof Error ? e.message : '搜尋失敗'
  } finally {
    favoriteSearching.value = false
  }
}

async function chooseFavoriteRecipe(recipeId: number) {
  if (favoritePickerUserId.value === null) return
  favoriteSaving.value = true
  favoritesError.value = null
  try {
    const saved = await addFavoriteRecipe(favoritePickerUserId.value, recipeId)
    favoriteRecipes.value = [...favoriteRecipes.value.filter((r) => r.id !== saved.id), saved]
    closeFavoritePicker()
  } catch (e) {
    favoritesError.value = e instanceof Error ? e.message : '加入最愛失敗'
  } finally {
    favoriteSaving.value = false
  }
}

async function removeFavorite(id: number) {
  favoritesError.value = null
  try {
    await removeFavoriteRecipe(id)
    favoriteRecipes.value = favoriteRecipes.value.filter((r) => r.id !== id)
  } catch (e) {
    favoritesError.value = e instanceof Error ? e.message : '移除失敗，請稍後再試'
  }
}

watchEffect(() => {
  if (userA.value && userB.value) {
    loadSoupDays()
    loadExcludedRecipes()
    loadFavoriteRecipes()
  }
})

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

// ---- 整週重新推薦：等同再產生一次同一週的菜單（後端每次產生都是新的一筆，不會覆蓋），
// 產生後直接切換過去看新結果 ----

const regeneratingWeek = ref(false)

async function submitRegenerateWeek() {
  if (!plan.value || !userA.value || !userB.value) return
  const ok = await confirmDialog(`確定要整週重新推薦「${plan.value.plan_date} 那一週」嗎？目前的安排（含你手動調整過的部分）不會被覆蓋，但畫面會切換到新產生的版本。`)
  if (!ok) return
  regeneratingWeek.value = true
  generateError.value = null
  try {
    const result = await generateMealPlan({
      week_start_date: plan.value.plan_date,
      user_id_a: userA.value.id,
      user_id_b: userB.value.id,
    })
    plan.value = result
    setCurrentMealPlanId(result.id)
    await loadOtherPlans()
  } catch (e) {
    generateError.value = e instanceof Error ? e.message : '整週重新推薦失敗，請稍後再試'
  } finally {
    regeneratingWeek.value = false
  }
}

// ---- 查看其他週：後端每次「產生」都會留下一筆新紀錄，這裡列出兩人名下所有週菜單讓你切換查看 ----

const otherPlans = ref<MealPlanSummary[]>([])
const otherPlansLoading = ref(false)
const showWeekPicker = ref(false)

async function loadOtherPlans() {
  if (!userA.value) return
  otherPlansLoading.value = true
  try {
    otherPlans.value = await listMealPlans({ user_id: userA.value.id })
  } catch {
    // 週清單載入失敗不影響主要功能，靜默忽略即可
  } finally {
    otherPlansLoading.value = false
  }
}

watchEffect(() => {
  if (userA.value) loadOtherPlans()
})

function switchToPlan(planId: number) {
  setCurrentMealPlanId(planId)
  showWeekPicker.value = false
}

const deletingPlanId = ref<number | null>(null)

async function deletePlan(planId: number, planDateLabel: string) {
  const ok = await confirmDialog(`確定要刪除「${planDateLabel} 那一週」的推薦嗎？這個操作無法復原。`)
  if (!ok) return
  deletingPlanId.value = planId
  generateError.value = null
  try {
    await deleteMealPlan(planId)
    otherPlans.value = otherPlans.value.filter((p) => p.id !== planId)
    if (plan.value?.id === planId) {
      const next = otherPlans.value[0] ?? null
      setCurrentMealPlanId(next?.id ?? null)
      if (!next) plan.value = null
    }
  } catch (e) {
    generateError.value = e instanceof Error ? e.message : '刪除失敗，請稍後再試'
  } finally {
    deletingPlanId.value = null
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

// ---- 餐點編輯：改成「一餐一餐」處理。點某天某一餐開小視窗，裡面可以移除/換掉現有的菜、
// 自由新增菜（早餐/下午茶各自一份，需選是誰的；午餐/晚餐兩人共用）。組成改變後份量會先概略
// 平均分配，實際貼合熱量目標要另外按「重新計算份量」（rebalance-day）----

const mealEditor = ref<{ date: string; mealType: MealType } | null>(null)
const mealEditorAddUserId = ref<number | null>(null)
// 換菜目標：一般「換一道」是單一 mealId，多選後「換成…」是好幾個 mealId 一次套用同一個新食譜
const mealEditorReplacingIds = ref<number[]>([])
const mealEditorQuery = ref('')
const mealEditorResults = ref<RecipeSearchResult[]>([])
const mealEditorSearching = ref(false)
const mealEditorBusy = ref(false)
const rebalancingDay = ref<string | null>(null)

// ---- 多選：勾選這一餐裡的好幾道菜，一次移除或一次換成同一道新食譜 ----
const mealEditorSelected = ref<Set<number>>(new Set())

function toggleMealEditorSelected(mealId: number) {
  const next = new Set(mealEditorSelected.value)
  if (next.has(mealId)) next.delete(mealId)
  else next.add(mealId)
  mealEditorSelected.value = next
}
function clearMealEditorSelection() {
  mealEditorSelected.value = new Set()
}

// ---- 搜尋欄記住最近 5 筆查詢過的菜名，方便重複查同幾道菜 ----
const recentMealSearches = useLocalStorage<string[]>('block7_meal_editor_recent_searches', [])
function rememberMealSearch(query: string) {
  const trimmed = query.trim()
  if (!trimmed) return
  recentMealSearches.value = [trimmed, ...recentMealSearches.value.filter((q) => q !== trimmed)].slice(0, 5)
}

function openMealEditor(date: string, mealType: MealType) {
  mealEditor.value = { date, mealType }
  mealEditorAddUserId.value = userA.value?.id ?? null
  mealEditorReplacingIds.value = []
  mealEditorQuery.value = ''
  mealEditorResults.value = []
  clearMealEditorSelection()
  adjustError.value = null
}
function closeMealEditor() {
  mealEditor.value = null
}

function mealEditorDishes(): MealDetail[] {
  if (!plan.value || !mealEditor.value) return []
  const { date, mealType } = mealEditor.value
  const day = plan.value.days.find((d) => d.date === date)
  if (!day) return []
  return day.meals
    .filter((m) => m.meal_type === mealType)
    .slice()
    .sort((a, b) => a.recipe_name.localeCompare(b.recipe_name, 'zh-Hant'))
}

function startReplaceDish(mealId: number) {
  mealEditorReplacingIds.value = [mealId]
  mealEditorQuery.value = ''
  mealEditorResults.value = []
}
function startBulkReplace() {
  if (mealEditorSelected.value.size === 0) return
  mealEditorReplacingIds.value = [...mealEditorSelected.value]
  mealEditorQuery.value = ''
  mealEditorResults.value = []
}
function cancelReplaceDish() {
  mealEditorReplacingIds.value = []
}

async function runMealEditorSearch() {
  if (!mealEditorQuery.value.trim()) return
  mealEditorSearching.value = true
  adjustError.value = null
  try {
    mealEditorResults.value = await searchRecipesByName(mealEditorQuery.value.trim())
    rememberMealSearch(mealEditorQuery.value)
  } catch (e) {
    adjustError.value = e instanceof Error ? e.message : '搜尋失敗'
  } finally {
    mealEditorSearching.value = false
  }
}

function useRecentMealSearch(query: string) {
  mealEditorQuery.value = query
  runMealEditorSearch()
}

async function chooseMealEditorRecipe(recipeId: number) {
  if (!plan.value?.id || !mealEditor.value) return
  mealEditorBusy.value = true
  adjustError.value = null
  try {
    if (mealEditorReplacingIds.value.length > 0) {
      // 逐一套用同一個新食譜到每個選到的 mealId；換菜 API 是就地取代同一個 meal_id，先後順序不影響結果
      for (const mealId of mealEditorReplacingIds.value) {
        plan.value = await replaceMeal(plan.value.id, { meal_id: mealId, new_recipe_id: recipeId })
      }
      mealEditorReplacingIds.value = []
      clearMealEditorSelection()
    } else {
      const { date, mealType } = mealEditor.value
      const needsUser = FIXED_MEAL_TYPES.includes(mealType as FixedMealType)
      if (needsUser && !mealEditorAddUserId.value) throw new Error('請先選要新增給誰')
      plan.value = await addDish(plan.value.id, {
        meal_date: date,
        meal_type: mealType,
        recipe_id: recipeId,
        user_id: needsUser ? mealEditorAddUserId.value : null,
      })
    }
    mealEditorQuery.value = ''
    mealEditorResults.value = []
  } catch (e) {
    adjustError.value = e instanceof Error ? e.message : '操作失敗，請稍後再試'
  } finally {
    mealEditorBusy.value = false
  }
}

async function removeMealEditorDish(mealId: number) {
  if (!plan.value?.id) return
  mealEditorBusy.value = true
  adjustError.value = null
  try {
    plan.value = await removeDish(plan.value.id, mealId)
  } catch (e) {
    adjustError.value = e instanceof Error ? e.message : '移除失敗，請稍後再試'
  } finally {
    mealEditorBusy.value = false
  }
}

async function removeSelectedDishes() {
  if (!plan.value?.id || mealEditorSelected.value.size === 0) return
  mealEditorBusy.value = true
  adjustError.value = null
  try {
    for (const mealId of mealEditorSelected.value) {
      plan.value = await removeDish(plan.value.id, mealId)
    }
    clearMealEditorSelection()
  } catch (e) {
    adjustError.value = e instanceof Error ? e.message : '移除失敗，請稍後再試'
  } finally {
    mealEditorBusy.value = false
  }
}

async function submitRebalanceDay(date: string) {
  if (!plan.value?.id) return
  rebalancingDay.value = date
  adjustError.value = null
  try {
    plan.value = await rebalanceDay(plan.value.id, { meal_date: date })
  } catch (e) {
    adjustError.value = e instanceof Error ? e.message : '重新計算份量失敗'
  } finally {
    rebalancingDay.value = null
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

// ---- 備料規劃：計畫確認後才生成，把週菜單換算成「週日整週肉類批次 + 週二/週四備便當 + 每日晚餐提示」----

const prepPlan = ref<PrepPlan | null>(null)
const prepPlanLoading = ref(false)
const prepPlanError = ref<string | null>(null)
const showPrepPlan = ref(false)

async function loadPrepPlan(planId: number) {
  prepPlanLoading.value = true
  prepPlanError.value = null
  try {
    prepPlan.value = await fetchPrepPlan(planId)
  } catch (e) {
    prepPlanError.value = e instanceof Error ? e.message : '讀取備料規劃失敗'
  } finally {
    prepPlanLoading.value = false
  }
}

watchEffect(() => {
  if (plan.value?.id && plan.value.plan_status === '已確認') loadPrepPlan(plan.value.id)
  else prepPlan.value = null
})

function dayMealSummary(d: PrepDayMeal | null): string {
  if (!d) return ''
  const fresh = d.cook_fresh.map((x) => x.recipe_name).join('、')
  const reheat = d.reheat_from_batch.map((x) => x.recipe_name).join('、')
  const parts = []
  if (fresh) parts.push(`現煮 ${fresh}`)
  if (reheat) parts.push(`微波 ${reheat}`)
  return parts.join('；')
}

function mealTypeLabel(type: string): string {
  return MEAL_TYPE_LABELS[type] ?? type
}
function dayLabel(day: DayMeals): string {
  const weekday = WEEKDAY_LABELS[new Date(`${day.date}T00:00:00`).getDay()]
  return weekday ?? day.date
}

// ---- 兩人菜單多半一致，中式一餐又拆成主食/肉/菜三道：把同一餐兩人的三道菜分組顯示，
// 相同的菜合併成一行（公克不同就兩個都列出），真的不同的菜收進「差異」摺疊區，避免整頁看起來一團亂 ----

const MEAL_TYPE_DISPLAY_ORDER = ['breakfast', 'lunch', 'afternoon_snack', 'dinner']
const MEAL_TYPE_ICONS: Record<string, string> = {
  breakfast: '🌅',
  lunch: '🍚',
  afternoon_snack: '🍵',
  dinner: '🌙',
}
const CATEGORY_ORDER = ['主食', '肉', '菜', '湯']
const CATEGORY_ICONS: Record<string, string> = {
  主食: '🍚',
  肉: '🍖',
  菜: '🥬',
  湯: '🍲',
}

interface MealSlotView {
  category: string | null
  icon: string
  primary: MealDetail
  diff: MealDetail | null
  otherWeightG: number | null
}

interface MealTypeView {
  type: string
  label: string
  icon: string
  slots: MealSlotView[]
}

function buildMealTypeView(day: DayMeals, mealType: string): MealTypeView | null {
  const items = day.meals.filter((m) => m.meal_type === mealType)
  if (items.length === 0) return null

  const aId = userA.value?.id
  const bId = userB.value?.id
  const aItems = items.filter((m) => m.assigned_user_id === aId)
  const bItems = items.filter((m) => m.assigned_user_id === bId)

  const hasCategories = items.some((m) => m.recipe_category && CATEGORY_ORDER.includes(m.recipe_category))
  const categoryKeys: (string | null)[] = hasCategories ? CATEGORY_ORDER : [null]

  const slots: MealSlotView[] = []
  for (const cat of categoryKeys) {
    const aItem = cat ? aItems.find((m) => m.recipe_category === cat) : aItems[0]
    const bItem = cat ? bItems.find((m) => m.recipe_category === cat) : bItems[0]
    if (!aItem && !bItem) continue

    const primary = (aItem ?? bItem) as MealDetail
    const other = aItem ? bItem : undefined
    const sameRecipe = !!aItem && !!bItem && aItem.recipe_id === bItem.recipe_id

    slots.push({
      category: cat,
      icon: cat ? (CATEGORY_ICONS[cat] ?? '🍽️') : (MEAL_TYPE_ICONS[mealType] ?? '🍽️'),
      primary,
      diff: !other || sameRecipe ? null : other,
      otherWeightG: sameRecipe && other && other.serving_weight_g !== primary.serving_weight_g ? other.serving_weight_g : null,
    })
  }

  return slots.length ? { type: mealType, label: mealTypeLabel(mealType), icon: MEAL_TYPE_ICONS[mealType] ?? '🍽️', slots } : null
}

function dayMealTypeViews(day: DayMeals): MealTypeView[] {
  return MEAL_TYPE_DISPLAY_ORDER.map((t) => buildMealTypeView(day, t)).filter((v): v is MealTypeView => v !== null)
}

interface DiffItemView {
  key: string
  type: string
  mealLabel: string
  category: string | null
  item: MealDetail
}

function dayDiffItems(day: DayMeals): DiffItemView[] {
  const result: DiffItemView[] = []
  for (const mt of dayMealTypeViews(day)) {
    for (const slot of mt.slots) {
      if (slot.diff) result.push({ key: `${mt.type}-${slot.category ?? 'x'}`, type: mt.type, mealLabel: mt.label, category: slot.category, item: slot.diff })
    }
  }
  return result
}

const expandedDiffDates = ref<Set<string>>(new Set())
function toggleDiffExpanded(date: string) {
  const next = new Set(expandedDiffDates.value)
  if (next.has(date)) next.delete(date)
  else next.add(date)
  expandedDiffDates.value = next
}
</script>

<template>
  <div class="mx-auto max-w-5xl px-4 py-8">
    <div v-if="!hasTwoUsers" class="rounded-2xl border border-dashed border-ink/20 p-6 text-center text-tea">
      請先到「總覽」頁設定兩位使用者
    </div>

    <template v-else>
      <section class="rounded-2xl border border-ink/10 bg-surface p-4">
        <button type="button" class="flex w-full items-center justify-between text-left" @click="showFixedMeals = !showFixedMeals">
          <span class="font-serif text-lg text-ink">固定餐點</span>
          <span class="text-xs text-tea">{{ showFixedMeals ? '收合' : '展開' }}</span>
        </button>

        <div v-if="showFixedMeals" class="mt-3">
          <p class="text-xs text-tea">早餐/下午茶可以固定吃某個食譜，產生週菜單時只依熱量調整份量，不會被規則式演算法換成別的菜</p>
          <p v-if="fixedMealsLoading" class="mt-2 text-xs text-tea">載入中…</p>
          <p v-if="fixedMealsError" class="mt-2 rounded-lg bg-alert/10 px-3 py-2 text-xs text-alert">{{ fixedMealsError }}</p>

          <div v-for="user in [userA, userB]" :key="user ? user.id : ''">
            <div v-if="user" class="mt-3 rounded-xl border border-ink/10 p-3">
              <p class="text-sm font-semibold text-ink">{{ user.name }}</p>
              <div v-for="mt in FIXED_MEAL_TYPES" :key="mt" class="mt-2 flex items-center gap-2">
                <span class="w-14 shrink-0 text-xs text-tea">{{ mealTypeLabel(mt) }}</span>
                <span class="min-w-0 flex-1 truncate text-sm text-ink">{{ fixedMealFor(user.id, mt)?.recipe_name ?? '未固定' }}</span>
                <button
                  v-if="fixedMealFor(user.id, mt)"
                  type="button"
                  class="shrink-0 text-xs text-tea hover:text-alert"
                  @click="removeFixedMeal(fixedMealFor(user.id, mt)!.id)"
                >
                  取消
                </button>
                <button
                  v-else
                  type="button"
                  class="shrink-0 text-xs font-semibold text-accent hover:text-accent-bright"
                  @click="openFixedMealPicker(user.id, mt)"
                >
                  設定
                </button>
              </div>
            </div>
          </div>

          <div v-if="fixedMealPickerTarget" class="mt-3 rounded-xl border border-accent bg-accent-tint/50 p-3">
            <div class="flex items-center justify-between">
              <p class="text-xs text-ink">
                選一個食譜當作{{ userName(fixedMealPickerTarget.userId) }}固定的{{ mealTypeLabel(fixedMealPickerTarget.mealType) }}
              </p>
              <button type="button" class="text-xs text-tea hover:text-ink" @click="closeFixedMealPicker">關閉</button>
            </div>
            <div class="mt-2 flex gap-2">
              <input
                v-model="fixedMealQuery"
                type="text"
                placeholder="食譜名稱"
                class="w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
                @keydown.enter="runFixedMealSearch"
              />
              <button
                type="button"
                class="shrink-0 rounded-lg border border-ink/15 px-3 py-2 text-xs font-semibold text-ink hover:bg-bg disabled:opacity-50"
                :disabled="fixedMealSearching"
                @click="runFixedMealSearch"
              >
                {{ fixedMealSearching ? '搜尋中…' : '搜尋' }}
              </button>
            </div>
            <ul v-if="fixedMealResults.length" class="mt-2 divide-y divide-ink/10">
              <li v-for="r in fixedMealResults" :key="r.id" class="flex items-center justify-between py-1.5 text-sm">
                <span class="text-ink">{{ r.recipe_name }}<span class="text-tea">（{{ r.category }}）</span></span>
                <button
                  type="button"
                  class="text-xs font-semibold text-accent hover:text-accent-bright disabled:opacity-50"
                  :disabled="fixedMealSaving"
                  @click="chooseFixedMeal(r.id)"
                >
                  選這個
                </button>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section class="mt-4 rounded-2xl border border-ink/10 bg-surface p-4">
        <button type="button" class="flex w-full items-center justify-between text-left" @click="showRules = !showRules">
          <span class="font-serif text-lg text-ink">餐點規則設定</span>
          <span class="text-xs text-tea">{{ showRules ? '收合' : '展開' }}</span>
        </button>

        <div v-if="showRules" class="mt-3 space-y-4">
          <div>
            <p class="text-sm font-semibold text-ink">湯品星期（兩人共用）</p>
            <p class="text-xs text-tea">勾選這天想在午餐/晚餐多喝一道湯</p>
            <p v-if="soupError" class="mt-2 rounded-lg bg-alert/10 px-3 py-2 text-xs text-alert">{{ soupError }}</p>
            <div class="mt-2 flex flex-wrap gap-2">
              <button
                v-for="(label, dow) in SOUP_WEEKDAY_LABELS"
                :key="dow"
                type="button"
                class="rounded-full border px-3 py-1 text-xs"
                :class="isSoupDay(dow) ? 'border-accent bg-accent text-on-accent' : 'border-ink/15 text-ink hover:bg-bg'"
                @click="toggleSoupDay(dow)"
              >
                {{ label }}
              </button>
            </div>
          </div>

          <div class="border-t border-ink/10 pt-3">
            <div class="flex items-center justify-between">
              <p class="text-sm font-semibold text-ink">黑名單（兩人共用）</p>
              <button type="button" class="text-xs font-semibold text-accent hover:text-accent-bright" @click="openExcludedPicker">
                加入黑名單
              </button>
            </div>
            <p class="text-xs text-tea">標記「不要再推薦」的食譜，之後產生/重推菜單一律排除</p>
            <p v-if="excludedError" class="mt-2 rounded-lg bg-alert/10 px-3 py-2 text-xs text-alert">{{ excludedError }}</p>
            <ul v-if="excludedRecipes.length" class="mt-2 divide-y divide-ink/10 rounded-xl border border-ink/10 px-3">
              <li v-for="r in excludedRecipes" :key="r.id" class="flex items-center justify-between py-1.5 text-sm">
                <span class="text-ink">{{ r.recipe_name }}</span>
                <button type="button" class="text-xs text-tea hover:text-alert" @click="removeExcluded(r.id)">移除</button>
              </li>
            </ul>
            <p v-else class="mt-2 text-xs text-tea">尚未設定</p>

            <div v-if="excludedPickerOpen" class="mt-3 rounded-xl border border-accent bg-accent-tint/50 p-3">
              <div class="flex items-center justify-between">
                <p class="text-xs text-ink">選一個食譜加入黑名單</p>
                <button type="button" class="text-xs text-tea hover:text-ink" @click="closeExcludedPicker">關閉</button>
              </div>
              <div class="mt-2 flex gap-2">
                <input
                  v-model="excludedQuery"
                  type="text"
                  placeholder="食譜名稱"
                  class="w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
                  @keydown.enter="runExcludedSearch"
                />
                <button
                  type="button"
                  class="shrink-0 rounded-lg border border-ink/15 px-3 py-2 text-xs font-semibold text-ink hover:bg-bg disabled:opacity-50"
                  :disabled="excludedSearching"
                  @click="runExcludedSearch"
                >
                  {{ excludedSearching ? '搜尋中…' : '搜尋' }}
                </button>
              </div>
              <ul v-if="excludedResults.length" class="mt-2 divide-y divide-ink/10">
                <li v-for="r in excludedResults" :key="r.id" class="flex items-center justify-between py-1.5 text-sm">
                  <span class="text-ink">{{ r.recipe_name }}<span class="text-tea">（{{ r.category }}）</span></span>
                  <button
                    type="button"
                    class="text-xs font-semibold text-accent hover:text-accent-bright disabled:opacity-50"
                    :disabled="excludedSaving"
                    @click="chooseExcludedRecipe(r.id)"
                  >
                    選這個
                  </button>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section class="mt-4 rounded-2xl border border-ink/10 bg-surface p-4">
        <button type="button" class="flex w-full items-center justify-between text-left" @click="showFavorites = !showFavorites">
          <span class="font-serif text-lg text-ink">最愛清單</span>
          <span class="text-xs text-tea">{{ showFavorites ? '收合' : '展開' }}</span>
        </button>

        <div v-if="showFavorites" class="mt-3">
          <p class="text-xs text-tea">常常想吃、但不用每次都吃的菜，選餐評分時會軟性加分，比較容易被選到（不像固定餐點會鎖死）</p>
          <p v-if="favoritesError" class="mt-2 rounded-lg bg-alert/10 px-3 py-2 text-xs text-alert">{{ favoritesError }}</p>

          <div v-for="user in [userA, userB]" :key="user ? `fav-${user.id}` : ''" class="mt-2">
            <div v-if="user" class="rounded-xl border border-ink/10 p-3">
              <div class="flex items-center justify-between">
                <p class="text-sm font-semibold text-ink">{{ user.name }}</p>
                <button type="button" class="text-xs font-semibold text-accent hover:text-accent-bright" @click="openFavoritePicker(user.id)">
                  加入最愛
                </button>
              </div>
              <ul v-if="favoriteRecipes.filter((r) => r.user_id === user.id).length" class="mt-2 divide-y divide-ink/10">
                <li
                  v-for="r in favoriteRecipes.filter((r2) => r2.user_id === user.id)"
                  :key="r.id"
                  class="flex items-center justify-between py-1 text-sm"
                >
                  <span class="text-ink">{{ r.recipe_name }}</span>
                  <button type="button" class="text-xs text-tea hover:text-alert" @click="removeFavorite(r.id)">移除</button>
                </li>
              </ul>
              <p v-else class="mt-2 text-xs text-tea">尚未設定</p>
            </div>
          </div>

          <div v-if="favoritePickerUserId !== null" class="mt-3 rounded-xl border border-accent bg-accent-tint/50 p-3">
            <div class="flex items-center justify-between">
              <p class="text-xs text-ink">選一個食譜加入{{ userName(favoritePickerUserId) }}的最愛</p>
              <button type="button" class="text-xs text-tea hover:text-ink" @click="closeFavoritePicker">關閉</button>
            </div>
            <div class="mt-2 flex gap-2">
              <input
                v-model="favoriteQuery"
                type="text"
                placeholder="食譜名稱"
                class="w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
                @keydown.enter="runFavoriteSearch"
              />
              <button
                type="button"
                class="shrink-0 rounded-lg border border-ink/15 px-3 py-2 text-xs font-semibold text-ink hover:bg-bg disabled:opacity-50"
                :disabled="favoriteSearching"
                @click="runFavoriteSearch"
              >
                {{ favoriteSearching ? '搜尋中…' : '搜尋' }}
              </button>
            </div>
            <ul v-if="favoriteResults.length" class="mt-2 divide-y divide-ink/10">
              <li v-for="r in favoriteResults" :key="r.id" class="flex items-center justify-between py-1.5 text-sm">
                <span class="text-ink">{{ r.recipe_name }}<span class="text-tea">（{{ r.category }}）</span></span>
                <button
                  type="button"
                  class="text-xs font-semibold text-accent hover:text-accent-bright disabled:opacity-50"
                  :disabled="favoriteSaving"
                  @click="chooseFavoriteRecipe(r.id)"
                >
                  選這個
                </button>
              </li>
            </ul>
          </div>
        </div>
      </section>

      <div v-if="!plan && !loadingPlan" class="mt-4 rounded-2xl border border-ink/10 bg-surface p-6">
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
            <div class="relative flex items-center gap-2">
              <h1 class="font-serif text-2xl text-ink">{{ plan.plan_date }} 那一週</h1>
              <button
                type="button"
                class="rounded-full border border-ink/15 px-2.5 py-1 text-xs font-semibold text-ink hover:bg-bg"
                @click="showWeekPicker = !showWeekPicker"
              >
                查看其他週 {{ showWeekPicker ? '▴' : '▾' }}
              </button>

              <div
                v-if="showWeekPicker"
                class="absolute left-0 top-full z-20 mt-1 max-h-72 w-64 overflow-y-auto rounded-xl border border-ink/10 bg-surface p-2 shadow-lg"
              >
                <p v-if="otherPlansLoading" class="px-2 py-1 text-xs text-tea">載入中…</p>
                <p v-else-if="otherPlans.length === 0" class="px-2 py-1 text-xs text-tea">還沒有其他週的紀錄</p>
                <div
                  v-for="p in otherPlans"
                  :key="p.id"
                  class="flex w-full items-center justify-between rounded-lg px-2 py-1 text-sm"
                  :class="p.id === plan.id ? 'bg-accent-tint text-ink' : 'text-ink hover:bg-bg'"
                >
                  <button type="button" class="min-w-0 flex-1 py-0.5 text-left" @click="switchToPlan(p.id)">
                    <span>{{ p.plan_date }}</span>
                    <span class="ml-1 text-xs text-tea">{{ p.plan_status }}</span>
                  </button>
                  <button
                    type="button"
                    class="shrink-0 pl-2 text-xs text-tea hover:text-alert disabled:opacity-40"
                    :disabled="deletingPlanId === p.id"
                    @click="deletePlan(p.id, p.plan_date)"
                  >
                    {{ deletingPlanId === p.id ? '刪除中…' : '刪除' }}
                  </button>
                </div>
              </div>
            </div>
            <p class="text-xs text-tea">
              狀態：{{ plan.plan_status }} · {{ userA?.name }} 目標 {{ plan.user_a_daily_calories_target }}kcal
              <span v-if="plan.user_a_menstrual_phase && plan.user_a_menstrual_phase !== '無'">
                （{{ plan.user_a_menstrual_phase }}）
              </span>
              · {{ userB?.name }} 目標 {{ plan.user_b_daily_calories_target }}kcal
            </p>
          </div>
          <div class="flex shrink-0 items-start gap-2">
            <button
              type="button"
              class="rounded-full border border-accent px-4 py-2 text-sm font-semibold text-accent hover:bg-accent hover:text-on-accent disabled:opacity-50"
              :disabled="regeneratingWeek"
              @click="submitRegenerateWeek"
            >
              {{ regeneratingWeek ? '推薦中…' : '整週重新推薦' }}
            </button>
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
        </div>
        <p v-if="confirmError" class="mt-2 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ confirmError }}</p>
        <p v-if="adjustError" class="mt-2 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ adjustError }}</p>

        <div class="mt-4 flex gap-3 overflow-x-auto pb-2">
          <div
            v-for="day in plan.days"
            :key="day.date"
            class="w-[220px] shrink-0 rounded-2xl border border-ink/10 bg-surface p-3"
            :class="regeneratingDay === day.date && 'opacity-50'"
          >
            <div class="flex items-center justify-between">
              <p class="text-xs font-semibold uppercase tracking-wide text-muted">{{ dayLabel(day) }} · {{ day.date }}</p>
              <div class="flex shrink-0 gap-2">
                <button
                  type="button"
                  class="text-[11px] font-semibold text-accent hover:text-accent-bright disabled:opacity-40"
                  :disabled="rebalancingDay !== null"
                  @click="submitRebalanceDay(day.date)"
                  title="菜色不變，依熱量目標重新分配份量"
                >
                  {{ rebalancingDay === day.date ? '計算中…' : '重算份量' }}
                </button>
                <button
                  type="button"
                  class="text-[11px] font-semibold text-accent hover:text-accent-bright disabled:opacity-40"
                  :disabled="regeneratingDay !== null"
                  @click="submitRegenerateDay(day.date)"
                >
                  {{ regeneratingDay === day.date ? '推薦中…' : '重新推薦' }}
                </button>
              </div>
            </div>

            <p v-if="dayMealTypeViews(day).length === 0" class="mt-2 text-xs text-tea">尚無安排</p>

            <div v-else class="mt-2 space-y-2.5">
              <div v-for="mt in dayMealTypeViews(day)" :key="mt.type">
                <button
                  type="button"
                  class="flex items-center gap-1 text-[11px] text-tea hover:text-accent"
                  @click="openMealEditor(day.date, mt.type as MealType)"
                >
                  <span aria-hidden="true">{{ mt.icon }}</span>{{ mt.label }}
                  <span class="text-muted" aria-hidden="true">✎</span>
                </button>
                <div class="mt-1 space-y-1" :class="mt.slots.length > 1 && 'pl-4'">
                  <div v-for="slot in mt.slots" :key="slot.category ?? 'single'" class="flex flex-wrap items-baseline gap-x-1 text-xs">
                    <span v-if="slot.category" aria-hidden="true">{{ slot.icon }}</span>
                    <span class="font-medium text-ink">{{ slot.primary.recipe_name }}</span>
                    <span class="text-muted">
                      · {{ slot.primary.serving_weight_g }}g<template v-if="slot.otherWeightG !== null">／{{ slot.otherWeightG }}g</template>
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <div v-if="dayDiffItems(day).length > 0" class="mt-2.5 border-t border-ink/10 pt-2">
              <button
                type="button"
                class="flex items-center gap-1 text-[11px] font-semibold text-accent hover:text-accent-bright"
                @click="toggleDiffExpanded(day.date)"
              >
                <span aria-hidden="true">{{ expandedDiffDates.has(day.date) ? '▾' : '▸' }}</span>
                {{ dayDiffItems(day).length }} 項差異
              </button>
              <div v-if="expandedDiffDates.has(day.date)" class="mt-1.5 space-y-1.5">
                <div v-for="d in dayDiffItems(day)" :key="d.key" class="flex items-start gap-1.5 text-[11px]">
                  <span class="shrink-0 rounded-full bg-accent-tint px-1.5 py-0.5 text-ink">{{ userName(d.item.assigned_user_id) }}</span>
                  <button type="button" class="text-left text-ink hover:text-accent" @click="openMealEditor(day.date, d.type as MealType)">
                    {{ d.mealLabel }}<template v-if="d.category">・{{ d.category }}</template>
                    改吃 {{ d.item.recipe_name }} · {{ d.item.serving_weight_g }}g
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <section v-if="plan.plan_status === '已確認'" class="mt-4 rounded-2xl border border-ink/10 bg-surface p-4">
          <button type="button" class="flex w-full items-center justify-between text-left" @click="showPrepPlan = !showPrepPlan">
            <span class="font-serif text-lg text-ink">備料規劃</span>
            <span class="text-xs text-tea">{{ showPrepPlan ? '收合' : '展開' }}</span>
          </button>

          <div v-if="showPrepPlan" class="mt-3">
            <p v-if="prepPlanLoading" class="text-xs text-tea">載入中…</p>
            <p v-if="prepPlanError" class="rounded-lg bg-alert/10 px-3 py-2 text-xs text-alert">{{ prepPlanError }}</p>

            <template v-if="prepPlan">
              <div class="flex gap-3 overflow-x-auto pb-2">
                <div
                  v-for="card in prepPlan.days"
                  :key="card.date"
                  class="w-[240px] shrink-0 rounded-2xl border p-3"
                  :class="card.prep_session ? 'border-accent bg-accent-tint/30' : 'border-ink/10 bg-surface'"
                >
                  <p class="text-xs font-semibold uppercase tracking-wide text-muted">{{ card.weekday_label }} · {{ card.date }}</p>

                  <div v-if="card.prep_session" class="mt-2">
                    <p class="text-xs font-semibold text-ink">
                      🍱 備 {{ card.prep_session.for_dates.join('、') }} 便當{{ card.prep_session.meat_batch ? '＋整週肉類批次' : '' }}
                    </p>
                    <ol class="mt-1.5 list-decimal space-y-1 pl-4 text-[11px] text-ink">
                      <li v-for="(s, i) in card.prep_session.steps" :key="i">{{ s }}</li>
                    </ol>
                  </div>

                  <div v-if="card.dinner" class="mt-2.5 border-t border-ink/10 pt-2">
                    <p class="text-[11px] font-semibold text-tea">🌙 晚餐</p>
                    <p class="mt-0.5 text-xs text-ink">{{ dayMealSummary(card.dinner) }}</p>
                  </div>

                  <div v-if="card.lunch_fresh" class="mt-2 border-t border-ink/10 pt-2">
                    <p class="text-[11px] font-semibold text-tea">🍚 午餐（非便當，現煮）</p>
                    <p class="mt-0.5 text-xs text-ink">{{ dayMealSummary(card.lunch_fresh) }}</p>
                  </div>
                  <p v-else-if="card.lunch_is_bento" class="mt-2 border-t border-ink/10 pt-2 text-[11px] text-tea">🍱 中午帶便當</p>
                </div>
              </div>

              <p class="mt-2 text-[11px] text-muted">杯數換算假設：1 杯生米約煮出 {{ prepPlan.rice_cup_assumption_g }}g 熟飯，可依實際狀況再調整</p>
            </template>
          </div>
        </section>

        <!-- 編輯面板：改成靠右側滑出的視窗，蓋在畫面上，不會把下面的內容往下推 -->
        <Teleport to="body">
          <div v-if="mealEditor" class="fixed inset-0 z-30 flex justify-end">
            <div class="absolute inset-0 bg-ink/30" @click="closeMealEditor" />
            <section class="relative flex h-full w-full max-w-md flex-col overflow-y-auto border-l border-accent bg-accent-tint/50 p-4 shadow-xl">
              <div class="flex items-center justify-between">
                <p class="text-sm text-ink">編輯：{{ mealEditor.date }} {{ mealTypeLabel(mealEditor.mealType) }}</p>
                <button type="button" class="text-xs text-tea hover:text-ink" @click="closeMealEditor">關閉 ✕</button>
              </div>
              <p class="mt-1 text-xs text-tea">
                可以自由新增/移除這一餐的食譜，或勾選多道菜一起處理。組成改變後份量會先概略分配，按「重算份量」依熱量目標重新精算整天的份量。
              </p>

              <div v-if="mealEditorSelected.size > 0" class="mt-3 flex flex-wrap items-center gap-2 rounded-xl border border-accent bg-surface px-3 py-2">
                <span class="text-xs font-semibold text-ink">已選 {{ mealEditorSelected.size }} 項</span>
                <button type="button" class="text-xs font-semibold text-accent hover:text-accent-bright" :disabled="mealEditorBusy" @click="startBulkReplace">
                  一起換成…
                </button>
                <button type="button" class="text-xs text-tea hover:text-alert" :disabled="mealEditorBusy" @click="removeSelectedDishes">
                  一起移除
                </button>
                <button type="button" class="ml-auto text-xs text-tea hover:text-ink" @click="clearMealEditorSelection">取消選取</button>
              </div>

              <ul v-if="mealEditorDishes().length" class="mt-3 divide-y divide-ink/10 rounded-xl border border-ink/10 bg-surface px-3">
                <li v-for="d in mealEditorDishes()" :key="d.id" class="flex items-center justify-between gap-2 py-2 text-sm">
                  <label class="flex min-w-0 items-center gap-2">
                    <input
                      type="checkbox"
                      class="shrink-0 accent-accent"
                      :checked="mealEditorSelected.has(d.id)"
                      @change="toggleMealEditorSelected(d.id)"
                    />
                    <span class="min-w-0">
                      <span class="text-ink">{{ d.recipe_name }}</span>
                      <span class="ml-1 text-xs text-tea">{{ userName(d.assigned_user_id) }} · {{ d.serving_weight_g }}g</span>
                    </span>
                  </label>
                  <div class="flex shrink-0 gap-2">
                    <button type="button" class="text-xs font-semibold text-accent hover:text-accent-bright" :disabled="mealEditorBusy" @click="startReplaceDish(d.id)">
                      換一道
                    </button>
                    <button type="button" class="text-xs text-tea hover:text-alert" :disabled="mealEditorBusy" @click="removeMealEditorDish(d.id)">
                      移除
                    </button>
                  </div>
                </li>
              </ul>
              <p v-else class="mt-3 text-xs text-tea">這一餐目前沒有菜</p>

              <div class="mt-3 rounded-xl border border-ink/15 bg-surface p-3">
                <div class="flex items-center justify-between">
                  <p class="text-xs font-semibold text-ink">
                    {{ mealEditorReplacingIds.length > 1 ? `選一道換掉選取的 ${mealEditorReplacingIds.length} 道菜` : mealEditorReplacingIds.length === 1 ? '選一道換掉上面那道菜' : '新增食譜' }}
                  </p>
                  <button v-if="mealEditorReplacingIds.length > 0" type="button" class="text-xs text-tea hover:text-ink" @click="cancelReplaceDish">
                    取消換菜
                  </button>
                </div>
                <div v-if="mealEditorReplacingIds.length === 0 && FIXED_MEAL_TYPES.includes(mealEditor.mealType as FixedMealType)" class="mt-2 flex gap-2">
                  <button
                    v-for="user in [userA, userB]"
                    :key="user ? user.id : ''"
                    type="button"
                    class="rounded-full border px-3 py-1 text-xs"
                    :class="user && mealEditorAddUserId === user.id ? 'border-accent bg-accent text-on-accent' : 'border-ink/15 text-ink hover:bg-bg'"
                    @click="user && (mealEditorAddUserId = user.id)"
                  >
                    加給 {{ user?.name }}
                  </button>
                </div>
                <div class="mt-2 flex gap-2">
                  <input
                    v-model="mealEditorQuery"
                    type="text"
                    placeholder="食譜名稱"
                    class="w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
                    @keydown.enter="runMealEditorSearch"
                  />
                  <button
                    type="button"
                    class="shrink-0 rounded-lg border border-ink/15 px-3 py-2 text-xs font-semibold text-ink hover:bg-bg disabled:opacity-50"
                    :disabled="mealEditorSearching"
                    @click="runMealEditorSearch"
                  >
                    {{ mealEditorSearching ? '搜尋中…' : '搜尋' }}
                  </button>
                </div>
                <div v-if="recentMealSearches.length" class="mt-2 flex flex-wrap gap-1.5">
                  <span class="text-[11px] text-tea">最近查過：</span>
                  <button
                    v-for="q in recentMealSearches"
                    :key="q"
                    type="button"
                    class="rounded-full border border-ink/15 px-2 py-0.5 text-[11px] text-ink hover:bg-bg"
                    @click="useRecentMealSearch(q)"
                  >
                    {{ q }}
                  </button>
                </div>
                <ul v-if="mealEditorResults.length" class="mt-2 divide-y divide-ink/10">
                  <li v-for="r in mealEditorResults" :key="r.id" class="flex items-center justify-between py-1.5 text-sm">
                    <span class="text-ink">{{ r.recipe_name }}<span class="text-tea">（{{ r.category }}・{{ r.cost_level }}）</span></span>
                    <button
                      type="button"
                      class="text-xs font-semibold text-accent hover:text-accent-bright disabled:opacity-50"
                      :disabled="mealEditorBusy"
                      @click="chooseMealEditorRecipe(r.id)"
                    >
                      選這個
                    </button>
                  </li>
                </ul>
              </div>

              <button
                type="button"
                class="mt-3 w-full rounded-full border border-accent py-2 text-xs font-semibold text-accent hover:bg-accent hover:text-on-accent disabled:opacity-50"
                :disabled="rebalancingDay !== null"
                @click="submitRebalanceDay(mealEditor.date)"
              >
                {{ rebalancingDay === mealEditor.date ? '計算中…' : '重算這天的份量' }}
              </button>
            </section>
          </div>
        </Teleport>
      </template>
    </template>
  </div>
</template>

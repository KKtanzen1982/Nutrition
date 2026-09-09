<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { searchIngredientsByName } from './ingredient_api'
import {
  addRecipeStepsVersion,
  createRecipe,
  deleteRecipe,
  fetchRecipe,
  listRecipes,
  recalculateRecipeNutrition,
  searchRecipesByName,
  setRecipeStepsAsCurrent,
  updateRecipe,
  updateRecipeIngredients,
} from './recipe_api'
import { useConfirmDialog } from '../shared/useConfirmDialog'
import type { IngredientSearchResult, RecipeDetail, RecipeListEntry, RecipeSearchResult } from '../shared/types'

const { confirmDialog } = useConfirmDialog()

const RECIPE_CATEGORIES = ['早餐', '主食', '肉', '菜', '飲料', '點心']
const COST_LEVELS = ['低', '中', '高']

interface IngredientRow {
  ingredient_id: number
  ingredient_name: string
  quantity_g: number | null
  unit: string
}

const query = ref('')
const categoryFilter = ref('')
const costFilter = ref('')
const page = ref(1)
const limit = 20

const items = ref<RecipeListEntry[]>([])
const searchResults = ref<RecipeSearchResult[] | null>(null)
const total = ref(0)
const loading = ref(true)
const error = ref<string | null>(null)

async function loadBrowse() {
  loading.value = true
  error.value = null
  try {
    const res = await listRecipes(categoryFilter.value || undefined, costFilter.value || undefined, page.value, limit)
    items.value = res.items
    total.value = res.total
  } catch (e) {
    error.value = e instanceof Error ? e.message : '讀取食譜清單失敗'
  } finally {
    loading.value = false
  }
}

async function loadSearch() {
  loading.value = true
  error.value = null
  try {
    searchResults.value = await searchRecipesByName(query.value.trim())
  } catch (e) {
    error.value = e instanceof Error ? e.message : '搜尋失敗'
  } finally {
    loading.value = false
  }
}

function reload() {
  if (query.value.trim()) {
    loadSearch()
  } else {
    searchResults.value = null
    loadBrowse()
  }
}

watch([categoryFilter, costFilter, page], reload)
reload()

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit)))

let searchDebounce: ReturnType<typeof setTimeout> | undefined
function onQueryInput() {
  clearTimeout(searchDebounce)
  searchDebounce = setTimeout(() => {
    page.value = 1
    reload()
  }, 350)
}

const selectedId = ref<number | null>(null)
const detail = ref<RecipeDetail | null>(null)
const detailLoading = ref(false)
const detailError = ref<string | null>(null)

async function openDetail(id: number) {
  selectedId.value = id
  detail.value = null
  detailLoading.value = true
  detailError.value = null
  try {
    detail.value = await fetchRecipe(id)
  } catch (e) {
    detailError.value = e instanceof Error ? e.message : '讀取食譜詳情失敗'
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  selectedId.value = null
  detail.value = null
}

// GET /recipes/:id 的 steps 其實是「所有版本」混在一起（後端 Recipe.steps 關聯沒有過濾 is_current），
// 不能直接當成「目前版本」顯示，要自己依 is_current / version 分組。
const currentSteps = computed(() => {
  if (!detail.value) return []
  return detail.value.steps.filter((s) => s.is_current).sort((a, b) => a.step_number - b.step_number)
})

const stepVersions = computed(() => {
  if (!detail.value) return []
  const byVersion = new Map<number, typeof detail.value.steps>()
  for (const s of detail.value.steps) {
    if (!byVersion.has(s.version)) byVersion.set(s.version, [])
    byVersion.get(s.version)!.push(s)
  }
  return [...byVersion.entries()]
    .map(([version, steps]) => ({
      version,
      isCurrent: steps.some((s) => s.is_current),
      steps: [...steps].sort((a, b) => a.step_number - b.step_number),
    }))
    .sort((a, b) => b.version - a.version)
})

const settingCurrentVersion = ref<number | null>(null)
async function makeVersionCurrent(version: number) {
  if (!detail.value) return
  settingCurrentVersion.value = version
  detailError.value = null
  try {
    await setRecipeStepsAsCurrent(detail.value.id, version)
    detail.value = await fetchRecipe(detail.value.id)
  } catch (e) {
    detailError.value = e instanceof Error ? e.message : '切換版本失敗'
  } finally {
    settingCurrentVersion.value = null
  }
}

const showAddStepVersion = ref(false)
const newStepRows = ref<string[]>([''])
const addingStepVersion = ref(false)
const addStepVersionError = ref<string | null>(null)

function addNewStepRow() {
  newStepRows.value.push('')
}
function removeNewStepRow(index: number) {
  newStepRows.value.splice(index, 1)
}

async function submitAddStepVersion() {
  if (!detail.value) return
  const steps = newStepRows.value
    .filter((s) => s.trim())
    .map((step_description, i) => ({ step_number: i + 1, step_description }))
  if (steps.length === 0) return

  addingStepVersion.value = true
  addStepVersionError.value = null
  try {
    await addRecipeStepsVersion(detail.value.id, steps)
    detail.value = await fetchRecipe(detail.value.id)
    newStepRows.value = ['']
    showAddStepVersion.value = false
  } catch (e) {
    addStepVersionError.value = e instanceof Error ? e.message : '新增步驟版本失敗'
  } finally {
    addingStepVersion.value = false
  }
}

const editingBasic = ref(false)
const basicForm = reactive({ recipe_name: '', category: '', base_weight_g: 0, cost_level: '' })
const savingBasic = ref(false)

function startEditBasic() {
  if (!detail.value) return
  Object.assign(basicForm, {
    recipe_name: detail.value.recipe_name,
    category: detail.value.category,
    base_weight_g: detail.value.base_weight_g,
    cost_level: detail.value.cost_level,
  })
  editingBasic.value = true
}

async function submitEditBasic() {
  if (!detail.value) return
  savingBasic.value = true
  detailError.value = null
  try {
    detail.value = await updateRecipe(detail.value.id, { ...basicForm })
    editingBasic.value = false
    reload()
  } catch (e) {
    detailError.value = e instanceof Error ? e.message : '更新失敗'
  } finally {
    savingBasic.value = false
  }
}

// ---- 編輯食材：整組取代（跟建立食譜時同一套搜尋加入 UI），儲存後後端會自動重算營養素 ----
const editingIngredients = ref(false)
const editIngredientRows = ref<IngredientRow[]>([])
const editIngSearchQuery = ref('')
const editIngSearchResults = ref<IngredientSearchResult[]>([])
const editIngSearching = ref(false)
const savingIngredients = ref(false)

function startEditIngredients() {
  if (!detail.value) return
  editIngredientRows.value = detail.value.ingredients.map((ing) => ({
    ingredient_id: ing.ingredient_id,
    ingredient_name: ing.ingredient?.ingredient_name ?? `食材 #${ing.ingredient_id}`,
    quantity_g: ing.quantity_g,
    unit: ing.unit,
  }))
  editIngSearchQuery.value = ''
  editIngSearchResults.value = []
  editingIngredients.value = true
}
function cancelEditIngredients() {
  editingIngredients.value = false
}

async function runEditIngredientSearch() {
  if (!editIngSearchQuery.value.trim()) return
  editIngSearching.value = true
  try {
    editIngSearchResults.value = await searchIngredientsByName(editIngSearchQuery.value.trim())
  } catch {
    editIngSearchResults.value = []
  } finally {
    editIngSearching.value = false
  }
}

function addEditIngredientRow(ing: IngredientSearchResult) {
  if (editIngredientRows.value.some((r) => r.ingredient_id === ing.id)) return
  editIngredientRows.value.push({ ingredient_id: ing.id, ingredient_name: ing.ingredient_name, quantity_g: null, unit: ing.unit })
}
function removeEditIngredientRow(index: number) {
  editIngredientRows.value.splice(index, 1)
}

const canSubmitEditIngredients = computed(
  () => editIngredientRows.value.length > 0 && editIngredientRows.value.every((r) => r.quantity_g !== null),
)

async function submitEditIngredients() {
  if (!detail.value || !canSubmitEditIngredients.value) return
  savingIngredients.value = true
  detailError.value = null
  try {
    detail.value = await updateRecipeIngredients(
      detail.value.id,
      editIngredientRows.value.map((r) => ({ ingredient_id: r.ingredient_id, quantity_g: r.quantity_g as number, unit: r.unit })),
    )
    editingIngredients.value = false
  } catch (e) {
    detailError.value = e instanceof Error ? e.message : '更新食材失敗'
  } finally {
    savingIngredients.value = false
  }
}

const recalculating = ref(false)
async function recalcNutrition() {
  if (!detail.value) return
  recalculating.value = true
  try {
    await recalculateRecipeNutrition(detail.value.id)
    detail.value = await fetchRecipe(detail.value.id)
  } catch (e) {
    detailError.value = e instanceof Error ? e.message : '重新計算失敗'
  } finally {
    recalculating.value = false
  }
}

async function removeRecipe() {
  if (!detail.value) return
  if (!(await confirmDialog(`刪除食譜「${detail.value.recipe_name}」？`))) return
  try {
    await deleteRecipe(detail.value.id)
    closeDetail()
    reload()
  } catch (e) {
    detailError.value = e instanceof Error ? e.message : '刪除失敗'
  }
}

const showCreate = ref(false)
const createForm = reactive({
  recipe_name: '',
  category: RECIPE_CATEGORIES[0],
  base_weight_g: null as number | null,
  cost_level: COST_LEVELS[0],
})
const ingredientRows = ref<IngredientRow[]>([])
const stepRows = ref<string[]>([''])
const ingSearchQuery = ref('')
const ingSearchResults = ref<IngredientSearchResult[]>([])
const ingSearching = ref(false)
const creating = ref(false)
const createError = ref<string | null>(null)

async function runIngredientSearch() {
  if (!ingSearchQuery.value.trim()) return
  ingSearching.value = true
  try {
    ingSearchResults.value = await searchIngredientsByName(ingSearchQuery.value.trim())
  } catch {
    ingSearchResults.value = []
  } finally {
    ingSearching.value = false
  }
}

function addIngredientRow(ing: IngredientSearchResult) {
  if (ingredientRows.value.some((r) => r.ingredient_id === ing.id)) return
  ingredientRows.value.push({ ingredient_id: ing.id, ingredient_name: ing.ingredient_name, quantity_g: null, unit: ing.unit })
}
function removeIngredientRow(index: number) {
  ingredientRows.value.splice(index, 1)
}
function addStepRow() {
  stepRows.value.push('')
}
function removeStepRow(index: number) {
  stepRows.value.splice(index, 1)
}

const canSubmitCreate = computed(
  () =>
    createForm.recipe_name.trim() !== '' &&
    createForm.base_weight_g !== null &&
    ingredientRows.value.length > 0 &&
    ingredientRows.value.every((r) => r.quantity_g !== null) &&
    stepRows.value.some((s) => s.trim()),
)

async function submitCreate() {
  if (!canSubmitCreate.value || createForm.base_weight_g === null) return
  creating.value = true
  createError.value = null
  try {
    await createRecipe({
      recipe_name: createForm.recipe_name,
      category: createForm.category,
      base_weight_g: createForm.base_weight_g,
      cost_level: createForm.cost_level,
      ingredients: ingredientRows.value.map((r) => ({
        ingredient_id: r.ingredient_id,
        quantity_g: r.quantity_g as number,
        unit: r.unit,
      })),
      steps: stepRows.value
        .filter((s) => s.trim())
        .map((step_description, i) => ({ step_number: i + 1, step_description })),
    })
    createForm.recipe_name = ''
    createForm.base_weight_g = null
    ingredientRows.value = []
    stepRows.value = ['']
    showCreate.value = false
    page.value = 1
    reload()
  } catch (e) {
    createError.value = e instanceof Error ? e.message : '新增食譜失敗'
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-3xl px-4 py-8">
    <div class="flex items-center justify-between gap-3">
      <h1 class="font-serif text-2xl text-ink">食譜庫</h1>
      <button
        type="button"
        class="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-bright"
        @click="showCreate = !showCreate"
      >
        {{ showCreate ? '取消新增' : '+ 新增食譜' }}
      </button>
    </div>

    <section v-if="showCreate" class="mt-4 rounded-2xl border border-ink/10 bg-surface p-6">
      <div class="flex items-center gap-1.5">
        <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-ink" aria-hidden="true" />
        <h2 class="border-b-[1.5px] border-accent pb-1 text-[11.5px] font-semibold uppercase tracking-wide text-muted">新增食譜</h2>
      </div>

      <div class="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <input v-model="createForm.recipe_name" type="text" placeholder="食譜名稱" class="rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink sm:col-span-2" />
        <select v-model="createForm.category" class="rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink">
          <option v-for="c in RECIPE_CATEGORIES" :key="c" :value="c">{{ c }}</option>
        </select>
        <select v-model="createForm.cost_level" class="rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink">
          <option v-for="c in COST_LEVELS" :key="c" :value="c">{{ c }}</option>
        </select>
        <input v-model.number="createForm.base_weight_g" type="number" placeholder="基礎重量 (g)" class="rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink sm:col-span-4" />
      </div>

      <div class="mt-4">
        <p class="text-xs text-tea">食材（至少 1 種）</p>
        <div class="mt-1 flex gap-2">
          <input
            v-model="ingSearchQuery"
            type="text"
            placeholder="搜尋食材名稱"
            class="min-w-0 flex-1 rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
            @keydown.enter="runIngredientSearch"
          />
          <button type="button" class="shrink-0 rounded-lg border border-ink/15 px-3 py-2 text-xs font-semibold text-ink hover:bg-bg" :disabled="ingSearching" @click="runIngredientSearch">
            {{ ingSearching ? '搜尋中…' : '搜尋' }}
          </button>
        </div>
        <ul v-if="ingSearchResults.length" class="mt-2 divide-y divide-ink/10 rounded-lg border border-ink/10">
          <li v-for="ing in ingSearchResults" :key="ing.id" class="flex items-center justify-between px-3 py-1.5 text-sm">
            <span class="text-ink">{{ ing.ingredient_name }}<span class="text-tea">（{{ ing.category }}）</span></span>
            <button type="button" class="text-xs font-semibold text-accent hover:text-accent-bright" @click="addIngredientRow(ing)">加入</button>
          </li>
        </ul>
        <div v-for="(row, i) in ingredientRows" :key="row.ingredient_id" class="mt-2 flex items-center gap-2">
          <span class="min-w-0 flex-1 truncate text-sm text-ink">{{ row.ingredient_name }}</span>
          <input v-model.number="row.quantity_g" type="number" placeholder="用量" class="w-24 rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
          <span class="text-xs text-tea">{{ row.unit }}</span>
          <button type="button" class="text-xs text-tea hover:text-alert" @click="removeIngredientRow(i)">刪除</button>
        </div>
      </div>

      <div class="mt-4">
        <div class="flex items-center justify-between">
          <p class="text-xs text-tea">製作步驟（至少 1 個）</p>
          <button type="button" class="text-xs font-semibold text-accent hover:text-accent-bright" @click="addStepRow">+ 新增步驟</button>
        </div>
        <div v-for="(_, i) in stepRows" :key="i" class="mt-2 flex items-center gap-2">
          <span class="w-5 shrink-0 text-sm text-tea">{{ i + 1 }}.</span>
          <input v-model="stepRows[i]" type="text" placeholder="步驟說明" class="min-w-0 flex-1 rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
          <button type="button" class="shrink-0 text-xs text-tea hover:text-alert" @click="removeStepRow(i)">刪除</button>
        </div>
      </div>

      <p v-if="createError" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ createError }}</p>
      <button
        type="button"
        class="mt-4 w-full rounded-full bg-accent py-2.5 text-sm font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
        :disabled="creating || !canSubmitCreate"
        @click="submitCreate"
      >
        {{ creating ? '新增中…' : '新增食譜' }}
      </button>
    </section>

    <div class="mt-6 flex flex-wrap gap-2">
      <input
        v-model="query"
        type="text"
        placeholder="搜尋食譜名稱"
        class="min-w-0 flex-1 rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
        @input="onQueryInput"
      />
      <select v-model="categoryFilter" class="rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink">
        <option value="">全部分類</option>
        <option v-for="c in RECIPE_CATEGORIES" :key="c" :value="c">{{ c }}</option>
      </select>
      <select v-model="costFilter" class="rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink">
        <option value="">全部成本</option>
        <option v-for="c in COST_LEVELS" :key="c" :value="c">{{ c }}</option>
      </select>
    </div>

    <p v-if="loading" class="mt-4 text-sm text-tea">載入中…</p>
    <p v-if="error" class="mt-4 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ error }}</p>

    <ul v-if="searchResults && !loading" class="mt-4 divide-y divide-ink/10 rounded-2xl border border-ink/10 bg-surface">
      <li v-for="r in searchResults" :key="r.id" class="flex cursor-pointer items-center justify-between p-4" @click="openDetail(r.id)">
        <div>
          <p class="text-sm text-ink">{{ r.recipe_name }}</p>
          <p class="text-xs text-tea">{{ r.category }} · {{ r.cost_level }}</p>
        </div>
        <span class="font-serif text-lg text-ink">{{ r.total_calories_kcal ?? '—' }}<small class="text-sm text-tea">kcal</small></span>
      </li>
      <li v-if="searchResults.length === 0" class="p-4 text-sm text-tea">沒有符合的食譜</li>
    </ul>

    <template v-else-if="!loading">
      <ul class="mt-4 divide-y divide-ink/10 rounded-2xl border border-ink/10 bg-surface">
        <li v-for="r in items" :key="r.id" class="flex cursor-pointer items-center justify-between p-4" @click="openDetail(r.id)">
          <div>
            <p class="text-sm text-ink">{{ r.recipe_name }}</p>
            <p class="text-xs text-tea">{{ r.category }} · {{ r.cost_level }}</p>
          </div>
          <span class="font-serif text-lg text-ink">{{ r.nutrition?.total_calories_kcal ?? '—' }}<small class="text-sm text-tea">kcal</small></span>
        </li>
        <li v-if="items.length === 0" class="p-4 text-sm text-tea">沒有符合的食譜</li>
      </ul>

      <div v-if="totalPages > 1" class="mt-4 flex items-center justify-center gap-3 text-sm text-tea">
        <button type="button" class="disabled:opacity-30" :disabled="page <= 1" @click="page -= 1">上一頁</button>
        <span>{{ page }} / {{ totalPages }}</span>
        <button type="button" class="disabled:opacity-30" :disabled="page >= totalPages" @click="page += 1">下一頁</button>
      </div>
    </template>

    <!-- 選食譜來看/編輯改成靠右側滑出的視窗，不用在清單下面捲半天才找得到 -->
    <Teleport to="body">
      <div v-if="selectedId !== null" class="fixed inset-0 z-30 flex justify-end">
        <div class="absolute inset-0 bg-ink/35" @click="closeDetail" />
        <section class="relative flex h-full w-full max-w-md flex-col overflow-y-auto border-l-2 border-accent bg-surface p-6 shadow-xl">
      <div class="flex items-center justify-between">
        <h2 class="font-serif text-xl text-ink">{{ detail?.recipe_name ?? '載入中…' }}</h2>
        <button type="button" class="text-xs text-tea hover:text-ink" @click="closeDetail">關閉 ✕</button>
      </div>

      <p v-if="detailLoading" class="mt-3 text-sm text-tea">載入中…</p>
      <p v-if="detailError" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ detailError }}</p>

      <template v-if="detail">
        <div v-if="!editingBasic" class="mt-3 flex items-center justify-between">
          <p class="text-xs text-tea">{{ detail.category }} · {{ detail.cost_level }} · 基礎 {{ detail.base_weight_g }}g</p>
          <button type="button" class="text-xs font-semibold text-accent hover:text-accent-bright" @click="startEditBasic">編輯基本資料</button>
        </div>
        <div v-else class="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          <input v-model="basicForm.recipe_name" type="text" class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink sm:col-span-2" />
          <select v-model="basicForm.category" class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink">
            <option v-for="c in RECIPE_CATEGORIES" :key="c" :value="c">{{ c }}</option>
          </select>
          <select v-model="basicForm.cost_level" class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink">
            <option v-for="c in COST_LEVELS" :key="c" :value="c">{{ c }}</option>
          </select>
          <input v-model.number="basicForm.base_weight_g" type="number" class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
          <button type="button" class="rounded-full bg-accent px-3 py-1 text-xs font-semibold text-on-accent" :disabled="savingBasic" @click="submitEditBasic">
            {{ savingBasic ? '儲存中…' : '儲存' }}
          </button>
          <button type="button" class="text-xs text-tea" @click="editingBasic = false">取消</button>
        </div>

        <div class="mt-4">
          <div class="flex items-center justify-between">
            <p class="text-[11.5px] font-semibold uppercase tracking-wide text-muted">食材</p>
            <button v-if="!editingIngredients" type="button" class="text-xs font-semibold text-accent hover:text-accent-bright" @click="startEditIngredients">
              編輯食材
            </button>
          </div>

          <ul v-if="!editingIngredients" class="mt-1 text-sm text-ink">
            <li v-for="ing in detail.ingredients" :key="ing.id">{{ ing.ingredient?.ingredient_name ?? `食材 #${ing.ingredient_id}` }} · {{ ing.quantity_g }}{{ ing.unit }}</li>
          </ul>

          <div v-else class="mt-2 rounded-lg border border-ink/10 bg-bg p-3">
            <div class="flex gap-2">
              <input
                v-model="editIngSearchQuery"
                type="text"
                placeholder="搜尋食材名稱"
                class="min-w-0 flex-1 rounded-lg border border-ink/15 bg-surface px-3 py-2 text-sm text-ink"
                @keydown.enter="runEditIngredientSearch"
              />
              <button type="button" class="shrink-0 rounded-lg border border-ink/15 px-3 py-2 text-xs font-semibold text-ink hover:bg-surface" :disabled="editIngSearching" @click="runEditIngredientSearch">
                {{ editIngSearching ? '搜尋中…' : '搜尋' }}
              </button>
            </div>
            <ul v-if="editIngSearchResults.length" class="mt-2 divide-y divide-ink/10 rounded-lg border border-ink/10">
              <li v-for="ing in editIngSearchResults" :key="ing.id" class="flex items-center justify-between px-3 py-1.5 text-sm">
                <span class="text-ink">{{ ing.ingredient_name }}<span class="text-tea">（{{ ing.category }}）</span></span>
                <button type="button" class="text-xs font-semibold text-accent hover:text-accent-bright" @click="addEditIngredientRow(ing)">加入</button>
              </li>
            </ul>
            <div v-for="(row, i) in editIngredientRows" :key="row.ingredient_id" class="mt-2 flex items-center gap-2">
              <span class="min-w-0 flex-1 truncate text-sm text-ink">{{ row.ingredient_name }}</span>
              <input v-model.number="row.quantity_g" type="number" placeholder="用量" class="w-24 rounded border border-ink/15 bg-surface px-2 py-1 text-sm text-ink" />
              <span class="text-xs text-tea">{{ row.unit }}</span>
              <button type="button" class="text-xs text-tea hover:text-alert" @click="removeEditIngredientRow(i)">刪除</button>
            </div>
            <p v-if="editIngredientRows.length === 0" class="mt-2 text-xs text-tea">至少需要 1 種食材</p>

            <div class="mt-3 flex gap-2">
              <button
                type="button"
                class="flex-1 rounded-full bg-accent py-2 text-xs font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
                :disabled="savingIngredients || !canSubmitEditIngredients"
                @click="submitEditIngredients"
              >
                {{ savingIngredients ? '儲存中…' : '儲存食材' }}
              </button>
              <button type="button" class="rounded-full border border-ink/15 px-4 py-2 text-xs text-ink hover:bg-surface" @click="cancelEditIngredients">
                取消
              </button>
            </div>
          </div>
        </div>

        <div class="mt-4">
          <p class="text-[11.5px] font-semibold uppercase tracking-wide text-muted">製作步驟</p>
          <ol class="mt-1 list-decimal space-y-1 pl-5 text-sm text-ink">
            <li v-for="s in currentSteps" :key="s.id">{{ s.step_description }}</li>
          </ol>
        </div>

        <div class="mt-4">
          <div class="flex items-center justify-between">
            <p class="text-[11.5px] font-semibold uppercase tracking-wide text-muted">步驟版本</p>
            <button
              type="button"
              class="text-xs font-semibold text-accent hover:text-accent-bright"
              @click="showAddStepVersion = !showAddStepVersion"
            >
              {{ showAddStepVersion ? '取消' : '+ 新增步驟版本' }}
            </button>
          </div>

          <div v-if="showAddStepVersion" class="mt-2 rounded-lg border border-ink/10 bg-bg p-3">
            <p class="text-xs text-tea">會整組取代成目前版本，舊版本仍保留在下面的版本清單裡</p>
            <div v-for="(_, i) in newStepRows" :key="i" class="mt-2 flex items-center gap-2">
              <span class="w-5 shrink-0 text-sm text-tea">{{ i + 1 }}.</span>
              <input
                v-model="newStepRows[i]"
                type="text"
                placeholder="步驟說明"
                class="min-w-0 flex-1 rounded border border-ink/15 bg-surface px-2 py-1 text-sm text-ink"
              />
              <button type="button" class="shrink-0 text-xs text-tea hover:text-alert" @click="removeNewStepRow(i)">刪除</button>
            </div>
            <button type="button" class="mt-2 text-xs font-semibold text-accent hover:text-accent-bright" @click="addNewStepRow">
              + 新增步驟
            </button>
            <p v-if="addStepVersionError" class="mt-2 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ addStepVersionError }}</p>
            <button
              type="button"
              class="mt-3 w-full rounded-full bg-accent py-2 text-sm font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
              :disabled="addingStepVersion || !newStepRows.some((s) => s.trim())"
              @click="submitAddStepVersion"
            >
              {{ addingStepVersion ? '送出中…' : '送出新版本' }}
            </button>
          </div>

          <ul class="mt-2 divide-y divide-ink/10 rounded-lg border border-ink/10">
            <li v-for="v in stepVersions" :key="v.version" class="p-3">
              <div class="flex items-center justify-between">
                <p class="text-sm text-ink">
                  版本 {{ v.version }}
                  <span v-if="v.isCurrent" class="ml-1 rounded-full bg-accent-tint px-2 py-0.5 text-[10px] text-ink">目前版本</span>
                </p>
                <button
                  v-if="!v.isCurrent"
                  type="button"
                  class="shrink-0 text-xs font-semibold text-accent hover:text-accent-bright disabled:opacity-50"
                  :disabled="settingCurrentVersion === v.version"
                  @click="makeVersionCurrent(v.version)"
                >
                  {{ settingCurrentVersion === v.version ? '切換中…' : '設為目前版本' }}
                </button>
              </div>
              <details class="mt-1">
                <summary class="cursor-pointer text-xs text-tea">查看這個版本的步驟</summary>
                <ol class="mt-1 list-decimal space-y-1 pl-5 text-sm text-ink">
                  <li v-for="s in v.steps" :key="s.id">{{ s.step_description }}</li>
                </ol>
              </details>
            </li>
          </ul>
        </div>

        <div class="mt-4 flex items-center justify-between">
          <div>
            <p class="text-[11.5px] font-semibold uppercase tracking-wide text-muted">營養素</p>
            <p v-if="detail.nutrition" class="text-sm text-ink">
              {{ detail.nutrition.total_calories_kcal }}kcal · 蛋白質 {{ detail.nutrition.protein_g }}g · 碳水 {{ detail.nutrition.carbs_g }}g · 脂肪 {{ detail.nutrition.fat_g }}g
            </p>
            <p v-else class="text-sm text-tea">尚未計算</p>
          </div>
          <button type="button" class="shrink-0 rounded-full border border-ink/15 px-3 py-1.5 text-xs font-semibold text-ink hover:bg-bg" :disabled="recalculating" @click="recalcNutrition">
            {{ recalculating ? '計算中…' : '重新計算' }}
          </button>
        </div>

        <button type="button" class="mt-4 text-xs text-tea hover:text-alert" @click="removeRecipe">刪除這個食譜</button>
      </template>
        </section>
      </div>
    </Teleport>
  </div>
</template>

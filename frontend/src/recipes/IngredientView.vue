<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import {
  createIngredient,
  fetchLowStockIngredients,
  listIngredients,
  searchIngredientsByName,
  updateIngredient,
  updateIngredientStock,
} from './ingredient_api'
import {
  fetchIngredientLocationPreferences,
  setIngredientLocationPreferences,
} from '../shopping/ingredient_location_preference_api'
import { listPurchaseLocations } from '../shopping/purchase_location_api'
import type { Ingredient, IngredientSearchResult, LowStockIngredient, PurchaseLocation } from '../shared/types'

const CATEGORIES = ['蔬菜', '肉類', '穀物', '乳製品', '調味料', '其他']
const SEASONS = ['春', '夏', '秋', '冬']
const COST_LEVELS = ['低', '中', '高']

function parseSeasonCsv(season: string | null | undefined): string[] {
  return (season ?? '').split(',').map((s) => s.trim()).filter(Boolean)
}
function toggleSeason(list: string[], s: string): string[] {
  return list.includes(s) ? list.filter((x) => x !== s) : [...list, s]
}

const query = ref('')
const categoryFilter = ref('')
const page = ref(1)
const limit = 20

const items = ref<Ingredient[]>([])
const searchResults = ref<IngredientSearchResult[] | null>(null)
const total = ref(0)
const loading = ref(true)
const error = ref<string | null>(null)

const lowStock = ref<LowStockIngredient[]>([])

async function loadBrowse() {
  loading.value = true
  error.value = null
  try {
    const res = await listIngredients(categoryFilter.value || undefined, page.value, limit)
    items.value = res.items
    total.value = res.total
  } catch (e) {
    error.value = e instanceof Error ? e.message : '讀取食材清單失敗'
  } finally {
    loading.value = false
  }
}

async function loadSearch() {
  loading.value = true
  error.value = null
  try {
    searchResults.value = await searchIngredientsByName(query.value.trim(), categoryFilter.value || undefined)
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

watch([categoryFilter, page], reload)
reload()

async function loadLowStock() {
  try {
    lowStock.value = await fetchLowStockIngredients()
  } catch {
    lowStock.value = []
  }
}
loadLowStock()

const purchaseLocations = ref<PurchaseLocation[]>([])
async function loadPurchaseLocations() {
  try {
    purchaseLocations.value = await listPurchaseLocations()
  } catch {
    purchaseLocations.value = []
  }
}
loadPurchaseLocations()

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit)))

let searchDebounce: ReturnType<typeof setTimeout> | undefined
function onQueryInput() {
  clearTimeout(searchDebounce)
  searchDebounce = setTimeout(() => {
    page.value = 1
    reload()
  }, 350)
}

const editingId = ref<number | null>(null)
const editForm = reactive<{
  ingredient_name: string
  category: string
  unit: string
  calories_per_100g: number | null
  protein_per_100g: number | null
  carbs_per_100g: number | null
  fat_per_100g: number | null
  fiber_per_100g: number | null
  needs_stock_tracking: boolean
  current_quantity_g: number | null
  min_threshold_g: number | null
  season: string[]
  cost_level: string
}>({
  ingredient_name: '',
  category: CATEGORIES[0],
  unit: 'g',
  calories_per_100g: null,
  protein_per_100g: null,
  carbs_per_100g: null,
  fat_per_100g: null,
  fiber_per_100g: null,
  needs_stock_tracking: false,
  current_quantity_g: null,
  min_threshold_g: null,
  season: [],
  cost_level: '',
})
const savingEdit = ref(false)
const editError = ref<string | null>(null)

function startEdit(item: Ingredient) {
  editingId.value = item.id
  Object.assign(editForm, {
    ingredient_name: item.ingredient_name,
    category: item.category,
    unit: item.unit,
    calories_per_100g: item.calories_per_100g,
    protein_per_100g: item.protein_per_100g,
    carbs_per_100g: item.carbs_per_100g,
    fat_per_100g: item.fat_per_100g,
    fiber_per_100g: item.fiber_per_100g,
    needs_stock_tracking: item.needs_stock_tracking,
    current_quantity_g: item.stock?.current_quantity_g ?? null,
    min_threshold_g: item.stock?.min_threshold_g ?? null,
    season: parseSeasonCsv(item.season),
    cost_level: item.cost_level ?? '',
  })
  editError.value = null
  loadLocationPreferences(item.id)
}

function cancelEdit() {
  editingId.value = null
}

interface LocationPrefRow {
  preferred_location_id: number | null
  notes: string
}

const MAX_LOCATION_PREFS = 3
const locationPrefRows = ref<LocationPrefRow[]>([])
const locationPrefLoading = ref(false)
const locationPrefError = ref<string | null>(null)
const savingLocationPref = ref(false)
const locationPrefSaved = ref(false)

async function loadLocationPreferences(ingredientId: number) {
  locationPrefLoading.value = true
  locationPrefError.value = null
  locationPrefSaved.value = false
  try {
    const prefs = await fetchIngredientLocationPreferences(ingredientId)
    locationPrefRows.value = [...prefs]
      .sort((a, b) => a.priority - b.priority)
      .map((p) => ({ preferred_location_id: p.preferred_location_id, notes: p.notes ?? '' }))
    if (locationPrefRows.value.length === 0) {
      locationPrefRows.value.push({ preferred_location_id: null, notes: '' })
    }
  } catch (e) {
    locationPrefError.value = e instanceof Error ? e.message : '讀取地點偏好失敗'
  } finally {
    locationPrefLoading.value = false
  }
}

function addLocationPrefRow() {
  if (locationPrefRows.value.length >= MAX_LOCATION_PREFS) return
  locationPrefRows.value.push({ preferred_location_id: null, notes: '' })
}

function removeLocationPrefRow(index: number) {
  locationPrefRows.value.splice(index, 1)
}

async function submitLocationPreferences(item: Ingredient) {
  savingLocationPref.value = true
  locationPrefError.value = null
  locationPrefSaved.value = false
  try {
    const preferences = locationPrefRows.value
      .filter((r) => r.preferred_location_id !== null)
      .map((r, i) => ({
        preferred_location_id: r.preferred_location_id as number,
        priority: i + 1,
        notes: r.notes || null,
      }))
    await setIngredientLocationPreferences(item.id, { preferences })
    locationPrefSaved.value = true
  } catch (e) {
    locationPrefError.value = e instanceof Error ? e.message : '儲存地點偏好失敗'
  } finally {
    savingLocationPref.value = false
  }
}

async function submitEdit(item: Ingredient) {
  savingEdit.value = true
  editError.value = null
  try {
    await updateIngredient(item.id, {
      ingredient_name: editForm.ingredient_name,
      category: editForm.category,
      unit: editForm.unit,
      calories_per_100g: editForm.calories_per_100g,
      protein_per_100g: editForm.protein_per_100g,
      carbs_per_100g: editForm.carbs_per_100g,
      fat_per_100g: editForm.fat_per_100g,
      fiber_per_100g: editForm.fiber_per_100g,
      needs_stock_tracking: editForm.needs_stock_tracking,
      season: editForm.season.length ? editForm.season.join(',') : null,
      cost_level: editForm.cost_level || null,
    })
    if (editForm.needs_stock_tracking) {
      await updateIngredientStock(item.id, {
        current_quantity_g: editForm.current_quantity_g ?? 0,
        min_threshold_g: editForm.min_threshold_g,
      })
    }
    editingId.value = null
    reload()
    loadLowStock()
  } catch (e) {
    editError.value = e instanceof Error ? e.message : '更新失敗'
  } finally {
    savingEdit.value = false
  }
}

const showCreate = ref(false)
const createForm = reactive({
  ingredient_name: '',
  category: CATEGORIES[0],
  unit: 'g',
  calories_per_100g: null as number | null,
  protein_per_100g: null as number | null,
  carbs_per_100g: null as number | null,
  fat_per_100g: null as number | null,
  fiber_per_100g: null as number | null,
  needs_stock_tracking: false,
  season: [] as string[],
  cost_level: '',
})
const creating = ref(false)
const createError = ref<string | null>(null)

async function submitCreate() {
  if (!createForm.ingredient_name.trim()) return
  creating.value = true
  createError.value = null
  try {
    await createIngredient({
      ...createForm,
      season: createForm.season.length ? createForm.season.join(',') : null,
      cost_level: createForm.cost_level || null,
    })
    createForm.ingredient_name = ''
    createForm.calories_per_100g = null
    createForm.protein_per_100g = null
    createForm.carbs_per_100g = null
    createForm.fat_per_100g = null
    createForm.fiber_per_100g = null
    createForm.needs_stock_tracking = false
    createForm.season = []
    createForm.cost_level = ''
    showCreate.value = false
    page.value = 1
    reload()
  } catch (e) {
    createError.value = e instanceof Error ? e.message : '新增失敗'
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-3xl px-4 py-8">
    <div class="flex items-center justify-between gap-3">
      <h1 class="font-serif text-2xl text-ink">食材庫</h1>
      <button
        type="button"
        class="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-bright"
        @click="showCreate = !showCreate"
      >
        {{ showCreate ? '取消新增' : '+ 新增食材' }}
      </button>
    </div>

    <div v-if="lowStock.length" class="mt-4 rounded-2xl bg-alert/10 p-4 text-sm text-alert">
      <p class="font-semibold">需要補貨（{{ lowStock.length }}）</p>
      <p class="mt-1">{{ lowStock.map((i) => i.ingredient_name).join('、') }}</p>
    </div>

    <section v-if="showCreate" class="mt-4 rounded-2xl border border-ink/10 bg-surface p-6">
      <div class="flex items-center gap-1.5">
        <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-ink" aria-hidden="true" />
        <h2 class="border-b-[1.5px] border-accent pb-1 text-[11.5px] font-semibold uppercase tracking-wide text-muted">新增食材</h2>
      </div>
      <div class="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
        <label class="text-xs text-tea sm:col-span-2">
          食材名稱
          <input v-model="createForm.ingredient_name" type="text" class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
        </label>
        <label class="text-xs text-tea">
          分類
          <select v-model="createForm.category" class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink">
            <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
          </select>
        </label>
        <label class="text-xs text-tea">
          成本等級
          <select v-model="createForm.cost_level" class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink">
            <option value="">未設定</option>
            <option v-for="c in COST_LEVELS" :key="c" :value="c">{{ c }}</option>
          </select>
        </label>
        <label class="text-xs text-tea">
          熱量 /100g
          <input v-model.number="createForm.calories_per_100g" type="number" class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
        </label>
        <label class="text-xs text-tea">
          蛋白質 /100g
          <input v-model.number="createForm.protein_per_100g" type="number" class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
        </label>
        <label class="text-xs text-tea">
          碳水 /100g
          <input v-model.number="createForm.carbs_per_100g" type="number" class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
        </label>
        <label class="text-xs text-tea">
          脂肪 /100g
          <input v-model.number="createForm.fat_per_100g" type="number" class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
        </label>
        <label class="text-xs text-tea">
          纖維 /100g
          <input v-model.number="createForm.fiber_per_100g" type="number" class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
        </label>
        <label class="flex items-center gap-2 self-end text-sm text-tea">
          <input v-model="createForm.needs_stock_tracking" type="checkbox" class="accent-accent" />
          追蹤庫存
        </label>
      </div>
      <div class="mt-3">
        <p class="text-xs text-tea">盛產季節（蔬果類選填，選了之後推薦菜單時非產季不會被排進去；不選＝不分季節）</p>
        <div class="mt-1 flex flex-wrap gap-2">
          <button
            v-for="s in SEASONS"
            :key="s"
            type="button"
            class="rounded-full border px-3 py-1 text-xs"
            :class="createForm.season.includes(s) ? 'border-accent bg-accent text-on-accent' : 'border-ink/15 text-ink hover:bg-bg'"
            @click="createForm.season = toggleSeason(createForm.season, s)"
          >
            {{ s }}
          </button>
        </div>
      </div>
      <p v-if="createError" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ createError }}</p>
      <button
        type="button"
        class="mt-3 w-full rounded-full bg-accent py-2.5 text-sm font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
        :disabled="creating || !createForm.ingredient_name.trim()"
        @click="submitCreate"
      >
        {{ creating ? '新增中…' : '新增食材' }}
      </button>
    </section>

    <div class="mt-6 flex flex-wrap gap-2">
      <input
        v-model="query"
        type="text"
        placeholder="搜尋食材名稱"
        class="min-w-0 flex-1 rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
        @input="onQueryInput"
      />
      <select v-model="categoryFilter" class="rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink">
        <option value="">全部分類</option>
        <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
      </select>
    </div>

    <p v-if="loading" class="mt-4 text-sm text-tea">載入中…</p>
    <p v-if="error" class="mt-4 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ error }}</p>
    <p v-if="editError" class="mt-4 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ editError }}</p>

    <ul v-if="searchResults && !loading" class="mt-4 divide-y divide-ink/10 rounded-2xl border border-ink/10 bg-surface">
      <li v-for="item in searchResults" :key="item.id" class="p-4">
        <p class="text-sm text-ink">{{ item.ingredient_name }}</p>
        <p class="text-xs text-tea">{{ item.category }} · {{ item.calories_per_100g ?? '—' }} kcal/100g</p>
      </li>
      <li v-if="searchResults.length === 0" class="p-4 text-sm text-tea">沒有符合的食材</li>
    </ul>

    <template v-else-if="!loading">
      <ul class="mt-4 divide-y divide-ink/10 rounded-2xl border border-ink/10 bg-surface">
        <li v-for="item in items" :key="item.id" class="p-4">
          <div class="flex items-center justify-between gap-3">
            <div>
              <p class="text-sm text-ink">{{ item.ingredient_name }}</p>
              <p class="text-xs text-tea">
                {{ item.category }} · {{ item.calories_per_100g ?? '—' }} kcal/100g
                <span v-if="item.cost_level"> · 成本{{ item.cost_level }}</span>
                <span v-if="item.season">· {{ item.season }}盛產</span>
                <span v-if="item.needs_stock_tracking && item.stock"> · 庫存 {{ item.stock.current_quantity_g }}{{ item.stock.unit }}</span>
              </p>
            </div>
            <button
              type="button"
              class="shrink-0 text-xs font-semibold text-accent hover:text-accent-bright"
              @click="editingId === item.id ? cancelEdit() : startEdit(item)"
            >
              {{ editingId === item.id ? '取消' : '編輯' }}
            </button>
          </div>

          <div v-if="editingId === item.id" class="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
            <label class="text-xs text-tea sm:col-span-2">
              食材名稱
              <input v-model="editForm.ingredient_name" type="text" class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
            </label>
            <label class="text-xs text-tea">
              分類
              <select v-model="editForm.category" class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink">
                <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
              </select>
            </label>
            <label class="text-xs text-tea">
              成本等級
              <select v-model="editForm.cost_level" class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink">
                <option value="">未設定</option>
                <option v-for="c in COST_LEVELS" :key="c" :value="c">{{ c }}</option>
              </select>
            </label>
            <label class="text-xs text-tea">
              熱量 /100g
              <input v-model.number="editForm.calories_per_100g" type="number" class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
            </label>
            <label class="text-xs text-tea">
              蛋白質 /100g
              <input v-model.number="editForm.protein_per_100g" type="number" class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
            </label>
            <label class="text-xs text-tea">
              碳水 /100g
              <input v-model.number="editForm.carbs_per_100g" type="number" class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
            </label>
            <label class="text-xs text-tea">
              脂肪 /100g
              <input v-model.number="editForm.fat_per_100g" type="number" class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
            </label>
            <label class="text-xs text-tea">
              纖維 /100g
              <input v-model.number="editForm.fiber_per_100g" type="number" class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
            </label>
            <label class="flex items-center gap-2 self-end text-sm text-tea">
              <input v-model="editForm.needs_stock_tracking" type="checkbox" class="accent-accent" />
              追蹤庫存
            </label>
            <div class="sm:col-span-3">
              <p class="text-xs text-tea">盛產季節（蔬果類選填，不選＝不分季節）</p>
              <div class="mt-1 flex flex-wrap gap-2">
                <button
                  v-for="s in SEASONS"
                  :key="s"
                  type="button"
                  class="rounded-full border px-3 py-1 text-xs"
                  :class="editForm.season.includes(s) ? 'border-accent bg-accent text-on-accent' : 'border-ink/15 text-ink hover:bg-bg'"
                  @click="editForm.season = toggleSeason(editForm.season, s)"
                >
                  {{ s }}
                </button>
              </div>
            </div>
            <template v-if="editForm.needs_stock_tracking">
              <label class="text-xs text-tea">
                目前庫存量
                <input v-model.number="editForm.current_quantity_g" type="number" class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
              </label>
              <label class="text-xs text-tea">
                補貨警告閾值
                <input v-model.number="editForm.min_threshold_g" type="number" class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
              </label>
            </template>
            <button
              type="button"
              class="rounded-full bg-accent px-3 py-2 text-xs font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50 sm:col-span-3"
              :disabled="savingEdit"
              @click="submitEdit(item)"
            >
              {{ savingEdit ? '儲存中…' : '儲存' }}
            </button>
          </div>

          <div v-if="editingId === item.id" class="mt-4 border-t border-ink/10 pt-3">
            <p class="text-[11.5px] font-semibold uppercase tracking-wide text-muted">採購地點偏好（最多 3 個，依序為優先順序）</p>
            <p v-if="locationPrefLoading" class="mt-2 text-xs text-tea">載入中…</p>
            <template v-else>
              <div v-for="(row, i) in locationPrefRows" :key="i" class="mt-2 flex items-center gap-2">
                <span class="w-4 shrink-0 text-xs text-tea">{{ i + 1 }}.</span>
                <select v-model.number="row.preferred_location_id" class="min-w-0 flex-1 rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink">
                  <option :value="null">選擇地點</option>
                  <option v-for="loc in purchaseLocations" :key="loc.id" :value="loc.id">{{ loc.location_name }}</option>
                </select>
                <input v-model="row.notes" type="text" placeholder="備註（選填）" class="w-32 shrink-0 rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
                <button type="button" class="shrink-0 text-xs text-tea hover:text-alert" @click="removeLocationPrefRow(i)">刪除</button>
              </div>
              <button
                v-if="locationPrefRows.length < MAX_LOCATION_PREFS"
                type="button"
                class="mt-2 text-xs font-semibold text-accent hover:text-accent-bright"
                @click="addLocationPrefRow"
              >
                + 新增地點偏好
              </button>
              <p v-if="locationPrefError" class="mt-2 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ locationPrefError }}</p>
              <div class="mt-2 flex items-center gap-3">
                <button
                  type="button"
                  class="rounded-full border border-ink/15 px-3 py-1.5 text-xs font-semibold text-ink hover:bg-bg disabled:opacity-50"
                  :disabled="savingLocationPref"
                  @click="submitLocationPreferences(item)"
                >
                  {{ savingLocationPref ? '儲存中…' : '儲存地點偏好' }}
                </button>
                <span v-if="locationPrefSaved" class="text-xs text-accent">已儲存</span>
              </div>
            </template>
          </div>
        </li>
        <li v-if="items.length === 0" class="p-4 text-sm text-tea">沒有符合的食材</li>
      </ul>

      <div v-if="totalPages > 1" class="mt-4 flex items-center justify-center gap-3 text-sm text-tea">
        <button type="button" class="disabled:opacity-30" :disabled="page <= 1" @click="page -= 1">上一頁</button>
        <span>{{ page }} / {{ totalPages }}</span>
        <button type="button" class="disabled:opacity-30" :disabled="page >= totalPages" @click="page += 1">下一頁</button>
      </div>
    </template>
  </div>
</template>

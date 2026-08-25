<script setup lang="ts">
import { reactive, ref, watchEffect } from 'vue'
import { searchIngredientsByName } from '../recipes/ingredient_api'
import {
  addShoppingListItem,
  deleteShoppingListItem,
  fetchShoppingList,
  markShoppingListItemPurchased,
  updateShoppingListItem,
  updateShoppingListStatus,
} from './shopping_list_api'
import { useConfirmDialog } from '../shared/useConfirmDialog'
import { useHouseholdConfig } from '../shared/useHouseholdConfig'
import type { IngredientSearchResult, ShoppingListDetail, ShoppingListItem } from '../shared/types'

const STATUS_OPTIONS = ['草稿', '已確認', '採購中', '已採購', '歸檔']

const { config, setCurrentShoppingListId } = useHouseholdConfig()
const { confirmDialog } = useConfirmDialog()

const list = ref<ShoppingListDetail | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)
const itemError = ref<string | null>(null)

async function load(listId: number) {
  loading.value = true
  error.value = null
  try {
    list.value = await fetchShoppingList(listId)
    statusForm.value = list.value.status
  } catch (e) {
    error.value = e instanceof Error ? e.message : '讀取購物清單失敗'
  } finally {
    loading.value = false
  }
}

watchEffect(() => {
  const id = config.value.currentShoppingListId
  if (id !== null) load(id)
})

const manualListId = ref('')
function loadManual() {
  const id = Number(manualListId.value)
  if (!id) return
  setCurrentShoppingListId(id)
}

function assignedUserLabel(userId: number | null): string {
  if (userId === null) return '共用'
  return config.value.users.find((u) => u.id === userId)?.name ?? `使用者 #${userId}`
}

async function togglePurchased(item: ShoppingListItem) {
  if (!list.value) return
  itemError.value = null
  try {
    await markShoppingListItemPurchased(list.value.list_id, item.id, !item.is_purchased)
    await load(list.value.list_id)
  } catch (e) {
    itemError.value = e instanceof Error ? e.message : '更新採購狀態失敗'
  }
}

async function removeItem(item: ShoppingListItem) {
  if (!list.value) return
  if (!(await confirmDialog(`刪除「${item.ingredient_name}」？`))) return
  itemError.value = null
  try {
    await deleteShoppingListItem(list.value.list_id, item.id)
    await load(list.value.list_id)
  } catch (e) {
    itemError.value = e instanceof Error ? e.message : '刪除項目失敗'
  }
}

const editingItemId = ref<number | null>(null)
const editQuantity = ref<number | null>(null)

function startEditQuantity(item: ShoppingListItem) {
  editingItemId.value = item.id
  editQuantity.value = item.quantity_needed_g
}

function cancelEditQuantity() {
  editingItemId.value = null
}

async function submitEditQuantity(item: ShoppingListItem) {
  if (!list.value || editQuantity.value === null) return
  itemError.value = null
  try {
    // 後端的 update 是整包覆蓋（沒有 exclude_unset），所以把其他既有欄位一併帶上，避免被清空。
    await updateShoppingListItem(list.value.list_id, item.id, {
      quantity_needed_g: editQuantity.value,
      purchase_location_id: item.purchase_location_id,
      assigned_user_id: item.assigned_user_id,
      notes: item.notes,
    })
    editingItemId.value = null
    await load(list.value.list_id)
  } catch (e) {
    itemError.value = e instanceof Error ? e.message : '更新用量失敗'
  }
}

const addForm = reactive({
  ingredient_id: null as number | null,
  ingredient_name: '',
  quantity_needed_g: null as number | null,
  notes: '',
})
const adding = ref(false)
const addError = ref<string | null>(null)

const ingSearchQuery = ref('')
const ingSearchResults = ref<IngredientSearchResult[]>([])
const ingSearching = ref(false)

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

function pickIngredient(ing: IngredientSearchResult) {
  addForm.ingredient_id = ing.id
  addForm.ingredient_name = ing.ingredient_name
  ingSearchResults.value = []
  ingSearchQuery.value = ''
}

async function submitAddItem() {
  if (!list.value || addForm.ingredient_id === null || addForm.quantity_needed_g === null) return
  adding.value = true
  addError.value = null
  try {
    await addShoppingListItem(list.value.list_id, {
      ingredient_id: addForm.ingredient_id,
      quantity_needed_g: addForm.quantity_needed_g,
      notes: addForm.notes || null,
    })
    addForm.ingredient_id = null
    addForm.ingredient_name = ''
    addForm.quantity_needed_g = null
    addForm.notes = ''
    await load(list.value.list_id)
  } catch (e) {
    addError.value = e instanceof Error ? e.message : '新增項目失敗'
  } finally {
    adding.value = false
  }
}

const statusForm = ref('草稿')
const updatingStatus = ref(false)
const statusError = ref<string | null>(null)

async function submitStatus() {
  if (!list.value) return
  updatingStatus.value = true
  statusError.value = null
  try {
    await updateShoppingListStatus(list.value.list_id, statusForm.value)
    await load(list.value.list_id)
  } catch (e) {
    statusError.value = e instanceof Error ? e.message : '更新狀態失敗'
  } finally {
    updatingStatus.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-3xl px-4 py-8">
    <div v-if="config.currentShoppingListId === null" class="rounded-2xl border border-dashed border-ink/20 p-6 text-center">
      <p class="text-sm text-tea">尚未生成購物清單，請先到「週推薦」頁確認一次推薦。</p>
      <div class="mt-3 flex justify-center gap-2">
        <input
          v-model="manualListId"
          type="number"
          placeholder="或輸入清單 ID"
          class="rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
        />
        <button type="button" class="rounded-lg border border-ink/15 px-3 py-2 text-sm text-ink hover:bg-bg" @click="loadManual">
          查看
        </button>
      </div>
      <RouterLink to="/shopping-list/history" class="mt-3 inline-block text-xs font-semibold text-tea hover:text-ink">
        或查看採購歷史 →
      </RouterLink>
    </div>

    <template v-else>
      <p v-if="loading" class="text-sm text-tea">載入中…</p>
      <p v-if="error" class="rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ error }}</p>

      <template v-if="list">
        <div class="flex justify-end">
          <RouterLink to="/shopping-list/history" class="text-xs font-semibold text-tea hover:text-ink">
            採購歷史 →
          </RouterLink>
        </div>
        <div class="mt-2 rounded-2xl border border-ink/10 bg-surface p-4">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 class="font-serif text-2xl text-ink">{{ list.week_start_date }} 購物清單</h1>
              <p class="text-xs text-tea">{{ list.total_items }} 項 · 清單日期 {{ list.list_date }}</p>
            </div>
            <div class="flex items-center gap-2">
              <select v-model="statusForm" class="rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink">
                <option v-for="s in STATUS_OPTIONS" :key="s" :value="s">{{ s }}</option>
              </select>
              <button
                type="button"
                class="rounded-full bg-accent px-3 py-2 text-sm font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
                :disabled="updatingStatus"
                @click="submitStatus"
              >
                {{ updatingStatus ? '更新中…' : '更新狀態' }}
              </button>
            </div>
          </div>
          <p v-if="statusError" class="mt-2 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ statusError }}</p>
        </div>

        <p v-if="itemError" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ itemError }}</p>

        <div v-for="(groups, locationName) in list.items_by_location" :key="locationName" class="mt-4">
          <h2 class="font-serif text-lg text-ink">{{ locationName }}</h2>
          <div v-for="group in groups" :key="group.category" class="mt-2 rounded-2xl border border-ink/10 bg-surface p-4">
            <p class="text-[11.5px] font-semibold uppercase tracking-wide text-muted">{{ group.category }}</p>
            <ul class="mt-2 divide-y divide-ink/10">
              <li v-for="item in group.items" :key="item.id" class="flex items-center gap-3 py-2.5">
                <input type="checkbox" class="accent-accent" :checked="item.is_purchased" @change="togglePurchased(item)" />
                <div class="min-w-0 flex-1">
                  <p class="text-sm" :class="item.is_purchased ? 'text-muted line-through' : 'text-ink'">
                    {{ item.ingredient_name }}
                    <span v-if="item.cost_level" class="ml-1 rounded-full bg-accent-tint px-2 py-0.5 text-[10px] text-ink">{{ item.cost_level }}</span>
                    <span v-if="item.needs_restocking" class="ml-1 rounded-full bg-alert/10 px-2 py-0.5 text-[10px] text-alert">補貨</span>
                  </p>
                  <p class="text-xs text-tea">{{ assignedUserLabel(item.assigned_user_id) }}<span v-if="item.notes"> · {{ item.notes }}</span></p>
                </div>
                <div v-if="editingItemId === item.id" class="flex shrink-0 items-center gap-1">
                  <input v-model.number="editQuantity" type="number" step="1" class="w-20 rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
                  <span class="text-xs text-tea">{{ item.unit }}</span>
                  <button type="button" class="text-xs font-semibold text-accent" @click="submitEditQuantity(item)">存</button>
                  <button type="button" class="text-xs text-tea" @click="cancelEditQuantity">取消</button>
                </div>
                <button
                  v-else
                  type="button"
                  class="shrink-0 font-serif text-lg text-ink hover:text-accent"
                  @click="startEditQuantity(item)"
                >
                  {{ item.quantity_needed_g }}<small class="text-sm text-tea">{{ item.unit }}</small>
                </button>
                <button type="button" class="shrink-0 text-xs text-tea hover:text-alert" @click="removeItem(item)">刪除</button>
              </li>
            </ul>
          </div>
        </div>

        <section class="mt-6 rounded-2xl border border-ink/10 bg-surface p-6">
          <div class="flex items-center gap-1.5">
            <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-ink" aria-hidden="true" />
            <h2 class="border-b-[1.5px] border-accent pb-1 text-[11.5px] font-semibold uppercase tracking-wide text-muted">
              新增臨時食材
            </h2>
          </div>
          <div class="mt-3">
            <div v-if="!addForm.ingredient_id" class="flex gap-2">
              <input
                v-model="ingSearchQuery"
                type="text"
                placeholder="搜尋食材名稱"
                class="min-w-0 flex-1 rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
                @keydown.enter="runIngredientSearch"
              />
              <button
                type="button"
                class="shrink-0 rounded-lg border border-ink/15 px-3 py-2 text-xs font-semibold text-ink hover:bg-bg"
                :disabled="ingSearching"
                @click="runIngredientSearch"
              >
                {{ ingSearching ? '搜尋中…' : '搜尋' }}
              </button>
            </div>
            <ul v-if="ingSearchResults.length" class="mt-2 divide-y divide-ink/10 rounded-lg border border-ink/10">
              <li v-for="ing in ingSearchResults" :key="ing.id" class="flex items-center justify-between px-3 py-1.5 text-sm">
                <span class="text-ink">{{ ing.ingredient_name }}<span class="text-tea">（{{ ing.category }}）</span></span>
                <button type="button" class="text-xs font-semibold text-accent hover:text-accent-bright" @click="pickIngredient(ing)">選這個</button>
              </li>
            </ul>
            <div v-if="addForm.ingredient_id" class="mt-2 flex items-center gap-2 text-sm text-ink">
              已選：{{ addForm.ingredient_name }}
              <button type="button" class="text-xs text-tea hover:text-alert" @click="addForm.ingredient_id = null">換一個</button>
            </div>
          </div>
          <div class="mt-3 grid grid-cols-2 gap-3">
            <input
              v-model.number="addForm.quantity_needed_g"
              type="number"
              placeholder="用量（g）"
              class="rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
            />
            <input
              v-model="addForm.notes"
              type="text"
              placeholder="備註（選填）"
              class="rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
            />
          </div>
          <p v-if="addError" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ addError }}</p>
          <button
            type="button"
            class="mt-3 w-full rounded-full bg-accent py-2.5 text-sm font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
            :disabled="adding || addForm.ingredient_id === null || addForm.quantity_needed_g === null"
            @click="submitAddItem"
          >
            {{ adding ? '新增中…' : '新增項目' }}
          </button>
        </section>
      </template>
    </template>
  </div>
</template>

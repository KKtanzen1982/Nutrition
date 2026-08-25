<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import ExerciseItemDetailModal from './ExerciseItemDetailModal.vue'
import { createExerciseItem, searchExerciseItems } from './exercise_item_api'
import type { ExerciseItemLibraryEntry, ExerciseItemType } from '../shared/types'

const GYM_CATEGORIES = ['胸部', '背部', '下肢', '手臂', '核心', '有氧']
const YOGA_TYPES = ['瑜珈', '拉伸']

const props = defineProps<{
  modelValue: string
  itemType: ExerciseItemType
  userId: number | null
  yogaType?: string
  placeholder?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  select: [item: ExerciseItemLibraryEntry]
  clear: []
}>()

const text = ref(props.modelValue)
watch(
  () => props.modelValue,
  (v) => {
    if (v !== text.value) text.value = v
  },
)

const categoryOptions = computed(() => (props.itemType === 'gym' ? GYM_CATEGORIES : YOGA_TYPES))
const selectedCategory = ref('')

const suggestions = ref<ExerciseItemLibraryEntry[]>([])
const open = ref(false)
const adding = ref(false)
const selectedId = ref<number | null>(null)
let debounceTimer: ReturnType<typeof setTimeout> | undefined
let requestSeq = 0

function itemSubLabel(item: ExerciseItemLibraryEntry): string {
  return 'category' in item ? item.category : item.type
}

const detailItemId = ref<number | null>(null)
const showDetail = ref(false)

function openDetail(item: ExerciseItemLibraryEntry) {
  detailItemId.value = item.id
  showDetail.value = true
}

async function runSearch(query: string) {
  const seq = ++requestSeq
  try {
    const results = await searchExerciseItems({
      itemType: props.itemType,
      q: query,
      category: selectedCategory.value || undefined,
      userId: props.userId,
      limit: 8,
    })
    if (seq !== requestSeq) return
    suggestions.value = results
    open.value = true
  } catch {
    if (seq === requestSeq) suggestions.value = []
  }
}

function triggerSearch() {
  const query = text.value.trim()
  if (!query && !selectedCategory.value) {
    suggestions.value = []
    open.value = false
    return
  }
  runSearch(query)
}

function onInput() {
  emit('update:modelValue', text.value)
  if (selectedId.value !== null) {
    selectedId.value = null
    emit('clear')
  }
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(triggerSearch, 300)
}

function onCategoryChange() {
  triggerSearch()
}

function pick(item: ExerciseItemLibraryEntry) {
  text.value = item.item_name
  selectedId.value = item.id
  open.value = false
  emit('update:modelValue', item.item_name)
  emit('select', item)
}

function onFocus() {
  triggerSearch()
}

const root = ref<HTMLElement | null>(null)

function onDocumentMousedown(e: MouseEvent) {
  if (root.value && !root.value.contains(e.target as Node)) {
    open.value = false
  }
}

onMounted(() => document.addEventListener('mousedown', onDocumentMousedown))
onUnmounted(() => document.removeEventListener('mousedown', onDocumentMousedown))

const showAddButton = computed(() => {
  const name = text.value.trim()
  if (!name || selectedId.value !== null || adding.value) return false
  return !suggestions.value.some((s) => s.item_name === name)
})

async function addToLibrary() {
  const name = text.value.trim()
  if (!name || adding.value) return
  adding.value = true
  try {
    const created = await createExerciseItem(
      props.itemType === 'gym'
        ? { type: 'gym', item_name: name }
        : { type: 'yoga_stretch', item_name: name, yoga_type: props.yogaType },
    )
    pick(created)
  } catch {
    // 加入動作庫失敗不影響原本的自由輸入，安靜略過
  } finally {
    adding.value = false
  }
}
</script>

<template>
  <div ref="root" class="relative">
    <div class="flex gap-1">
      <select
        v-model="selectedCategory"
        class="w-16 shrink-0 rounded border border-ink/15 bg-bg px-1 text-xs text-tea"
        @change="onCategoryChange"
      >
        <option value="">全部</option>
        <option v-for="c in categoryOptions" :key="c" :value="c">{{ c }}</option>
      </select>
      <input
        v-model="text"
        type="text"
        :placeholder="placeholder ?? '動作名稱'"
        class="min-w-0 flex-1 rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink"
        @input="onInput"
        @focus="onFocus"
      />
    </div>
    <ul
      v-if="open && suggestions.length"
      class="absolute z-10 mt-1 max-h-48 w-full min-w-[160px] overflow-auto rounded-lg border border-ink/15 bg-surface shadow-lg"
    >
      <li
        v-for="item in suggestions"
        :key="item.id"
        class="flex items-center justify-between gap-2 px-2 py-1.5 text-sm text-ink hover:bg-accent-tint"
      >
        <span class="min-w-0 flex-1 cursor-pointer truncate" @mousedown.prevent="pick(item)">
          {{ item.item_name }}
          <span class="ml-1 text-xs text-tea">{{ itemSubLabel(item) }}</span>
        </span>
        <button
          type="button"
          class="shrink-0 text-xs text-tea hover:text-accent"
          title="檢視動作資料庫"
          @mousedown.prevent.stop="openDetail(item)"
        >
          ⓘ
        </button>
      </li>
    </ul>
    <button
      v-if="showAddButton"
      type="button"
      class="mt-1 text-xs font-semibold text-accent hover:text-accent-bright"
      @mousedown.prevent="addToLibrary"
    >
      {{ adding ? '加入中…' : '＋ 加入動作庫' }}
    </button>

    <ExerciseItemDetailModal v-model="showDetail" :item-type="itemType" :item-id="detailItemId" :user-id="userId" />
  </div>
</template>

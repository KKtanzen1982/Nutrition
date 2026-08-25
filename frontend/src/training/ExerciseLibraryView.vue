<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import AddExerciseItemModal from './AddExerciseItemModal.vue'
import ExerciseItemDetailModal from './ExerciseItemDetailModal.vue'
import TemplateFormModal from './TemplateFormModal.vue'
import { listExerciseItems } from './exercise_item_api'
import { fetchWorkoutTemplates } from './workout_template_api'
import { useHouseholdConfig } from '../shared/useHouseholdConfig'
import type { ExerciseItemLibraryEntry, ExerciseItemType, WorkoutTemplate } from '../shared/types'

const GYM_CATEGORIES = ['胸部', '背部', '下肢', '手臂', '核心', '有氧']
const YOGA_TYPES = ['瑜珈', '拉伸']

type Tab = ExerciseItemType | 'templates'

const { activeUser } = useHouseholdConfig()

const activeTab = ref<Tab>('gym')
const items = ref<ExerciseItemLibraryEntry[]>([])
const templates = ref<WorkoutTemplate[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const categoryFilter = ref('')
const muscleGroupFilter = ref('')

const categoryOptions = computed(() => (activeTab.value === 'gym' ? GYM_CATEGORIES : YOGA_TYPES))
const muscleGroupOptions = computed(() => {
  const groups = new Set<string>()
  for (const item of items.value) {
    if ('muscle_group' in item && item.muscle_group) groups.add(item.muscle_group)
  }
  return [...groups].sort()
})

async function load() {
  loading.value = true
  error.value = null
  categoryFilter.value = ''
  muscleGroupFilter.value = ''
  try {
    if (activeTab.value === 'templates') {
      if (activeUser.value) templates.value = await fetchWorkoutTemplates(activeUser.value.id)
    } else {
      items.value = await listExerciseItems(activeTab.value, undefined, activeUser.value?.id ?? undefined)
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '讀取失敗'
  } finally {
    loading.value = false
  }
}

watchEffect(() => {
  activeTab.value
  activeUser.value
  load()
})

function subLabel(item: ExerciseItemLibraryEntry): string {
  return 'category' in item ? item.category : item.type
}

const filteredItems = computed(() =>
  items.value
    .filter((item) => !categoryFilter.value || subLabel(item) === categoryFilter.value)
    .filter((item) => !muscleGroupFilter.value || ('muscle_group' in item && item.muscle_group === muscleGroupFilter.value)),
)

const groups = computed(() => {
  const map = new Map<string, ExerciseItemLibraryEntry[]>()
  for (const item of filteredItems.value) {
    const key = subLabel(item)
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(item)
  }
  return [...map.entries()]
})

const showDetail = ref(false)
const detailItemId = ref<number | null>(null)

function openDetail(item: ExerciseItemLibraryEntry) {
  detailItemId.value = item.id
  showDetail.value = true
}

const showAdd = ref(false)

function onCreated(item: ExerciseItemLibraryEntry) {
  items.value = [...items.value, item]
}

const showTemplateForm = ref(false)
const formTemplateId = ref<number | null>(null)

function openTemplateDetail(template: WorkoutTemplate) {
  formTemplateId.value = template.id
  showTemplateForm.value = true
}
function openNewTemplate() {
  formTemplateId.value = null
  showTemplateForm.value = true
}
function onTemplateSaved(template: WorkoutTemplate) {
  const idx = templates.value.findIndex((t) => t.id === template.id)
  if (idx === -1) templates.value = [...templates.value, template]
  else templates.value = templates.value.map((t) => (t.id === template.id ? template : t))
}
function onTemplateDeleted(templateId: number) {
  templates.value = templates.value.filter((t) => t.id !== templateId)
}
</script>

<template>
  <div class="mx-auto max-w-2xl px-4 py-8">
    <div class="flex items-center justify-between">
      <h1 class="font-serif text-2xl text-ink">動作資料庫</h1>
      <button
        v-if="activeTab !== 'templates'"
        type="button"
        class="rounded-full bg-accent px-3 py-1.5 text-xs font-semibold text-on-accent hover:bg-accent-bright"
        @click="showAdd = true"
      >
        + 新增動作
      </button>
      <button
        v-else
        type="button"
        class="rounded-full bg-accent px-3 py-1.5 text-xs font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
        :disabled="!activeUser"
        @click="openNewTemplate"
      >
        + 新增範本
      </button>
    </div>

    <div class="mt-4 flex gap-2">
      <button
        type="button"
        class="rounded-full px-3 py-1.5 text-sm font-semibold"
        :class="activeTab === 'gym' ? 'bg-accent text-on-accent' : 'bg-surface text-tea'"
        @click="activeTab = 'gym'"
      >
        健身房
      </button>
      <button
        type="button"
        class="rounded-full px-3 py-1.5 text-sm font-semibold"
        :class="activeTab === 'yoga_stretch' ? 'bg-accent text-on-accent' : 'bg-surface text-tea'"
        @click="activeTab = 'yoga_stretch'"
      >
        瑜珈/拉伸
      </button>
      <button
        type="button"
        class="rounded-full px-3 py-1.5 text-sm font-semibold"
        :class="activeTab === 'templates' ? 'bg-accent text-on-accent' : 'bg-surface text-tea'"
        @click="activeTab = 'templates'"
      >
        範本
      </button>
    </div>

    <div v-if="activeTab !== 'templates'" class="mt-3 flex flex-wrap gap-2">
      <select v-model="categoryFilter" class="rounded border border-ink/15 bg-bg px-2 py-1 text-xs text-ink">
        <option value="">全部分類</option>
        <option v-for="c in categoryOptions" :key="c" :value="c">{{ c }}</option>
      </select>
      <select
        v-if="activeTab === 'gym'"
        v-model="muscleGroupFilter"
        class="rounded border border-ink/15 bg-bg px-2 py-1 text-xs text-ink"
      >
        <option value="">全部肌群</option>
        <option v-for="m in muscleGroupOptions" :key="m" :value="m">{{ m }}</option>
      </select>
    </div>

    <p v-if="loading" class="mt-8 text-sm text-tea">載入中…</p>
    <p v-else-if="error" class="mt-8 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ error }}</p>
    <p v-else-if="!activeUser && activeTab === 'templates'" class="mt-8 text-sm text-tea">請先在上方完成使用者設定</p>

    <template v-else-if="activeTab === 'templates'">
      <p v-if="templates.length === 0" class="mt-8 text-sm text-tea">還沒有任何範本</p>
      <ul v-else class="mt-6 divide-y divide-ink/10 rounded-2xl border border-ink/10 bg-surface">
        <li
          v-for="t in templates"
          :key="t.id"
          class="cursor-pointer px-4 py-3 text-sm text-ink hover:bg-accent-tint"
          @click="openTemplateDetail(t)"
        >
          {{ t.template_name }}
          <span class="ml-1 text-xs text-tea">{{ t.exercise_type }}</span>
        </li>
      </ul>
    </template>

    <template v-else>
      <p v-if="groups.length === 0" class="mt-8 text-sm text-tea">沒有符合篩選條件的動作</p>
      <section v-for="[group, groupItems] in groups" :key="group" class="mt-6">
        <h2 class="text-xs font-semibold uppercase tracking-wide text-tea">{{ group }}</h2>
        <ul class="mt-2 divide-y divide-ink/10 rounded-2xl border border-ink/10 bg-surface">
          <li
            v-for="item in groupItems"
            :key="item.id"
            class="cursor-pointer px-4 py-3 text-sm text-ink hover:bg-accent-tint"
            @click="openDetail(item)"
          >
            {{ item.item_name }}
          </li>
        </ul>
      </section>
    </template>

    <ExerciseItemDetailModal
      v-model="showDetail"
      :item-type="activeTab === 'templates' ? 'gym' : activeTab"
      :item-id="detailItemId"
      :user-id="activeUser?.id ?? null"
    />
    <AddExerciseItemModal v-if="activeTab !== 'templates'" v-model="showAdd" :item-type="activeTab" @created="onCreated" />
    <TemplateFormModal
      v-model="showTemplateForm"
      :template-id="formTemplateId"
      :user-id="activeUser?.id ?? null"
      @saved="onTemplateSaved"
      @deleted="onTemplateDeleted"
    />
  </div>
</template>

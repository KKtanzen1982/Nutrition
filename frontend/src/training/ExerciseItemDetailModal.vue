<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import Modal from '../shared/Modal.vue'
import TrendChart from '../trends/TrendChart.vue'
import { getExerciseItem, getExerciseItemHistory, updateExerciseItem } from './exercise_item_api'
import type { ExerciseItemLibraryEntry, ExerciseItemType, ExerciseItemVolumePoint } from '../shared/types'

const props = defineProps<{
  modelValue: boolean
  itemType: ExerciseItemType
  itemId: number | null
  userId: number | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

const loading = ref(false)
const error = ref<string | null>(null)
const item = ref<ExerciseItemLibraryEntry | null>(null)
const history = ref<ExerciseItemVolumePoint[]>([])

const form = reactive({
  category: '',
  muscle_group: '',
  equipment: '',
  default_sets: null as number | null,
  default_reps: '',
  duration_min: null as number | null,
  difficulty: '',
  description: '',
})

const saving = ref(false)
const saveError = ref<string | null>(null)

function fillForm(loaded: ExerciseItemLibraryEntry) {
  if ('category' in loaded) {
    form.category = loaded.category
    form.muscle_group = loaded.muscle_group ?? ''
    form.equipment = loaded.equipment ?? ''
    form.default_sets = loaded.default_sets
    form.default_reps = loaded.default_reps ?? ''
  } else {
    form.duration_min = loaded.duration_min
    form.difficulty = loaded.difficulty ?? ''
  }
  form.description = loaded.description ?? ''
}

async function load() {
  if (props.itemId === null) return
  loading.value = true
  error.value = null
  item.value = null
  history.value = []
  try {
    const [loadedItem, loadedHistory] = await Promise.all([
      getExerciseItem(props.itemType, props.itemId),
      props.userId !== null ? getExerciseItemHistory(props.itemType, props.itemId, props.userId) : Promise.resolve([]),
    ])
    item.value = loadedItem
    history.value = loadedHistory
    fillForm(loadedItem)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '讀取失敗，請稍後再試'
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.modelValue, props.itemId, props.itemType],
  () => {
    if (props.modelValue && props.itemId !== null) load()
  },
  { immediate: true },
)

const isGym = computed(() => item.value !== null && 'category' in item.value)

async function save() {
  if (props.itemId === null) return
  saving.value = true
  saveError.value = null
  try {
    const payload = isGym.value
      ? {
          category: form.category,
          muscle_group: form.muscle_group || null,
          equipment: form.equipment || null,
          default_sets: form.default_sets,
          default_reps: form.default_reps || null,
          description: form.description || null,
        }
      : {
          duration_min: form.duration_min,
          difficulty: form.difficulty || null,
          description: form.description || null,
        }
    item.value = await updateExerciseItem(props.itemType, props.itemId, payload)
    emit('update:modelValue', false)
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : '儲存失敗，請稍後再試'
  } finally {
    saving.value = false
  }
}

const chartPoints = computed(() => history.value.map((p) => ({ label: p.date.slice(5), value: p.volume })))
const chartUnit = computed(() => (isGym.value ? '' : '分鐘'))
</script>

<template>
  <Modal :model-value="modelValue" title="動作資料庫" @update:model-value="(v) => emit('update:modelValue', v)">
    <p v-if="loading" class="text-sm text-tea">載入中…</p>
    <p v-else-if="error" class="rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ error }}</p>

    <template v-else-if="item">
      <h3 class="font-serif text-xl text-ink">{{ item.item_name }}</h3>

      <div v-if="isGym" class="mt-4 grid grid-cols-2 gap-3">
        <label class="text-xs text-tea">
          分類
          <input v-model="form.category" type="text" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
        </label>
        <label class="text-xs text-tea">
          肌群
          <input v-model="form.muscle_group" type="text" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
        </label>
        <label class="text-xs text-tea">
          器材
          <input v-model="form.equipment" type="text" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
        </label>
        <label class="text-xs text-tea">
          建議組數
          <input v-model.number="form.default_sets" type="number" min="1" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
        </label>
        <label class="text-xs text-tea">
          建議次數
          <input v-model="form.default_reps" type="text" placeholder="例如 8-10" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
        </label>
      </div>

      <div v-else class="mt-4 grid grid-cols-2 gap-3">
        <label class="text-xs text-tea">
          建議時長（分鐘）
          <input v-model.number="form.duration_min" type="number" min="1" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
        </label>
        <label class="text-xs text-tea">
          難度
          <select v-model="form.difficulty" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink">
            <option value="">未設定</option>
            <option value="初級">初級</option>
            <option value="中級">中級</option>
            <option value="進階">進階</option>
          </select>
        </label>
      </div>

      <label class="mt-3 block text-xs text-tea">
        備註（動作要領等）
        <textarea
          v-model="form.description"
          rows="3"
          placeholder="例如：注意下背打直、槓鈴軌跡貼胸口"
          class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink"
        />
      </label>

      <p v-if="saveError" class="mt-2 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ saveError }}</p>
      <button
        type="button"
        class="mt-3 rounded-full bg-accent px-4 py-1.5 text-xs font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
        :disabled="saving"
        @click="save"
      >
        {{ saving ? '儲存中…' : '儲存變更' }}
      </button>

      <div class="mt-6 border-t border-ink/10 pt-4">
        <p class="text-xs text-tea">我的訓練量歷史</p>
        <TrendChart
          v-if="chartPoints.length"
          :points="chartPoints"
          mode="bar"
          :unit="chartUnit"
          :decimals="isGym ? 0 : 0"
          class="mt-2"
        />
        <p v-else class="mt-2 text-sm text-tea">還沒有這個動作的紀錄</p>
      </div>
    </template>
  </Modal>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import Modal from '../shared/Modal.vue'
import ExerciseItemAutocomplete from './ExerciseItemAutocomplete.vue'
import { createWorkoutTemplate, deleteWorkoutTemplate, fetchWorkoutTemplate, updateWorkoutTemplate } from './workout_template_api'
import { useConfirmDialog } from '../shared/useConfirmDialog'
import type { ExerciseItemLibraryEntry, WorkoutTemplate } from '../shared/types'

const { confirmDialog } = useConfirmDialog()

const EXERCISE_TYPES = ['健身房', '走路', '瑜珈', '拉伸']
const YOGA_STRETCH_TYPES = ['瑜珈', '拉伸']

const props = defineProps<{
  modelValue: boolean
  templateId: number | null
  userId: number | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: [template: WorkoutTemplate]
  deleted: [templateId: number]
}>()

interface DetailRow {
  exercise_name: string
  sets: number | null
  reps: string
  weight_kg: number | null
  duration_min: number | null
  exercise_item_id: number | null
  yoga_stretch_item_id: number | null
}

function emptyDetailRow(): DetailRow {
  return { exercise_name: '', sets: null, reps: '', weight_kg: null, duration_min: null, exercise_item_id: null, yoga_stretch_item_id: null }
}

const form = reactive({
  template_name: '',
  exercise_type: EXERCISE_TYPES[0],
  duration_min: null as number | null,
})
const detailRows = ref<DetailRow[]>([])

const showsGymDetails = computed(() => form.exercise_type === '健身房')
const showsYogaStretchDetails = computed(() => YOGA_STRETCH_TYPES.includes(form.exercise_type))
const isCreate = computed(() => props.templateId === null)

const loading = ref(false)
const error = ref<string | null>(null)
const saving = ref(false)
const saveError = ref<string | null>(null)

function resetForm() {
  form.template_name = ''
  form.exercise_type = EXERCISE_TYPES[0]
  form.duration_min = null
  detailRows.value = []
  error.value = null
  saveError.value = null
}

async function load() {
  if (props.templateId === null) {
    resetForm()
    return
  }
  loading.value = true
  error.value = null
  try {
    const template = await fetchWorkoutTemplate(props.templateId)
    form.template_name = template.template_name
    form.exercise_type = template.exercise_type
    form.duration_min = template.duration_min
    detailRows.value = template.details
      .slice()
      .sort((a, b) => a.order - b.order)
      .map((d) => ({
        exercise_name: d.exercise_name,
        sets: d.sets,
        reps: d.reps ?? '',
        weight_kg: d.weight_kg,
        duration_min: d.duration_min ?? null,
        exercise_item_id: d.exercise_item_id ?? null,
        yoga_stretch_item_id: d.yoga_stretch_item_id ?? null,
      }))
  } catch (e) {
    error.value = e instanceof Error ? e.message : '讀取範本失敗'
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.modelValue, props.templateId],
  () => {
    if (props.modelValue) load()
  },
  { immediate: true },
)

function addDetailRow() {
  detailRows.value.push(emptyDetailRow())
}
function removeDetailRow(index: number) {
  detailRows.value.splice(index, 1)
}

function onSelectLibraryItem(row: DetailRow, item: ExerciseItemLibraryEntry) {
  if ('category' in item) {
    row.exercise_item_id = item.id
    row.yoga_stretch_item_id = null
    row.sets = item.default_sets
    row.reps = item.default_reps ?? ''
  } else {
    row.yoga_stretch_item_id = item.id
    row.exercise_item_id = null
    row.duration_min = item.duration_min
  }
}
function onClearLibraryItem(row: DetailRow) {
  row.exercise_item_id = null
  row.yoga_stretch_item_id = null
}

function isValidDetailRow(r: DetailRow): boolean {
  if (!r.exercise_name) return false
  if (showsGymDetails.value) return r.sets !== null && !!r.reps
  if (showsYogaStretchDetails.value) return r.duration_min !== null
  return false
}

function toDetailPayload(r: DetailRow) {
  return showsGymDetails.value
    ? { exercise_name: r.exercise_name, sets: r.sets, reps: r.reps, weight_kg: r.weight_kg, exercise_item_id: r.exercise_item_id }
    : { exercise_name: r.exercise_name, duration_min: r.duration_min, yoga_stretch_item_id: r.yoga_stretch_item_id }
}

async function save() {
  if (!props.userId || !form.template_name.trim()) return
  saving.value = true
  saveError.value = null
  try {
    const details = detailRows.value.filter(isValidDetailRow).map(toDetailPayload)
    const basePayload = {
      template_name: form.template_name.trim(),
      exercise_type: form.exercise_type,
      duration_min: form.duration_min,
      details,
    }
    const result = isCreate.value
      ? await createWorkoutTemplate({ user_id: props.userId, ...basePayload })
      : await updateWorkoutTemplate(props.templateId as number, basePayload)
    emit('saved', result)
    emit('update:modelValue', false)
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : '儲存失敗，請稍後再試'
  } finally {
    saving.value = false
  }
}

const deleting = ref(false)

async function removeTemplate() {
  if (props.templateId === null) return
  if (!(await confirmDialog('刪除這個範本？'))) return
  deleting.value = true
  saveError.value = null
  try {
    await deleteWorkoutTemplate(props.templateId)
    emit('deleted', props.templateId)
    emit('update:modelValue', false)
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : '刪除失敗，請稍後再試'
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <Modal
    :model-value="modelValue"
    :title="isCreate ? '新增範本' : '編輯範本'"
    @update:model-value="(v) => emit('update:modelValue', v)"
  >
    <p v-if="loading" class="text-sm text-tea">載入中…</p>
    <p v-else-if="error" class="rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ error }}</p>

    <template v-else>
      <label class="block text-xs text-tea">
        範本名稱
        <input v-model="form.template_name" type="text" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
      </label>

      <div class="mt-3 grid grid-cols-2 gap-3">
        <label class="text-xs text-tea">
          類型
          <select v-model="form.exercise_type" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink">
            <option v-for="t in EXERCISE_TYPES" :key="t" :value="t">{{ t }}</option>
          </select>
        </label>
        <label class="text-xs text-tea">
          時長（分鐘）
          <input v-model.number="form.duration_min" type="number" min="1" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
        </label>
      </div>

      <div v-if="showsGymDetails || showsYogaStretchDetails" class="mt-4">
        <div class="flex items-center justify-between">
          <p class="text-xs text-tea">訓練項目明細</p>
          <button type="button" class="text-xs font-semibold text-accent hover:text-accent-bright" @click="addDetailRow">
            + 新增項目
          </button>
        </div>

        <template v-if="showsGymDetails">
          <div v-for="(row, i) in detailRows" :key="i" class="mt-2 grid grid-cols-[1fr_60px_60px_70px_auto] items-center gap-2">
            <ExerciseItemAutocomplete
              v-model="row.exercise_name"
              item-type="gym"
              :user-id="userId"
              placeholder="動作名稱"
              @select="(item) => onSelectLibraryItem(row, item)"
              @clear="() => onClearLibraryItem(row)"
            />
            <input v-model.number="row.sets" type="number" min="1" placeholder="組" class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
            <input v-model="row.reps" type="text" placeholder="次數" class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
            <input v-model.number="row.weight_kg" type="number" step="0.5" placeholder="kg" class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
            <button type="button" class="text-xs text-tea hover:text-alert" @click="removeDetailRow(i)">刪除</button>
          </div>
        </template>
        <template v-else>
          <div v-for="(row, i) in detailRows" :key="i" class="mt-2 grid grid-cols-[1fr_80px_auto] items-center gap-2">
            <ExerciseItemAutocomplete
              v-model="row.exercise_name"
              item-type="yoga_stretch"
              :yoga-type="form.exercise_type"
              :user-id="userId"
              placeholder="動作名稱"
              @select="(item) => onSelectLibraryItem(row, item)"
              @clear="() => onClearLibraryItem(row)"
            />
            <input v-model.number="row.duration_min" type="number" min="1" placeholder="時長(分)" class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
            <button type="button" class="text-xs text-tea hover:text-alert" @click="removeDetailRow(i)">刪除</button>
          </div>
        </template>
      </div>

      <p v-if="saveError" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ saveError }}</p>
      <button
        type="button"
        class="mt-4 w-full rounded-full bg-accent py-2.5 text-sm font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
        :disabled="saving || !form.template_name.trim()"
        @click="save"
      >
        {{ saving ? '儲存中…' : '儲存範本' }}
      </button>
      <button
        v-if="!isCreate"
        type="button"
        class="mt-2 w-full text-xs text-tea hover:text-alert disabled:opacity-50"
        :disabled="deleting"
        @click="removeTemplate"
      >
        {{ deleting ? '刪除中…' : '刪除範本' }}
      </button>
    </template>
  </Modal>
</template>

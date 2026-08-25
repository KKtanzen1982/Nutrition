<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import Modal from '../shared/Modal.vue'
import ExerciseItemAutocomplete from './ExerciseItemAutocomplete.vue'
import { createTrainingProgram } from './training_program_api'
import type { CreateTrainingProgramDayPayload, ExerciseItemLibraryEntry, TrainingProgram } from '../shared/types'

const EXERCISE_TYPES = ['健身房', '走路', '瑜珈', '拉伸']
const YOGA_STRETCH_TYPES = ['瑜珈', '拉伸']
const DAY_COUNT_OPTIONS = [3, 4, 5, 6, 7]

const props = defineProps<{
  modelValue: boolean
  userId: number | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  created: [program: TrainingProgram]
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

interface DayBuilder {
  day_label: string
  exercise_type: string
  duration_min: number | null
  detailRows: DetailRow[]
}

function emptyDay(): DayBuilder {
  return { day_label: '', exercise_type: EXERCISE_TYPES[0], duration_min: null, detailRows: [] }
}

const form = reactive({
  program_name: '',
  description: '',
})
const dayCount = ref(3)
const days = ref<DayBuilder[]>([emptyDay(), emptyDay(), emptyDay()])
const expandedIndex = ref(0)

watch(dayCount, (n) => {
  if (n > days.value.length) {
    while (days.value.length < n) days.value.push(emptyDay())
  } else if (n < days.value.length) {
    days.value.splice(n)
  }
})

function resetForm() {
  form.program_name = ''
  form.description = ''
  dayCount.value = 3
  days.value = [emptyDay(), emptyDay(), emptyDay()]
  expandedIndex.value = 0
  saveError.value = null
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) resetForm()
  },
)

function addDetailRow(day: DayBuilder) {
  day.detailRows.push(emptyDetailRow())
}
function removeDetailRow(day: DayBuilder, index: number) {
  day.detailRows.splice(index, 1)
}

function showsGymDetails(day: DayBuilder) {
  return day.exercise_type === '健身房'
}
function showsYogaStretchDetails(day: DayBuilder) {
  return YOGA_STRETCH_TYPES.includes(day.exercise_type)
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

function isValidDetailRow(day: DayBuilder, r: DetailRow): boolean {
  if (!r.exercise_name) return false
  if (showsGymDetails(day)) return r.sets !== null && !!r.reps
  if (showsYogaStretchDetails(day)) return r.duration_min !== null
  return false
}

function toDetailPayload(day: DayBuilder, r: DetailRow) {
  return showsGymDetails(day)
    ? { exercise_name: r.exercise_name, sets: r.sets, reps: r.reps, weight_kg: r.weight_kg, exercise_item_id: r.exercise_item_id }
    : { exercise_name: r.exercise_name, duration_min: r.duration_min, yoga_stretch_item_id: r.yoga_stretch_item_id }
}

const saving = ref(false)
const saveError = ref<string | null>(null)

const canSave = computed(() => !!props.userId && form.program_name.trim().length > 0)

async function save() {
  if (!props.userId || !form.program_name.trim()) return
  saving.value = true
  saveError.value = null
  try {
    const payload = {
      user_id: props.userId,
      program_name: form.program_name.trim(),
      description: form.description || null,
      days: days.value.map(
        (day, i): CreateTrainingProgramDayPayload => ({
          day_number: i + 1,
          day_label: day.day_label || null,
          exercise_type: day.exercise_type,
          duration_min: day.duration_min,
          details: day.detailRows.filter((r) => isValidDetailRow(day, r)).map((r) => toDetailPayload(day, r)),
        }),
      ),
    }
    const created = await createTrainingProgram(payload)
    emit('created', created)
    emit('update:modelValue', false)
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : '建立失敗，請稍後再試'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Modal :model-value="modelValue" title="新增訓練計畫" @update:model-value="(v) => emit('update:modelValue', v)">
    <label class="block text-xs text-tea">
      計畫名稱
      <input
        v-model="form.program_name"
        type="text"
        placeholder="例如「秋季增肌 PPL」"
        class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink"
      />
    </label>

    <label class="mt-3 block text-xs text-tea">
      說明（選填）
      <input v-model="form.description" type="text" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
    </label>

    <label class="mt-3 block text-xs text-tea">
      天數
      <select v-model.number="dayCount" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink">
        <option v-for="n in DAY_COUNT_OPTIONS" :key="n" :value="n">{{ n }} 天</option>
      </select>
    </label>

    <div class="mt-4 space-y-2">
      <div v-for="(day, dayIndex) in days" :key="dayIndex" class="rounded-xl border border-ink/10">
        <button
          type="button"
          class="flex w-full items-center justify-between px-3 py-2 text-left text-sm font-semibold text-ink"
          @click="expandedIndex = expandedIndex === dayIndex ? -1 : dayIndex"
        >
          <span>Day {{ dayIndex + 1 }}<span v-if="day.day_label" class="ml-1 font-normal text-tea">· {{ day.day_label }}</span></span>
          <span class="text-xs text-tea">{{ expandedIndex === dayIndex ? '收合' : '展開' }}</span>
        </button>

        <div v-if="expandedIndex === dayIndex" class="border-t border-ink/10 p-3">
          <div class="grid grid-cols-2 gap-3">
            <label class="text-xs text-tea">
              標籤（選填）
              <input v-model="day.day_label" type="text" placeholder="例如「推」" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
            </label>
            <label class="text-xs text-tea">
              類型
              <select v-model="day.exercise_type" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink">
                <option v-for="t in EXERCISE_TYPES" :key="t" :value="t">{{ t }}</option>
              </select>
            </label>
            <label class="text-xs text-tea">
              時長（分鐘）
              <input v-model.number="day.duration_min" type="number" min="1" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
            </label>
          </div>

          <div v-if="showsGymDetails(day) || showsYogaStretchDetails(day)" class="mt-3">
            <div class="flex items-center justify-between">
              <p class="text-xs text-tea">訓練項目明細</p>
              <button type="button" class="text-xs font-semibold text-accent hover:text-accent-bright" @click="addDetailRow(day)">
                + 新增項目
              </button>
            </div>

            <template v-if="showsGymDetails(day)">
              <div v-for="(row, i) in day.detailRows" :key="i" class="mt-2 grid grid-cols-[1fr_60px_60px_70px_auto] items-center gap-2">
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
                <button type="button" class="text-xs text-tea hover:text-alert" @click="removeDetailRow(day, i)">刪除</button>
              </div>
            </template>
            <template v-else>
              <div v-for="(row, i) in day.detailRows" :key="i" class="mt-2 grid grid-cols-[1fr_80px_auto] items-center gap-2">
                <ExerciseItemAutocomplete
                  v-model="row.exercise_name"
                  item-type="yoga_stretch"
                  :yoga-type="day.exercise_type"
                  :user-id="userId"
                  placeholder="動作名稱"
                  @select="(item) => onSelectLibraryItem(row, item)"
                  @clear="() => onClearLibraryItem(row)"
                />
                <input v-model.number="row.duration_min" type="number" min="1" placeholder="時長(分)" class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
                <button type="button" class="text-xs text-tea hover:text-alert" @click="removeDetailRow(day, i)">刪除</button>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>

    <p v-if="saveError" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ saveError }}</p>
    <button
      type="button"
      class="mt-4 w-full rounded-full bg-accent py-2.5 text-sm font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
      :disabled="saving || !canSave"
      @click="save"
    >
      {{ saving ? '建立中…' : '建立計畫' }}
    </button>
  </Modal>
</template>

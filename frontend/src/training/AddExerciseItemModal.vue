<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import Modal from '../shared/Modal.vue'
import { createExerciseItem, listExerciseItems } from './exercise_item_api'
import type { ExerciseItemLibraryEntry, ExerciseItemType, ExerciseLibraryItem } from '../shared/types'

const GYM_CATEGORIES = ['胸部', '背部', '下肢', '手臂', '核心', '有氧']

const props = defineProps<{
  modelValue: boolean
  itemType: ExerciseItemType
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  created: [item: ExerciseItemLibraryEntry]
}>()

const existingGymItems = ref<ExerciseLibraryItem[]>([])

const categoryOptions = computed(() => {
  const fromData = existingGymItems.value.map((i) => i.category)
  return [...new Set([...GYM_CATEGORIES, ...fromData])]
})
const muscleGroupOptions = computed(() => [...new Set(existingGymItems.value.map((i) => i.muscle_group).filter((v): v is string => !!v))].sort())
const equipmentOptions = computed(() => [...new Set(existingGymItems.value.map((i) => i.equipment).filter((v): v is string => !!v))].sort())

const form = reactive({
  item_name: '',
  category: GYM_CATEGORIES[0],
  muscle_group: '',
  equipment: '',
  default_sets: null as number | null,
  default_reps: '',
  yoga_type: '瑜珈',
  duration_min: null as number | null,
  difficulty: '',
  description: '',
})

function resetForm() {
  form.item_name = ''
  form.category = GYM_CATEGORIES[0]
  form.muscle_group = ''
  form.equipment = ''
  form.default_sets = null
  form.default_reps = ''
  form.yoga_type = '瑜珈'
  form.duration_min = null
  form.difficulty = ''
  form.description = ''
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      resetForm()
      error.value = null
      if (props.itemType === 'gym') {
        listExerciseItems('gym').then((items) => {
          existingGymItems.value = items as ExerciseLibraryItem[]
        })
      }
    }
  },
)

const saving = ref(false)
const error = ref<string | null>(null)

async function submit() {
  if (!form.item_name.trim()) return
  saving.value = true
  error.value = null
  try {
    const created = await createExerciseItem(
      props.itemType === 'gym'
        ? {
            type: 'gym',
            item_name: form.item_name.trim(),
            category: form.category,
            muscle_group: form.muscle_group || null,
            equipment: form.equipment || null,
            default_sets: form.default_sets,
            default_reps: form.default_reps || null,
            description: form.description || null,
          }
        : {
            type: 'yoga_stretch',
            item_name: form.item_name.trim(),
            yoga_type: form.yoga_type,
            duration_min: form.duration_min,
            difficulty: form.difficulty || undefined,
            description: form.description || null,
          },
    )
    emit('created', created)
    emit('update:modelValue', false)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '新增失敗，請稍後再試'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Modal :model-value="modelValue" title="新增動作" @update:model-value="(v) => emit('update:modelValue', v)">
    <label class="block text-xs text-tea">
      名稱
      <input v-model="form.item_name" type="text" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
    </label>

    <div v-if="itemType === 'gym'" class="mt-3 grid grid-cols-2 gap-3">
      <label class="text-xs text-tea">
        分類
        <input
          v-model="form.category"
          type="text"
          list="add-item-category-options"
          class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink"
        />
        <datalist id="add-item-category-options">
          <option v-for="c in categoryOptions" :key="c" :value="c" />
        </datalist>
      </label>
      <label class="text-xs text-tea">
        肌群
        <input
          v-model="form.muscle_group"
          type="text"
          list="add-item-muscle-group-options"
          class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink"
        />
        <datalist id="add-item-muscle-group-options">
          <option v-for="m in muscleGroupOptions" :key="m" :value="m" />
        </datalist>
      </label>
      <label class="text-xs text-tea">
        器材
        <input
          v-model="form.equipment"
          type="text"
          list="add-item-equipment-options"
          class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink"
        />
        <datalist id="add-item-equipment-options">
          <option v-for="e in equipmentOptions" :key="e" :value="e" />
        </datalist>
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

    <div v-else class="mt-3 grid grid-cols-2 gap-3">
      <label class="text-xs text-tea">
        類型
        <select v-model="form.yoga_type" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink">
          <option value="瑜珈">瑜珈</option>
          <option value="拉伸">拉伸</option>
        </select>
      </label>
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
      備註
      <textarea v-model="form.description" rows="2" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
    </label>

    <p v-if="error" class="mt-2 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ error }}</p>
    <button
      type="button"
      class="mt-3 w-full rounded-full bg-accent py-2 text-sm font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
      :disabled="saving || !form.item_name.trim()"
      @click="submit"
    >
      {{ saving ? '新增中…' : '新增動作' }}
    </button>
  </Modal>
</template>

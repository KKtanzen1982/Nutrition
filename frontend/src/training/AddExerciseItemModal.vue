<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import CustomSelect from '../shared/CustomSelect.vue'
import Modal from '../shared/Modal.vue'
import { useCustomOptionList } from '../shared/useCustomOptionList'
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

// 分類/肌群/器材：內建（分類）或既有資料裡出現過的值 + 使用者自訂的值（存在本機，可編輯/刪除）
const categoryCustom = useCustomOptionList('nutrition_custom_exercise_categories', GYM_CATEGORIES)
const muscleGroupCustom = useCustomOptionList('nutrition_custom_muscle_groups')
const equipmentCustom = useCustomOptionList('nutrition_custom_equipment')

const categoryOptions = computed(() => {
  const fromData = existingGymItems.value.map((i) => i.category)
  return [...new Set([...categoryCustom.allOptions.value, ...fromData])]
})
const muscleGroupOptions = computed(() => {
  const fromData = existingGymItems.value.map((i) => i.muscle_group).filter((v): v is string => !!v)
  return [...new Set([...muscleGroupCustom.allOptions.value, ...fromData])].sort()
})
const equipmentOptions = computed(() => {
  const fromData = existingGymItems.value.map((i) => i.equipment).filter((v): v is string => !!v)
  return [...new Set([...equipmentCustom.allOptions.value, ...fromData])].sort()
})

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
        <div class="mt-1">
          <CustomSelect
            v-model="form.category"
            :options="categoryOptions"
            :manageable-options="categoryCustom.customOptions.value"
            label="分類"
            :allow-empty="false"
            :add-option="categoryCustom.addOption"
            :rename-option="categoryCustom.renameOption"
            :remove-option="categoryCustom.removeOption"
          />
        </div>
      </label>
      <label class="text-xs text-tea">
        肌群
        <div class="mt-1">
          <CustomSelect
            v-model="form.muscle_group"
            :options="muscleGroupOptions"
            :manageable-options="muscleGroupCustom.customOptions.value"
            label="肌群"
            empty-label="未指定"
            :add-option="muscleGroupCustom.addOption"
            :rename-option="muscleGroupCustom.renameOption"
            :remove-option="muscleGroupCustom.removeOption"
          />
        </div>
      </label>
      <label class="text-xs text-tea">
        器材
        <div class="mt-1">
          <CustomSelect
            v-model="form.equipment"
            :options="equipmentOptions"
            :manageable-options="equipmentCustom.customOptions.value"
            label="器材"
            empty-label="未指定"
            :add-option="equipmentCustom.addOption"
            :rename-option="equipmentCustom.renameOption"
            :remove-option="equipmentCustom.removeOption"
          />
        </div>
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

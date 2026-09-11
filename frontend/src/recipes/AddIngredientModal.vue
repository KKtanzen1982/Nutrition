<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import Modal from '../shared/Modal.vue'
import { createIngredient } from './ingredient_api'
import type { Ingredient } from '../shared/types'

const CATEGORIES = ['蔬菜', '肉類', '穀物', '乳製品', '調味料', '其他']
const COST_LEVELS = ['低', '中', '高']

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  created: [ingredient: Ingredient]
}>()

const form = reactive({
  ingredient_name: '',
  category: CATEGORIES[0],
  unit: 'g',
  calories_per_100g: null as number | null,
  protein_per_100g: null as number | null,
  carbs_per_100g: null as number | null,
  fat_per_100g: null as number | null,
  fiber_per_100g: null as number | null,
  cost_level: '',
})

function resetForm() {
  form.ingredient_name = ''
  form.category = CATEGORIES[0]
  form.unit = 'g'
  form.calories_per_100g = null
  form.protein_per_100g = null
  form.carbs_per_100g = null
  form.fat_per_100g = null
  form.fiber_per_100g = null
  form.cost_level = ''
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      resetForm()
      error.value = null
    }
  },
)

const saving = ref(false)
const error = ref<string | null>(null)

async function submit() {
  if (!form.ingredient_name.trim()) return
  saving.value = true
  error.value = null
  try {
    const created = await createIngredient({
      ingredient_name: form.ingredient_name.trim(),
      category: form.category,
      unit: form.unit,
      calories_per_100g: form.calories_per_100g,
      protein_per_100g: form.protein_per_100g,
      carbs_per_100g: form.carbs_per_100g,
      fat_per_100g: form.fat_per_100g,
      fiber_per_100g: form.fiber_per_100g,
      cost_level: form.cost_level || null,
    })
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
  <Modal :model-value="modelValue" title="新增食材" @update:model-value="(v) => emit('update:modelValue', v)">
    <p class="text-xs text-tea">找不到需要的食材？在這裡直接建立，建立後會自動加進你剛剛在編輯的食譜裡。</p>

    <label class="mt-3 block text-xs text-tea">
      食材名稱
      <input v-model="form.ingredient_name" type="text" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
    </label>

    <div class="mt-3 grid grid-cols-2 gap-3">
      <label class="text-xs text-tea">
        分類
        <select v-model="form.category" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink">
          <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
        </select>
      </label>
      <label class="text-xs text-tea">
        成本等級
        <select v-model="form.cost_level" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink">
          <option value="">未設定</option>
          <option v-for="c in COST_LEVELS" :key="c" :value="c">{{ c }}</option>
        </select>
      </label>
      <label class="text-xs text-tea">
        單位
        <input v-model="form.unit" type="text" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
      </label>
      <label class="text-xs text-tea">
        熱量 /100g
        <input v-model.number="form.calories_per_100g" type="number" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
      </label>
      <label class="text-xs text-tea">
        蛋白質 /100g
        <input v-model.number="form.protein_per_100g" type="number" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
      </label>
      <label class="text-xs text-tea">
        碳水 /100g
        <input v-model.number="form.carbs_per_100g" type="number" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
      </label>
      <label class="text-xs text-tea">
        脂肪 /100g
        <input v-model.number="form.fat_per_100g" type="number" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
      </label>
      <label class="text-xs text-tea">
        纖維 /100g
        <input v-model.number="form.fiber_per_100g" type="number" class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
      </label>
    </div>

    <p v-if="error" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ error }}</p>
    <button
      type="button"
      class="mt-3 w-full rounded-full bg-accent py-2 text-sm font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
      :disabled="saving || !form.ingredient_name.trim()"
      @click="submit"
    >
      {{ saving ? '新增中…' : '新增食材' }}
    </button>
  </Modal>
</template>

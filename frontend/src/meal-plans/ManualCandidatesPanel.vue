<script setup lang="ts">
// 推薦流程第2步：在跑推薦之前，讓使用者寫入預計要用的食材或食譜，依類別強制併入候選清單
// （食譜名稱→直接鎖定該類別；食材名稱→列出含此食材的食譜供挑選），跟後端 preview 的
// manual_candidates 對應（見 backend/meal_plans/services.py 的 preview_plan）。
import { ref } from 'vue'
import { searchRecipesByIngredient, searchRecipesByName } from '../recipes/recipe_api'
import type { PreviewRecipe, RecipeSearchResult } from '../shared/types'

const CATEGORIES = ['主食', '肉', '菜', '湯', '早餐', '下午茶']

const props = defineProps<{ modelValue: Record<string, PreviewRecipe[]> }>()
const emit = defineEmits<{ 'update:modelValue': [value: Record<string, PreviewRecipe[]>] }>()

const category = ref(CATEGORIES[0])
const mode = ref<'name' | 'ingredient'>('name')
const query = ref('')
const results = ref<RecipeSearchResult[]>([])
const searching = ref(false)
const error = ref<string | null>(null)

async function runSearch() {
  if (!query.value.trim()) return
  searching.value = true
  error.value = null
  try {
    results.value = mode.value === 'name'
      ? await searchRecipesByName(query.value.trim(), category.value)
      : await searchRecipesByIngredient(query.value.trim(), category.value)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '搜尋失敗'
  } finally {
    searching.value = false
  }
}

function alreadyAdded(recipeId: number): boolean {
  return (props.modelValue[category.value] ?? []).some((c) => c.recipe_id === recipeId)
}

function addCandidate(r: RecipeSearchResult) {
  if (alreadyAdded(r.id)) return
  const current = props.modelValue[category.value] ?? []
  emit('update:modelValue', {
    ...props.modelValue,
    [category.value]: [...current, { recipe_id: r.id, recipe_name: r.recipe_name }],
  })
}

function removeCandidate(cat: string, recipeId: number) {
  emit('update:modelValue', {
    ...props.modelValue,
    [cat]: (props.modelValue[cat] ?? []).filter((c) => c.recipe_id !== recipeId),
  })
}
</script>

<template>
  <div class="rounded-xl border border-ink/10 p-3">
    <p class="text-sm font-semibold text-ink">預計要使用的食材或食譜（選填）</p>
    <p class="mt-1 text-xs text-tea">
      指定食譜會直接鎖定進對應類別的候選清單；指定食材會列出含這個食材的食譜供你挑選要不要加入候選
    </p>

    <div class="mt-2 flex flex-wrap gap-2">
      <select v-model="category" class="rounded-lg border border-ink/15 bg-bg px-2 py-1.5 text-xs text-ink">
        <option v-for="c in CATEGORIES" :key="c" :value="c">{{ c }}</option>
      </select>
      <div class="flex rounded-lg border border-ink/15 text-xs">
        <button
          type="button"
          class="px-2 py-1.5"
          :class="mode === 'name' ? 'bg-accent text-on-accent' : 'text-ink hover:bg-bg'"
          @click="mode = 'name'"
        >
          依食譜名稱
        </button>
        <button
          type="button"
          class="px-2 py-1.5"
          :class="mode === 'ingredient' ? 'bg-accent text-on-accent' : 'text-ink hover:bg-bg'"
          @click="mode = 'ingredient'"
        >
          依食材名稱
        </button>
      </div>
    </div>

    <div class="mt-2 flex gap-2">
      <input
        v-model="query"
        type="text"
        :placeholder="mode === 'name' ? '食譜名稱' : '食材名稱'"
        class="w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
        @keydown.enter="runSearch"
      />
      <button
        type="button"
        class="shrink-0 rounded-lg border border-ink/15 px-3 py-2 text-xs font-semibold text-ink hover:bg-bg disabled:opacity-50"
        :disabled="searching"
        @click="runSearch"
      >
        {{ searching ? '搜尋中…' : '搜尋' }}
      </button>
    </div>
    <p v-if="error" class="mt-2 rounded-lg bg-alert/10 px-3 py-2 text-xs text-alert">{{ error }}</p>

    <ul v-if="results.length" class="mt-2 divide-y divide-ink/10">
      <li v-for="r in results" :key="r.id" class="flex items-center justify-between py-1.5 text-sm">
        <span class="text-ink">{{ r.recipe_name }}<span class="text-tea">（{{ r.category }}）</span></span>
        <button
          type="button"
          class="text-xs font-semibold text-accent hover:text-accent-bright disabled:opacity-50"
          :disabled="alreadyAdded(r.id)"
          @click="addCandidate(r)"
        >
          {{ alreadyAdded(r.id) ? '已加入' : `加入「${category}」` }}
        </button>
      </li>
    </ul>

    <div v-if="Object.values(modelValue).some((list) => list.length)" class="mt-3 border-t border-ink/10 pt-2">
      <p class="text-xs font-semibold text-tea">已鎖定的候選</p>
      <div v-for="(list, cat) in modelValue" :key="cat">
        <ul v-if="list.length" class="mt-1 divide-y divide-ink/10">
          <li v-for="c in list" :key="c.recipe_id" class="flex items-center justify-between py-1 text-xs">
            <span class="text-ink">{{ cat }}｜{{ c.recipe_name }}</span>
            <button type="button" class="text-tea hover:text-alert" @click="removeCandidate(cat, c.recipe_id)">移除</button>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

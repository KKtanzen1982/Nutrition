<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import CardShell from '../shared/CardShell.vue'
import { fetchShoppingList } from './shopping_list_api'
import type { ShoppingListDetail } from '../shared/types'

const props = defineProps<{ listId: number | null }>()

const loading = ref(false)
const error = ref<string | null>(null)
const list = ref<ShoppingListDetail | null>(null)

async function load(listId: number | null) {
  if (listId === null) {
    list.value = null
    return
  }
  loading.value = true
  error.value = null
  try {
    list.value = await fetchShoppingList(listId)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '讀取購物清單失敗'
  } finally {
    loading.value = false
  }
}

watchEffect(() => {
  load(props.listId)
})

const allItems = computed(() =>
  Object.values(list.value?.items_by_location ?? {}).flatMap((groups) => groups.flatMap((g) => g.items)),
)
const purchasedCount = computed(() => allItems.value.filter((i) => i.is_purchased).length)
const totalCount = computed(() => allItems.value.length)
const progressPct = computed(() => (totalCount.value === 0 ? 0 : Math.round((purchasedCount.value / totalCount.value) * 100)))
</script>

<template>
  <CardShell
    title="購物清單"
    to="/shopping-list"
    :loading="loading"
    :error="error"
    :is-empty="props.listId === null"
    empty-text="尚未生成購物清單"
  >
    <div v-if="list">
      <p class="font-serif text-4xl leading-none text-ink">
        {{ purchasedCount }}<small class="text-base text-tea">/{{ totalCount }} 項</small>
      </p>
      <p class="mt-2 text-xs text-tea">狀態：{{ list.status }}</p>
      <div class="mt-3 h-[3px] overflow-hidden rounded-full bg-accent-tint">
        <span class="block h-full rounded-full bg-accent" :style="{ width: `${progressPct}%` }" />
      </div>
    </div>
  </CardShell>
</template>

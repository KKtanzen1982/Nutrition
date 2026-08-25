<script setup lang="ts">
import { useRouter } from 'vue-router'

const props = defineProps<{
  title: string
  loading?: boolean
  error?: string | null
  isEmpty?: boolean
  emptyText?: string
  to?: string
}>()

const router = useRouter()

function go() {
  if (props.to) router.push(props.to)
}
</script>

<template>
  <section
    class="rounded-2xl border border-ink/10 bg-surface p-5"
    :class="to ? 'cursor-pointer transition hover:border-accent/40 hover:shadow-sm' : ''"
    :role="to ? 'button' : undefined"
    :tabindex="to ? 0 : undefined"
    @click="go"
    @keydown.enter="go"
  >
    <header class="mb-4 flex items-center justify-between">
      <div class="flex items-center gap-1.5">
        <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-ink" aria-hidden="true" />
        <h2 class="border-b-[1.5px] border-accent pb-1 text-[11.5px] font-semibold uppercase tracking-wide text-muted">
          {{ title }}
        </h2>
      </div>
      <slot name="actions" />
    </header>

    <div v-if="loading" class="py-6 text-center text-sm text-tea">載入中…</div>
    <div v-else-if="error" class="rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">
      {{ error }}
    </div>
    <div v-else-if="isEmpty" class="py-6 text-center text-sm text-tea">
      {{ emptyText ?? '尚無資料' }}
    </div>
    <slot v-else />
  </section>
</template>

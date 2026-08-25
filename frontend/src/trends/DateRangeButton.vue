<script setup lang="ts">
defineProps<{ from: string; to: string; max?: string }>()
const emit = defineEmits<{ 'update:from': [string]; 'update:to': [string] }>()

function onFromInput(e: Event) {
  emit('update:from', (e.target as HTMLInputElement).value)
}
function onToInput(e: Event) {
  emit('update:to', (e.target as HTMLInputElement).value)
}
</script>

<template>
  <details class="relative inline-block">
    <summary
      class="flex cursor-pointer list-none items-center gap-1.5 rounded-lg border border-ink/15 bg-bg px-3 py-1.5 text-sm text-ink select-none [&::-webkit-details-marker]:hidden"
    >
      <span aria-hidden="true">📅</span>
      <span>{{ from }} ～ {{ to }}</span>
    </summary>
    <div class="absolute z-10 mt-1 flex items-center gap-2 rounded-lg border border-ink/15 bg-surface p-3 shadow-md">
      <input
        :value="from"
        type="date"
        :max="to"
        class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink"
        @input="onFromInput"
      />
      <span class="text-xs text-tea">至</span>
      <input
        :value="to"
        type="date"
        :min="from"
        :max="max"
        class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink"
        @input="onToInput"
      />
    </div>
  </details>
</template>

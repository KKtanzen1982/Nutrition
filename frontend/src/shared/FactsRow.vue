<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string
    editing?: boolean
  }>(),
  { editing: false },
)
</script>

<template>
  <div class="flex items-baseline justify-between gap-4 border-t border-ink/10 py-3">
    <dt class="shrink-0 text-[11.5px] font-semibold uppercase tracking-wide text-muted">{{ label }}</dt>
    <dd class="flex-1 text-right">
      <template v-if="editing">
        <slot name="input" />
      </template>
      <span v-else class="font-serif text-lg text-ink"><slot /></span>
    </dd>
  </div>
</template>

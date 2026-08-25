<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'

const props = defineProps<{
  modelValue: boolean
  title: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

function close() {
  emit('update:modelValue', false)
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && props.modelValue) close()
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div v-if="modelValue" class="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4">
      <div class="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-ink/10 bg-surface p-6 shadow-xl">
        <div class="flex items-center justify-between">
          <h2 class="font-serif text-lg text-ink">{{ title }}</h2>
          <button
            type="button"
            class="rounded-full px-2 py-1 text-sm text-tea hover:text-ink"
            aria-label="關閉"
            @click="close"
          >
            ✕
          </button>
        </div>
        <div class="mt-4">
          <slot />
        </div>
      </div>
    </div>
  </Teleport>
</template>

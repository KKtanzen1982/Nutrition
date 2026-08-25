<script setup lang="ts">
import { useConfirmDialog } from './useConfirmDialog'

const { state, respond } = useConfirmDialog()
</script>

<template>
  <Teleport to="body">
    <div v-if="state.open" class="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4">
      <div class="w-full max-w-sm rounded-2xl border border-ink/10 bg-surface p-6 shadow-xl">
        <p class="text-sm text-ink">{{ state.message }}</p>
        <div class="mt-5 flex justify-end gap-2">
          <button
            type="button"
            class="rounded-full px-4 py-1.5 text-sm font-medium text-tea hover:text-ink"
            @click="respond(false)"
          >
            取消
          </button>
          <button
            type="button"
            class="rounded-full bg-alert px-4 py-1.5 text-sm font-semibold text-on-accent hover:opacity-90"
            @click="respond(true)"
          >
            確定
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

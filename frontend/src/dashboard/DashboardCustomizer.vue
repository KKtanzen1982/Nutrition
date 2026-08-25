<script setup lang="ts">
import { ref } from 'vue'
import { CARD_LABELS, useDashboardLayout } from './useDashboardLayout'

const { layout, toggleVisible, moveCard } = useDashboardLayout()
const open = ref(false)
</script>

<template>
  <div class="relative">
    <button
      class="rounded-full border border-ink/15 px-3 py-1.5 text-sm text-tea hover:border-ink/30 hover:text-ink"
      @click="open = !open"
    >
      自訂卡片
    </button>

    <div
      v-if="open"
      class="absolute right-0 z-10 mt-2 w-64 rounded-xl border border-ink/10 bg-surface p-3 shadow-lg"
    >
      <ul class="space-y-1">
        <li
          v-for="(card, index) in layout"
          :key="card.id"
          class="flex items-center justify-between rounded-lg px-2 py-1.5 text-sm hover:bg-accent-tint/50"
        >
          <label class="flex items-center gap-2">
            <input type="checkbox" :checked="card.visible" class="accent-accent" @change="toggleVisible(card.id)" />
            <span :class="!card.visible ? 'text-muted line-through' : 'text-ink'">{{ CARD_LABELS[card.id] }}</span>
          </label>
          <div class="flex gap-1">
            <button
              class="text-tea hover:text-ink disabled:opacity-30"
              :disabled="index === 0"
              @click="moveCard(card.id, -1)"
            >
              ↑
            </button>
            <button
              class="text-tea hover:text-ink disabled:opacity-30"
              :disabled="index === layout.length - 1"
              @click="moveCard(card.id, 1)"
            >
              ↓
            </button>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

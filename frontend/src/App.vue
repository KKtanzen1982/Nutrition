<script setup lang="ts">
import { useRoute } from 'vue-router'
import UserSwitcher from './shared/UserSwitcher.vue'
import ConfirmDialog from './shared/ConfirmDialog.vue'

const route = useRoute()

const navLinks = [
  { path: '/', label: '總覽' },
  { path: '/profile', label: '個人資料' },
  { path: '/weight', label: '體重' },
  { path: '/exercise', label: '運動' },
  { path: '/exercise-library', label: '動作資料庫' },
  { path: '/training-calendar', label: '訓練計畫' },
  { path: '/meal-plan', label: '週推薦' },
  { path: '/shopping-list', label: '購物清單' },
  { path: '/recipes', label: '食譜' },
  { path: '/ingredients', label: '食材' },
  { path: '/trends', label: '趨勢' },
  { path: '/settings', label: '設定' },
]
</script>

<template>
  <div class="min-h-screen bg-bg text-ink">
    <nav class="border-b border-ink/10 bg-surface">
      <div class="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-4 gap-y-1 px-4 py-3">
        <span class="font-serif text-lg">飲食管理</span>
        <div class="flex flex-wrap gap-1">
          <RouterLink
            v-for="link in navLinks"
            :key="link.path"
            :to="link.path"
            class="px-3 py-1.5 text-sm font-semibold uppercase tracking-wide"
            :class="route.path === link.path ? 'border-b-2 border-accent text-ink' : 'text-tea hover:text-ink'"
          >
            {{ link.label }}
          </RouterLink>
        </div>
      </div>
    </nav>
    <div class="mx-auto max-w-5xl px-4 pt-4">
      <UserSwitcher />
    </div>
    <RouterView />
    <ConfirmDialog />
  </div>
</template>

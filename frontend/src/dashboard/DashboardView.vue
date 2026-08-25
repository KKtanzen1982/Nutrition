<script setup lang="ts">
import CardExercise from '../fitness/CardExercise.vue'
import CardShoppingList from '../shopping/CardShoppingList.vue'
import CardTodayMeals from '../meal-plans/CardTodayMeals.vue'
import CardWeight from '../fitness/CardWeight.vue'
import DashboardCustomizer from './DashboardCustomizer.vue'
import { useDashboardLayout } from './useDashboardLayout'
import { useHouseholdConfig } from '../shared/useHouseholdConfig'

const { config, isConfigured, userIcon } = useHouseholdConfig()
const { visibleCardIds } = useDashboardLayout()

const personalCardIds = ['weight', 'exercise', 'today-meals']
</script>

<template>
  <div class="mx-auto max-w-5xl px-4 py-6">
    <header class="mb-6 flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="font-serif text-2xl text-ink">今日總覽</h1>
        <p class="text-sm text-tea">同時檢視每位成員的狀態</p>
      </div>
      <DashboardCustomizer v-if="isConfigured" />
    </header>

    <div v-if="!isConfigured" class="rounded-2xl border border-dashed border-ink/20 p-6 text-center text-tea">
      請先在上方完成使用者設定
    </div>

    <div v-else class="space-y-8">
      <section v-for="user in config.users" :key="user.id">
        <h2 class="mb-3 flex items-center gap-1.5 font-serif text-lg text-ink">
          <span aria-hidden="true">{{ userIcon(user.id) }}</span> {{ user.name }}
        </h2>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <template v-for="id in visibleCardIds.filter((c) => personalCardIds.includes(c))" :key="id">
            <CardWeight v-if="id === 'weight'" :user-id="user.id" />
            <CardExercise v-else-if="id === 'exercise'" :user-id="user.id" />
            <CardTodayMeals
              v-else-if="id === 'today-meals'"
              :plan-id="config.currentMealPlanId"
              :user-id="user.id"
            />
          </template>
        </div>
      </section>

      <section v-if="visibleCardIds.includes('shopping-list')">
        <h2 class="mb-3 font-serif text-lg text-ink">共用</h2>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <CardShoppingList :list-id="config.currentShoppingListId" />
        </div>
      </section>
    </div>
  </div>
</template>

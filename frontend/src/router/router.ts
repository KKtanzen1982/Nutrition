import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../dashboard/DashboardView.vue'
import ExerciseView from '../fitness/ExerciseView.vue'
import ExerciseLibraryView from '../training/ExerciseLibraryView.vue'
import TrainingCalendarView from '../training/TrainingCalendarView.vue'
import IngredientView from '../recipes/IngredientView.vue'
import MealPlanView from '../meal-plans/MealPlanView.vue'
import ProfileView from '../users/ProfileView.vue'
import RecipeView from '../recipes/RecipeView.vue'
import SettingsView from '../settings/SettingsView.vue'
import ShoppingHistoryView from '../shopping/ShoppingHistoryView.vue'
import ShoppingListView from '../shopping/ShoppingListView.vue'
import TrendsView from '../trends/TrendsView.vue'
import WeightView from '../fitness/WeightView.vue'

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'dashboard', component: DashboardView },
    { path: '/profile', name: 'profile', component: ProfileView },
    { path: '/weight', name: 'weight', component: WeightView },
    { path: '/exercise', name: 'exercise', component: ExerciseView },
    { path: '/exercise-library', name: 'exercise-library', component: ExerciseLibraryView },
    { path: '/training-calendar', name: 'training-calendar', component: TrainingCalendarView },
    { path: '/meal-plan', name: 'meal-plan', component: MealPlanView },
    { path: '/shopping-list', name: 'shopping-list', component: ShoppingListView },
    { path: '/shopping-list/history', name: 'shopping-list-history', component: ShoppingHistoryView },
    { path: '/recipes', name: 'recipes', component: RecipeView },
    { path: '/ingredients', name: 'ingredients', component: IngredientView },
    { path: '/trends', name: 'trends', component: TrendsView },
    { path: '/settings', name: 'settings', component: SettingsView },
  ],
})

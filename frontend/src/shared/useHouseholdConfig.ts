import { computed } from 'vue'
import { useLocalStorage } from './useLocalStorage'

export interface KnownUser {
  id: number
  name: string
}

interface HouseholdConfig {
  users: KnownUser[]
  activeUserId: number | null
  currentMealPlanId: number | null
  currentShoppingListId: number | null
}

const STORAGE_KEY = 'block7_household_config'
const CUTE_ICONS = ['🐻', '🐰', '🐱', '🐼', '🦊', '🐨']

const defaultConfig: HouseholdConfig = {
  users: [],
  activeUserId: null,
  currentMealPlanId: null,
  currentShoppingListId: null,
}

// Module-scoped singleton so every component shares the same reactive config
// without needing a full store library for just one page.
const config = useLocalStorage<HouseholdConfig>(STORAGE_KEY, defaultConfig)

export function useHouseholdConfig() {
  const isConfigured = computed(() => config.value.users.length >= 1)
  const activeUser = computed(() => config.value.users.find((u) => u.id === config.value.activeUserId) ?? null)

  function setUsers(users: KnownUser[]) {
    config.value.users = users
    if (!users.some((u) => u.id === config.value.activeUserId)) {
      config.value.activeUserId = users[0]?.id ?? null
    }
  }

  function setActiveUser(userId: number) {
    config.value.activeUserId = userId
  }

  function setCurrentMealPlanId(id: number | null) {
    config.value.currentMealPlanId = id
  }

  function setCurrentShoppingListId(id: number | null) {
    config.value.currentShoppingListId = id
  }

  function userIcon(userId: number): string {
    const index = config.value.users.findIndex((u) => u.id === userId)
    return CUTE_ICONS[index] ?? '🙂'
  }

  return {
    config,
    isConfigured,
    activeUser,
    setUsers,
    setActiveUser,
    setCurrentMealPlanId,
    setCurrentShoppingListId,
    userIcon,
  }
}

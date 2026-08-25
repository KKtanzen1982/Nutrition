import { computed } from 'vue'
import { useLocalStorage } from '../shared/useLocalStorage'

export interface DashboardCardConfig {
  id: string
  visible: boolean
}

const STORAGE_KEY = 'block7_dashboard_layout'

const defaultLayout: DashboardCardConfig[] = [
  { id: 'weight', visible: true },
  { id: 'exercise', visible: true },
  { id: 'today-meals', visible: true },
  { id: 'shopping-list', visible: true },
]

export const CARD_LABELS: Record<string, string> = {
  weight: '體重',
  exercise: '本週運動',
  'today-meals': '今日菜單',
  'shopping-list': '購物清單',
}

const layout = useLocalStorage<DashboardCardConfig[]>(STORAGE_KEY, defaultLayout)

export function useDashboardLayout() {
  const visibleCardIds = computed(() => layout.value.filter((c) => c.visible).map((c) => c.id))

  function toggleVisible(id: string) {
    const card = layout.value.find((c) => c.id === id)
    if (card) card.visible = !card.visible
  }

  function moveCard(id: string, direction: -1 | 1) {
    const index = layout.value.findIndex((c) => c.id === id)
    const target = index + direction
    if (index < 0 || target < 0 || target >= layout.value.length) return
    const temp = layout.value[index]
    layout.value[index] = layout.value[target]
    layout.value[target] = temp
  }

  return { layout, visibleCardIds, toggleVisible, moveCard }
}

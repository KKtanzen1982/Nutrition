<script setup lang="ts">
import { computed, ref, watchEffect } from 'vue'
import TrainingProgramFormModal from './TrainingProgramFormModal.vue'
import { deleteTrainingProgram, fetchTrainingPrograms } from './training_program_api'
import {
  createTrainingSchedule,
  deleteTrainingSchedule,
  fetchTrainingSchedule,
  updateTrainingSchedule,
} from './training_schedule_api'
import { fetchTrainingTargets, updateTrainingTargets } from './training_target_api'
import { fetchWeeklyProgress } from './training_progress_api'
import { toISODate } from '../shared/date_utils'
import { useConfirmDialog } from '../shared/useConfirmDialog'
import { useHouseholdConfig } from '../shared/useHouseholdConfig'
import type {
  TrainingProgram,
  TrainingProgramDay,
  TrainingScheduleEntry,
  TrainingTarget,
  WeeklyProgress,
} from '../shared/types'

const { activeUser } = useHouseholdConfig()
const { confirmDialog } = useConfirmDialog()

// ---- 計畫清單 ----

const programs = ref<TrainingProgram[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

async function loadPrograms(userId: number) {
  loading.value = true
  error.value = null
  try {
    programs.value = await fetchTrainingPrograms(userId)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '讀取訓練計畫失敗'
  } finally {
    loading.value = false
  }
}

watchEffect(() => {
  if (activeUser.value) loadPrograms(activeUser.value.id)
})

const showForm = ref(false)

function onCreated(program: TrainingProgram) {
  programs.value = [...programs.value, program]
}

async function removeProgram(program: TrainingProgram) {
  if (!(await confirmDialog(`刪除計畫「${program.program_name}」？（已建立的每日範本不會被刪除）`))) return
  try {
    await deleteTrainingProgram(program.id)
    programs.value = programs.value.filter((p) => p.id !== program.id)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '刪除失敗'
  }
}

// ---- 月曆 ----

const cursor = ref(new Date())
const monthParam = computed(() => {
  const y = cursor.value.getFullYear()
  const m = String(cursor.value.getMonth() + 1).padStart(2, '0')
  return `${y}-${m}`
})
const monthLabel = computed(() => `${cursor.value.getFullYear()} 年 ${cursor.value.getMonth() + 1} 月`)

function prevMonth() {
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() - 1, 1)
}
function nextMonth() {
  cursor.value = new Date(cursor.value.getFullYear(), cursor.value.getMonth() + 1, 1)
}

const scheduleEntries = ref<TrainingScheduleEntry[]>([])
const scheduleLoading = ref(true)
const scheduleError = ref<string | null>(null)

async function loadSchedule(userId: number, month: string) {
  scheduleLoading.value = true
  scheduleError.value = null
  try {
    scheduleEntries.value = await fetchTrainingSchedule(userId, month)
  } catch (e) {
    scheduleError.value = e instanceof Error ? e.message : '讀取排程失敗'
  } finally {
    scheduleLoading.value = false
  }
}

watchEffect(() => {
  if (activeUser.value) loadSchedule(activeUser.value.id, monthParam.value)
})

const scheduleByDate = computed(() => {
  const map = new Map<string, TrainingScheduleEntry>()
  for (const s of scheduleEntries.value) map.set(s.scheduled_date, s)
  return map
})

interface CalendarCell {
  date: Date
  iso: string
  inMonth: boolean
}

const calendarCells = computed<CalendarCell[]>(() => {
  const year = cursor.value.getFullYear()
  const month = cursor.value.getMonth()
  const firstOfMonth = new Date(year, month, 1)
  const firstWeekday = (firstOfMonth.getDay() + 6) % 7 // 0 = Monday
  const gridStart = new Date(year, month, 1 - firstWeekday)

  const cells: CalendarCell[] = []
  for (let i = 0; i < 42; i++) {
    const d = new Date(gridStart)
    d.setDate(gridStart.getDate() + i)
    cells.push({ date: d, iso: toISODate(d), inMonth: d.getMonth() === month })
  }
  return cells
})

const todayIso = toISODate(new Date())

// ---- 排程互動：點卡片 → 點日期格（不用拖曳） ----

const armedDay = ref<{ programDayId: number; label: string } | null>(null)
const movingScheduleId = ref<number | null>(null)
const selectedScheduleIso = ref<string | null>(null)
const actionError = ref<string | null>(null)

function armDay(program: TrainingProgram, day: TrainingProgramDay) {
  movingScheduleId.value = null
  selectedScheduleIso.value = null
  armedDay.value = { programDayId: day.id, label: day.day_label || `${program.program_name} Day${day.day_number}` }
}

function cancelArmed() {
  armedDay.value = null
  movingScheduleId.value = null
}

async function onCellClick(iso: string) {
  actionError.value = null
  const existing = scheduleByDate.value.get(iso)

  if (movingScheduleId.value !== null) {
    if (existing) {
      actionError.value = '這天已經有排程了，選別天'
      return
    }
    try {
      await updateTrainingSchedule(movingScheduleId.value, { scheduled_date: iso })
      movingScheduleId.value = null
      selectedScheduleIso.value = null
      if (activeUser.value) await loadSchedule(activeUser.value.id, monthParam.value)
    } catch (e) {
      actionError.value = e instanceof Error ? e.message : '搬移失敗'
    }
    return
  }

  if (existing) {
    selectedScheduleIso.value = selectedScheduleIso.value === iso ? null : iso
    return
  }

  if (armedDay.value) {
    try {
      await createTrainingSchedule({ program_day_id: armedDay.value.programDayId, scheduled_date: iso })
      armedDay.value = null
      if (activeUser.value) await loadSchedule(activeUser.value.id, monthParam.value)
    } catch (e) {
      actionError.value = e instanceof Error ? e.message : '排程失敗'
    }
  }
}

function startMoving(scheduleId: number) {
  movingScheduleId.value = scheduleId
  selectedScheduleIso.value = null
}

async function markSkipped(scheduleId: number) {
  actionError.value = null
  try {
    await updateTrainingSchedule(scheduleId, { status: '已跳過' })
    selectedScheduleIso.value = null
    if (activeUser.value) await loadSchedule(activeUser.value.id, monthParam.value)
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : '標記失敗'
  }
}

async function removeSchedule(scheduleId: number) {
  actionError.value = null
  try {
    await deleteTrainingSchedule(scheduleId)
    selectedScheduleIso.value = null
    if (activeUser.value) await loadSchedule(activeUser.value.id, monthParam.value)
  } catch (e) {
    actionError.value = e instanceof Error ? e.message : '移除失敗'
  }
}

const selectedSchedule = computed(() =>
  selectedScheduleIso.value ? scheduleByDate.value.get(selectedScheduleIso.value) ?? null : null,
)

const needsActualLog = computed(
  () =>
    selectedSchedule.value !== null &&
    selectedSchedule.value.status === '已排程' &&
    selectedSchedule.value.scheduled_date < todayIso,
)

function statusColor(status: TrainingScheduleEntry['status']) {
  if (status === '已完成') return 'bg-accent text-on-accent'
  if (status === '已跳過') return 'bg-ink/10 text-tea line-through'
  return 'bg-accent-tint text-ink'
}

// ---- 每週目標 ----

const targets = ref<TrainingTarget[]>([])
const targetsLoading = ref(true)
const targetsError = ref<string | null>(null)
const savingTargets = ref(false)
const targetsSaved = ref(false)
const showTargets = ref(false)

async function loadTargets(userId: number) {
  targetsLoading.value = true
  targetsError.value = null
  try {
    targets.value = await fetchTrainingTargets(userId)
  } catch (e) {
    targetsError.value = e instanceof Error ? e.message : '讀取每週目標失敗'
  } finally {
    targetsLoading.value = false
  }
}

watchEffect(() => {
  if (activeUser.value) loadTargets(activeUser.value.id)
})

async function saveTargets() {
  if (!activeUser.value) return
  savingTargets.value = true
  targetsError.value = null
  targetsSaved.value = false
  try {
    targets.value = await updateTrainingTargets(activeUser.value.id, targets.value)
    targetsSaved.value = true
    window.setTimeout(() => {
      targetsSaved.value = false
    }, 2000)
  } catch (e) {
    targetsError.value = e instanceof Error ? e.message : '儲存失敗'
  } finally {
    savingTargets.value = false
    if (activeUser.value) loadProgress(activeUser.value.id)
  }
}

// ---- 每週達成度 ----

const progress = ref<WeeklyProgress | null>(null)
const progressLoading = ref(true)
const progressError = ref<string | null>(null)

async function loadProgress(userId: number) {
  progressLoading.value = true
  progressError.value = null
  try {
    progress.value = await fetchWeeklyProgress(userId)
  } catch (e) {
    progressError.value = e instanceof Error ? e.message : '讀取每週達成度失敗'
  } finally {
    progressLoading.value = false
  }
}

watchEffect(() => {
  if (activeUser.value) loadProgress(activeUser.value.id)
})
</script>

<template>
  <div class="mx-auto max-w-2xl px-4 py-8">
    <div v-if="!activeUser" class="rounded-2xl border border-dashed border-ink/20 p-6 text-center text-tea">
      請先在上方完成使用者設定
    </div>

    <template v-else>
      <div class="flex items-center justify-between">
        <h1 class="font-serif text-2xl text-ink">訓練計畫</h1>
        <button
          type="button"
          class="rounded-full bg-accent px-3 py-1.5 text-xs font-semibold text-on-accent hover:bg-accent-bright"
          @click="showForm = true"
        >
          + 新增訓練計畫
        </button>
      </div>

      <p v-if="loading" class="mt-8 text-sm text-tea">載入中…</p>
      <p v-else-if="error" class="mt-8 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ error }}</p>
      <p v-else-if="programs.length === 0" class="mt-8 text-sm text-tea">還沒有任何訓練計畫</p>

      <ul v-else class="mt-6 space-y-3">
        <li v-for="program in programs" :key="program.id" class="rounded-2xl border border-ink/10 bg-surface p-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="font-serif text-lg text-ink">{{ program.program_name }}</p>
              <p v-if="program.description" class="text-xs text-tea">{{ program.description }}</p>
            </div>
            <button type="button" class="text-xs text-tea hover:text-alert" @click="removeProgram(program)">刪除</button>
          </div>
          <ul class="mt-2 flex flex-wrap gap-1.5">
            <li
              v-for="day in program.days"
              :key="day.id"
              class="cursor-pointer rounded-full px-2.5 py-1 text-xs transition"
              :class="
                armedDay?.programDayId === day.id
                  ? 'bg-accent text-on-accent'
                  : 'bg-accent-tint text-ink hover:bg-accent-tint/70'
              "
              @click="armDay(program, day)"
            >
              Day {{ day.day_number }}<span v-if="day.day_label"> · {{ day.day_label }}</span>
            </li>
          </ul>
        </li>
      </ul>

      <p v-if="armedDay" class="mt-4 rounded-lg bg-accent-tint px-3 py-2 text-sm text-ink">
        已選取「{{ armedDay.label }}」，點下面月曆的日期格子排上去
        <button type="button" class="ml-2 text-xs font-semibold text-tea underline" @click="cancelArmed">取消</button>
      </p>
      <p v-if="movingScheduleId !== null" class="mt-4 rounded-lg bg-accent-tint px-3 py-2 text-sm text-ink">
        選一個新日期把這筆排程搬過去
        <button type="button" class="ml-2 text-xs font-semibold text-tea underline" @click="cancelArmed">取消</button>
      </p>

      <section class="mt-6 rounded-2xl border border-ink/10 bg-surface p-4">
        <div class="flex items-center justify-between">
          <button type="button" class="rounded-full px-2 py-1 text-sm text-tea hover:text-ink" @click="prevMonth">‹</button>
          <p class="font-serif text-lg text-ink">{{ monthLabel }}</p>
          <button type="button" class="rounded-full px-2 py-1 text-sm text-tea hover:text-ink" @click="nextMonth">›</button>
        </div>

        <p v-if="scheduleLoading" class="mt-3 text-sm text-tea">載入中…</p>
        <p v-else-if="scheduleError" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ scheduleError }}</p>

        <template v-else>
          <div class="mt-3 grid grid-cols-7 gap-1 text-center text-[10px] text-tea">
            <span v-for="w in ['一', '二', '三', '四', '五', '六', '日']" :key="w">{{ w }}</span>
          </div>
          <div class="mt-1 grid grid-cols-7 gap-1">
            <button
              v-for="cell in calendarCells"
              :key="cell.iso"
              type="button"
              class="relative flex h-16 flex-col items-center justify-start rounded-lg border p-1 text-left"
              :class="[
                cell.inMonth ? 'border-ink/10' : 'border-transparent opacity-30',
                cell.iso === todayIso ? 'ring-1 ring-accent' : '',
                selectedScheduleIso === cell.iso ? 'bg-accent-tint' : 'bg-bg',
              ]"
              @click="onCellClick(cell.iso)"
            >
              <span
                v-if="scheduleByDate.get(cell.iso)?.volume_adjustment_pct"
                class="absolute right-0.5 top-0.5 h-1.5 w-1.5 rounded-full bg-alert"
                title="建議追量"
              />
              <span class="text-[10px] text-tea">{{ cell.date.getDate() }}</span>
              <span
                v-if="scheduleByDate.get(cell.iso)"
                class="mt-0.5 w-full truncate rounded px-1 py-0.5 text-[10px]"
                :class="statusColor(scheduleByDate.get(cell.iso)!.status)"
              >
                {{ scheduleByDate.get(cell.iso)!.day_label || scheduleByDate.get(cell.iso)!.program_name }}
              </span>
            </button>
          </div>
        </template>

        <div v-if="selectedSchedule" class="mt-4 rounded-lg border border-ink/10 p-3">
          <p class="text-sm text-ink">
            {{ selectedSchedule.scheduled_date }} · {{ selectedSchedule.day_label || selectedSchedule.program_name }}
            <span class="ml-1 text-xs text-tea">（{{ selectedSchedule.status }}）</span>
          </p>
          <p v-if="selectedSchedule.volume_adjustment_pct" class="mt-1 text-xs text-alert">
            前面進度落後，建議這天加量 {{ Math.round(selectedSchedule.volume_adjustment_pct * 100) }}%
          </p>
          <RouterLink
            v-if="needsActualLog"
            :to="`/exercise?schedule_id=${selectedSchedule.id}`"
            class="mt-2 inline-block rounded-full bg-accent px-3 py-1 text-xs font-semibold text-on-accent hover:bg-accent-bright"
          >
            補登實際紀錄
          </RouterLink>
          <div class="mt-2 flex flex-wrap gap-3">
            <button type="button" class="text-xs font-semibold text-accent hover:text-accent-bright" @click="startMoving(selectedSchedule.id)">
              移動
            </button>
            <button type="button" class="text-xs font-semibold text-tea hover:text-ink" @click="markSkipped(selectedSchedule.id)">
              標記已跳過
            </button>
            <button type="button" class="text-xs text-tea hover:text-alert" @click="removeSchedule(selectedSchedule.id)">
              移除排程
            </button>
          </div>
        </div>

        <p v-if="actionError" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ actionError }}</p>
      </section>

      <section class="mt-4 rounded-2xl border border-ink/10 bg-surface p-4">
        <button type="button" class="flex w-full items-center justify-between text-left" @click="showTargets = !showTargets">
          <span class="font-serif text-lg text-ink">每週目標</span>
          <span class="text-xs text-tea">{{ showTargets ? '收合' : '展開' }}</span>
        </button>

        <div v-if="showTargets" class="mt-3">
          <p v-if="targetsLoading" class="text-sm text-tea">載入中…</p>
          <p v-else-if="targetsError" class="rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ targetsError }}</p>

          <template v-else>
            <p class="text-xs text-tea">每個分類每週至少要練幾次，各自設定，只影響 {{ activeUser?.name }} 自己</p>
            <div class="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <label v-for="t in targets" :key="t.category" class="text-xs text-tea">
                {{ t.category }}
                <input
                  v-model.number="t.weekly_target_count"
                  type="number"
                  min="0"
                  class="mt-1 w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink"
                />
              </label>
            </div>
            <button
              type="button"
              class="mt-3 rounded-full bg-accent px-4 py-1.5 text-xs font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
              :disabled="savingTargets"
              @click="saveTargets"
            >
              {{ savingTargets ? '儲存中…' : targetsSaved ? '已儲存 ✓' : '儲存目標' }}
            </button>
          </template>
        </div>
      </section>

      <section class="mt-4 rounded-2xl border border-ink/10 bg-surface p-4">
        <p class="font-serif text-lg text-ink">本週達成度</p>

        <p v-if="progressLoading" class="mt-3 text-sm text-tea">載入中…</p>
        <p v-else-if="progressError" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ progressError }}</p>

        <ul v-else-if="progress" class="mt-3 divide-y divide-ink/10">
          <li v-for="c in progress.categories" :key="c.category" class="flex items-center justify-between py-2 text-sm">
            <span class="text-ink">{{ c.category }}</span>
            <span class="flex items-center gap-2 text-xs">
              <span :class="c.met ? 'text-accent' : 'text-tea'">{{ c.actual_count }} / {{ c.target_count }} 次{{ c.met ? ' ✓' : '' }}</span>
              <span v-if="c.this_week_volume !== undefined" :class="c.volume_met ? 'text-accent' : 'text-alert'">
                量 {{ c.this_week_volume }}（上週 {{ c.last_week_volume }}）{{ c.volume_met ? '✓' : '↓' }}
              </span>
            </span>
          </li>
        </ul>
      </section>
    </template>

    <TrainingProgramFormModal v-model="showForm" :user-id="activeUser?.id ?? null" @created="onCreated" />
  </div>
</template>

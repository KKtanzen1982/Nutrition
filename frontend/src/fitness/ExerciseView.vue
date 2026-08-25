<script setup lang="ts">
import { computed, reactive, ref, watchEffect } from 'vue'
import { useRoute } from 'vue-router'
import DateRangeButton from '../trends/DateRangeButton.vue'
import ExerciseItemAutocomplete from '../training/ExerciseItemAutocomplete.vue'
import TemplateFormModal from '../training/TemplateFormModal.vue'
import StepsEditModal from '../training/StepsEditModal.vue'
import { createDailyStepsRecord, createExerciseSession, fetchDailySteps, fetchExerciseSessions } from './exercise_api'
import { createWorkoutTemplate, fetchWorkoutTemplates, fetchWorkoutTemplate } from '../training/workout_template_api'
import { fetchTrainingScheduleEntry, linkActualSchedule } from '../training/training_schedule_api'
import { useHouseholdConfig } from '../shared/useHouseholdConfig'
import { daysAgo, startOfWeekMonday, toISODate, today } from '../shared/date_utils'
import type {
  DailyStepsRecord,
  ExerciseDetail,
  ExerciseItemLibraryEntry,
  ExerciseSession,
  TrainingScheduleEntry,
  WorkoutTemplate,
} from '../shared/types'

const route = useRoute()

const YOGA_STRETCH_TYPES = ['瑜珈', '拉伸']

const EXERCISE_TYPES = ['健身房', '走路', '瑜珈', '拉伸']
const HISTORY_FETCH_DAYS = 180

const { activeUser } = useHouseholdConfig()

const todayStr = toISODate(today())
const weekStartStr = toISODate(startOfWeekMonday(today()))
const historyRangeStartStr = toISODate(daysAgo(30))

const loading = ref(true)
const error = ref<string | null>(null)
const sessions = ref<ExerciseSession[]>([])
const steps = ref<DailyStepsRecord[]>([])

async function load(userId: number) {
  loading.value = true
  error.value = null
  try {
    const [sessionList, stepList] = await Promise.all([
      fetchExerciseSessions(userId, daysAgo(HISTORY_FETCH_DAYS), today()),
      fetchDailySteps(userId, daysAgo(HISTORY_FETCH_DAYS), today()),
    ])
    sessions.value = sessionList
    steps.value = stepList
  } catch (e) {
    error.value = e instanceof Error ? e.message : '讀取運動資料失敗'
  } finally {
    loading.value = false
  }
}

watchEffect(() => {
  if (activeUser.value) load(activeUser.value.id)
})

const weekSessions = computed(() => sessions.value.filter((s) => s.date >= weekStartStr))
const weekSteps = computed(() => steps.value.filter((s) => s.date >= weekStartStr))
const totalSessions = computed(() => weekSessions.value.length)
const totalMinutes = computed(() => weekSessions.value.reduce((sum, s) => sum + (s.duration_min ?? 0), 0))
const totalSteps = computed(() => weekSteps.value.reduce((sum, s) => sum + s.step_count, 0))
function formatDetail(d: ExerciseDetail): string {
  if (d.sets !== null && d.reps) {
    return `${d.exercise_name} ${d.sets}x${d.reps}${d.weight_kg ? ' ' + d.weight_kg + 'kg' : ''}`
  }
  if (d.duration_min) {
    return `${d.exercise_name} ${d.duration_min}分鐘`
  }
  return d.exercise_name
}

const byType = computed(() => {
  const counts = new Map<string, number>()
  for (const s of weekSessions.value) counts.set(s.exercise_type, (counts.get(s.exercise_type) ?? 0) + 1)
  return [...counts.entries()]
})

interface DetailRow {
  exercise_name: string
  sets: number | null
  reps: string
  weight_kg: number | null
  duration_min: number | null
  exercise_item_id: number | null
  yoga_stretch_item_id: number | null
}

const sessionForm = reactive({
  date: todayStr,
  exercise_type: EXERCISE_TYPES[0],
  duration_min: null as number | null,
  notes: '',
})
const detailRows = ref<DetailRow[]>([])
const savingSession = ref(false)
const sessionError = ref<string | null>(null)

const showsGymDetails = computed(() => sessionForm.exercise_type === '健身房')
const showsYogaStretchDetails = computed(() => YOGA_STRETCH_TYPES.includes(sessionForm.exercise_type))

function emptyDetailRow(): DetailRow {
  return { exercise_name: '', sets: null, reps: '', weight_kg: null, duration_min: null, exercise_item_id: null, yoga_stretch_item_id: null }
}
function addDetailRow() {
  detailRows.value.push(emptyDetailRow())
}
function removeDetailRow(index: number) {
  detailRows.value.splice(index, 1)
}

function onSelectLibraryItem(row: DetailRow, item: ExerciseItemLibraryEntry) {
  if ('category' in item) {
    row.exercise_item_id = item.id
    row.yoga_stretch_item_id = null
    row.sets = item.default_sets
    row.reps = item.default_reps ?? ''
  } else {
    row.yoga_stretch_item_id = item.id
    row.exercise_item_id = null
    row.duration_min = item.duration_min
  }
}
function onClearLibraryItem(row: DetailRow) {
  row.exercise_item_id = null
  row.yoga_stretch_item_id = null
}

// ---- 訓練項目範本：快速套用 / 另存為新範本 ----

const templates = ref<WorkoutTemplate[]>([])
const templatesLoading = ref(false)
const selectedTemplateId = ref<number | ''>('')

async function loadTemplates(userId: number) {
  templatesLoading.value = true
  try {
    templates.value = await fetchWorkoutTemplates(userId)
  } catch {
    // 範本清單讀取失敗不影響主要記錄流程，安靜略過
  } finally {
    templatesLoading.value = false
  }
}

watchEffect(() => {
  if (activeUser.value) loadTemplates(activeUser.value.id)
})

const showTemplateDetail = ref(false)

function onTemplateSaved(template: WorkoutTemplate) {
  const idx = templates.value.findIndex((t) => t.id === template.id)
  if (idx === -1) templates.value = [...templates.value, template]
  else templates.value = templates.value.map((t) => (t.id === template.id ? template : t))
}

function onTemplateDeleted(templateId: number) {
  templates.value = templates.value.filter((t) => t.id !== templateId)
  if (selectedTemplateId.value === templateId) selectedTemplateId.value = ''
}

function applyTemplateContent(template: WorkoutTemplate) {
  sessionForm.exercise_type = template.exercise_type
  if (template.duration_min !== null) sessionForm.duration_min = template.duration_min
  detailRows.value = template.details
    .slice()
    .sort((a, b) => a.order - b.order)
    .map((d) => ({
      exercise_name: d.exercise_name,
      sets: d.sets,
      reps: d.reps ?? '',
      weight_kg: d.weight_kg,
      duration_min: d.duration_min ?? null,
      exercise_item_id: d.exercise_item_id ?? null,
      yoga_stretch_item_id: d.yoga_stretch_item_id ?? null,
    }))
}

function applyTemplate() {
  const template = templates.value.find((t) => t.id === selectedTemplateId.value)
  if (!template) return
  applyTemplateContent(template)
}

// ---- 從訓練計畫月曆深連結補登實際紀錄（?schedule_id=） ----

const scheduleId = computed(() => {
  const raw = route.query.schedule_id
  const n = Number(Array.isArray(raw) ? raw[0] : raw)
  return Number.isFinite(n) && n > 0 ? n : null
})
const linkedSchedule = ref<TrainingScheduleEntry | null>(null)

async function prefillFromSchedule(id: number) {
  try {
    const schedule = await fetchTrainingScheduleEntry(id)
    const template = await fetchWorkoutTemplate(schedule.workout_template_id)
    linkedSchedule.value = schedule
    sessionForm.date = schedule.scheduled_date
    applyTemplateContent(template)
  } catch {
    // 深連結預填失敗不影響一般新增流程，安靜略過
  }
}

watchEffect(() => {
  if (scheduleId.value !== null) prefillFromSchedule(scheduleId.value)
})

function isValidDetailRow(r: DetailRow): boolean {
  if (!r.exercise_name) return false
  if (showsGymDetails.value) return r.sets !== null && !!r.reps
  if (showsYogaStretchDetails.value) return r.duration_min !== null
  return false
}

function toDetailPayload(r: DetailRow) {
  return showsGymDetails.value
    ? { exercise_name: r.exercise_name, sets: r.sets, reps: r.reps, weight_kg: r.weight_kg, exercise_item_id: r.exercise_item_id }
    : { exercise_name: r.exercise_name, duration_min: r.duration_min, yoga_stretch_item_id: r.yoga_stretch_item_id }
}

const savingTemplate = ref(false)
const templateSaveError = ref<string | null>(null)
const showSaveTemplateForm = ref(false)
const newTemplateName = ref('')

async function saveAsTemplate() {
  if (!activeUser.value || !newTemplateName.value.trim()) return
  const validRows = detailRows.value.filter(isValidDetailRow)
  if (validRows.length === 0) {
    templateSaveError.value = '請先填寫至少一項訓練項目明細'
    return
  }
  savingTemplate.value = true
  templateSaveError.value = null
  try {
    const created = await createWorkoutTemplate({
      user_id: activeUser.value.id,
      template_name: newTemplateName.value.trim(),
      exercise_type: sessionForm.exercise_type,
      duration_min: sessionForm.duration_min,
      details: validRows.map(toDetailPayload),
    })
    templates.value = [...templates.value, created]
    newTemplateName.value = ''
    showSaveTemplateForm.value = false
  } catch (e) {
    templateSaveError.value = e instanceof Error ? e.message : '另存範本失敗，請稍後再試'
  } finally {
    savingTemplate.value = false
  }
}

async function submitSession() {
  if (!activeUser.value || sessionForm.duration_min === null) return
  savingSession.value = true
  sessionError.value = null
  try {
    const details =
      showsGymDetails.value || showsYogaStretchDetails.value
        ? detailRows.value.filter(isValidDetailRow).map(toDetailPayload)
        : []
    const created = await createExerciseSession({
      user_id: activeUser.value.id,
      date: sessionForm.date,
      exercise_type: sessionForm.exercise_type,
      duration_min: sessionForm.duration_min,
      notes: sessionForm.notes || null,
      details: details.length ? details : undefined,
    })
    if (linkedSchedule.value) {
      try {
        await linkActualSchedule(linkedSchedule.value.id, created.id)
      } catch {
        // 排程綁定失敗不影響這筆紀錄本身已經成功建立，安靜略過
      }
      linkedSchedule.value = null
    }
    sessionForm.duration_min = null
    sessionForm.notes = ''
    detailRows.value = []
    selectedTemplateId.value = ''
    await load(activeUser.value.id)
  } catch (e) {
    sessionError.value = e instanceof Error ? e.message : '儲存失敗，請稍後再試'
  } finally {
    savingSession.value = false
  }
}

const stepsForm = reactive({ date: todayStr, step_count: null as number | null })
const savingSteps = ref(false)
const stepsError = ref<string | null>(null)
const showStepsEdit = ref(false)
const stepsEditRecord = ref<DailyStepsRecord | null>(null)

async function submitSteps() {
  if (!activeUser.value || stepsForm.step_count === null) return
  const existing = steps.value.find((s) => s.date === stepsForm.date)
  if (existing) {
    stepsEditRecord.value = existing
    showStepsEdit.value = true
    return
  }
  savingSteps.value = true
  stepsError.value = null
  try {
    await createDailyStepsRecord({ user_id: activeUser.value.id, date: stepsForm.date, step_count: stepsForm.step_count })
    stepsForm.step_count = null
    await load(activeUser.value.id)
  } catch (e) {
    stepsError.value = e instanceof Error ? e.message : '儲存失敗，請稍後再試'
  } finally {
    savingSteps.value = false
  }
}

function onStepsSaved() {
  stepsForm.step_count = null
  if (activeUser.value) load(activeUser.value.id)
}

// ---- 歷史紀錄：運動與步數分開，各自可設定日期區間（合併為單一日曆鈕），運動另有文字搜尋 ----

const sessionHistoryFrom = ref(historyRangeStartStr)
const sessionHistoryTo = ref(todayStr)
const sessionHistoryQuery = ref('')

const stepsHistoryFrom = ref(historyRangeStartStr)
const stepsHistoryTo = ref(todayStr)

const filteredSessionHistory = computed(() => {
  const query = sessionHistoryQuery.value.trim()
  return sessions.value
    .filter((s) => s.date >= sessionHistoryFrom.value && s.date <= sessionHistoryTo.value)
    .filter((s) => {
      if (!query) return true
      const haystack = [s.exercise_type, s.notes ?? '', ...(s.details ?? []).map((d) => d.exercise_name)].join(' ')
      return haystack.toLowerCase().includes(query.toLowerCase())
    })
    .sort((a, b) => b.date.localeCompare(a.date))
})

const filteredStepsHistory = computed(() =>
  steps.value
    .filter((s) => s.date >= stepsHistoryFrom.value && s.date <= stepsHistoryTo.value)
    .sort((a, b) => b.date.localeCompare(a.date)),
)
</script>

<template>
  <div class="mx-auto max-w-2xl px-4 py-8">
    <div v-if="!activeUser" class="rounded-2xl border border-dashed border-ink/20 p-6 text-center text-tea">
      請先在上方完成使用者設定
    </div>

    <template v-else>
      <div class="grid grid-cols-3 gap-3 text-center">
        <div class="rounded-2xl border border-ink/10 bg-surface p-4">
          <p class="font-serif text-3xl text-ink">{{ totalSessions }}</p>
          <p class="text-xs text-tea">本週次數</p>
        </div>
        <div class="rounded-2xl border border-ink/10 bg-surface p-4">
          <p class="font-serif text-3xl text-ink">{{ totalMinutes }}</p>
          <p class="text-xs text-tea">本週分鐘</p>
        </div>
        <div class="rounded-2xl border border-ink/10 bg-surface p-4">
          <p class="font-serif text-3xl text-ink">{{ totalSteps.toLocaleString() }}</p>
          <p class="text-xs text-tea">本週步數</p>
        </div>
      </div>
      <div v-if="byType.length" class="mt-3 flex flex-wrap gap-1.5">
        <span v-for="[type, count] in byType" :key="type" class="rounded-full bg-accent-tint px-2.5 py-1 text-xs text-ink">
          {{ type }} × {{ count }}
        </span>
      </div>

      <p class="mt-6 text-xs text-tea">
        小提醒：目前還不支援編輯或刪除紀錄，如果打錯了，再新增一筆正確的就好。
      </p>

      <p v-if="linkedSchedule" class="mt-3 rounded-lg bg-accent-tint px-3 py-2 text-sm text-ink">
        正在補登「{{ linkedSchedule.program_name }} · {{ linkedSchedule.day_label }}」的實際紀錄，送出後會自動跟月曆上的排程綁在一起
      </p>

      <section class="mt-3 rounded-2xl border border-ink/10 bg-surface p-6">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1.5">
            <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-ink" aria-hidden="true" />
            <h1 class="border-b-[1.5px] border-accent pb-1 text-base font-semibold text-ink">
              新增運動紀錄
            </h1>
          </div>
          <input v-model="sessionForm.date" type="date" :max="todayStr" class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
        </div>

        <div class="mt-4">
          <label class="mb-1 block text-xs text-tea">類型</label>
          <select v-model="sessionForm.exercise_type" class="w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink">
            <option v-for="t in EXERCISE_TYPES" :key="t" :value="t">{{ t }}</option>
          </select>
        </div>

        <div class="mt-3">
          <label class="mb-1 block text-xs text-tea">時長（分鐘）</label>
          <input
            v-model.number="sessionForm.duration_min"
            type="number"
            min="1"
            class="w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-2xl font-semibold text-ink"
          />
        </div>

        <div v-if="showsGymDetails || showsYogaStretchDetails" class="mt-4">
          <div v-if="templates.length" class="mb-3 flex items-center gap-2">
            <label class="shrink-0 text-xs text-tea">從範本快速填寫</label>
            <select
              v-model="selectedTemplateId"
              class="min-w-0 flex-1 rounded-lg border border-ink/15 bg-bg px-2 py-1.5 text-sm text-ink"
              @change="applyTemplate"
            >
              <option value="">選擇範本…</option>
              <option v-for="t in templates" :key="t.id" :value="t.id">{{ t.template_name }}</option>
            </select>
            <button
              v-if="selectedTemplateId"
              type="button"
              class="shrink-0 text-xs font-semibold text-tea hover:text-ink"
              @click="showTemplateDetail = true"
            >
              檢視/編輯
            </button>
          </div>

          <div class="flex items-center justify-between">
            <p class="text-xs text-tea">訓練項目明細（選填）</p>
            <div class="flex items-center gap-3">
              <button
                type="button"
                class="text-xs font-semibold text-tea hover:text-ink"
                @click="showSaveTemplateForm = !showSaveTemplateForm"
              >
                另存為範本
              </button>
              <button type="button" class="text-xs font-semibold text-accent hover:text-accent-bright" @click="addDetailRow">
                + 新增項目
              </button>
            </div>
          </div>

          <div v-if="showSaveTemplateForm" class="mt-2 flex items-center gap-2">
            <input
              v-model="newTemplateName"
              type="text"
              placeholder="範本名稱，例如「胸推日」"
              class="min-w-0 flex-1 rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink"
            />
            <button
              type="button"
              class="shrink-0 rounded-full bg-accent px-3 py-1 text-xs font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
              :disabled="savingTemplate || !newTemplateName.trim()"
              @click="saveAsTemplate"
            >
              {{ savingTemplate ? '儲存中…' : '儲存範本' }}
            </button>
          </div>
          <p v-if="templateSaveError" class="mt-2 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ templateSaveError }}</p>

          <template v-if="showsGymDetails">
            <div v-for="(row, i) in detailRows" :key="i" class="mt-2 grid grid-cols-[1fr_60px_60px_70px_auto] items-center gap-2">
              <ExerciseItemAutocomplete
                v-model="row.exercise_name"
                item-type="gym"
                :user-id="activeUser?.id ?? null"
                placeholder="動作名稱"
                @select="(item) => onSelectLibraryItem(row, item)"
                @clear="() => onClearLibraryItem(row)"
              />
              <input v-model.number="row.sets" type="number" min="1" placeholder="組" class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
              <input v-model="row.reps" type="text" placeholder="次數" class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
              <input v-model.number="row.weight_kg" type="number" step="0.5" placeholder="kg" class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
              <button type="button" class="text-xs text-tea hover:text-alert" @click="removeDetailRow(i)">刪除</button>
            </div>
          </template>
          <template v-else>
            <div v-for="(row, i) in detailRows" :key="i" class="mt-2 grid grid-cols-[1fr_80px_auto] items-center gap-2">
              <ExerciseItemAutocomplete
                v-model="row.exercise_name"
                item-type="yoga_stretch"
                :yoga-type="sessionForm.exercise_type"
                :user-id="activeUser?.id ?? null"
                placeholder="動作名稱"
                @select="(item) => onSelectLibraryItem(row, item)"
                @clear="() => onClearLibraryItem(row)"
              />
              <input v-model.number="row.duration_min" type="number" min="1" placeholder="時長(分)" class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
              <button type="button" class="text-xs text-tea hover:text-alert" @click="removeDetailRow(i)">刪除</button>
            </div>
          </template>
        </div>

        <p v-if="sessionError" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ sessionError }}</p>

        <button
          type="button"
          class="mt-4 w-full rounded-full bg-accent py-2.5 text-sm font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
          :disabled="savingSession || sessionForm.duration_min === null"
          @click="submitSession"
        >
          {{ savingSession ? '儲存中…' : '新增紀錄' }}
        </button>
      </section>

      <section class="mt-4 rounded-2xl border border-ink/10 bg-surface p-6">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1.5">
            <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-ink" aria-hidden="true" />
            <h2 class="border-b-[1.5px] border-accent pb-1 text-[11.5px] font-semibold uppercase tracking-wide text-muted">
              新增步數
            </h2>
          </div>
          <input v-model="stepsForm.date" type="date" :max="todayStr" class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
        </div>
        <div class="mt-4">
          <label class="mb-1 block text-xs text-tea">步數</label>
          <input
            v-model.number="stepsForm.step_count"
            type="number"
            min="0"
            class="w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-2xl font-semibold text-ink"
          />
        </div>
        <p v-if="stepsError" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ stepsError }}</p>
        <button
          type="button"
          class="mt-4 w-full rounded-full bg-accent py-2.5 text-sm font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
          :disabled="savingSteps || stepsForm.step_count === null"
          @click="submitSteps"
        >
          {{ savingSteps ? '儲存中…' : '新增步數' }}
        </button>
      </section>

      <p v-if="loading" class="mt-8 text-sm text-tea">載入中…</p>
      <p v-else-if="error" class="mt-8 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ error }}</p>

      <template v-else>
        <section class="mt-8">
          <h2 class="font-serif text-xl text-ink">運動歷史</h2>
          <div class="mt-3 flex flex-wrap items-center gap-2">
            <DateRangeButton v-model:from="sessionHistoryFrom" v-model:to="sessionHistoryTo" :max="todayStr" />
            <input
              v-model="sessionHistoryQuery"
              type="text"
              placeholder="搜尋類型或動作名稱…"
              class="ml-auto min-w-0 flex-1 rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink sm:flex-none sm:w-48"
            />
          </div>
          <p v-if="filteredSessionHistory.length === 0" class="mt-3 text-sm text-tea">尚無符合條件的紀錄</p>
          <ul v-else class="mt-3 divide-y divide-ink/10">
            <li v-for="s in filteredSessionHistory" :key="s.id" class="py-3">
              <div class="flex items-center justify-between">
                <p class="text-sm text-ink">{{ s.date }} · {{ s.exercise_type }}</p>
                <span class="font-serif text-lg text-ink">{{ s.duration_min }}<small class="text-sm text-tea">分鐘</small></span>
              </div>
              <p v-if="s.details?.length" class="mt-1 text-xs text-tea">
                {{ s.details.map(formatDetail).join('、') }}
              </p>
            </li>
          </ul>
        </section>

        <section class="mt-8">
          <h2 class="font-serif text-xl text-ink">步數歷史</h2>
          <div class="mt-3">
            <DateRangeButton v-model:from="stepsHistoryFrom" v-model:to="stepsHistoryTo" :max="todayStr" />
          </div>
          <p v-if="filteredStepsHistory.length === 0" class="mt-3 text-sm text-tea">尚無符合條件的紀錄</p>
          <ul v-else class="mt-3 divide-y divide-ink/10">
            <li v-for="s in filteredStepsHistory" :key="s.id" class="flex items-center justify-between py-3">
              <p class="text-sm text-ink">{{ s.date }}</p>
              <span class="font-serif text-lg text-ink">{{ s.step_count.toLocaleString() }}</span>
            </li>
          </ul>
        </section>
      </template>
    </template>

    <TemplateFormModal
      v-model="showTemplateDetail"
      :template-id="selectedTemplateId || null"
      :user-id="activeUser?.id ?? null"
      @saved="onTemplateSaved"
      @deleted="onTemplateDeleted"
    />
    <StepsEditModal v-model="showStepsEdit" :record="stepsEditRecord" @saved="onStepsSaved" />
  </div>
</template>

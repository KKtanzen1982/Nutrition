<script setup lang="ts">
import { reactive, ref, watchEffect } from 'vue'
import FactsRow from '../shared/FactsRow.vue'
import { fetchUser, fetchUserGoalHistory, updateUser } from './users_api'
import { fetchDietaryPreferences, updateDietaryPreferences } from './dietary_preference_api'
import { useHouseholdConfig } from '../shared/useHouseholdConfig'
import type { DietaryPreference, GoalHistoryEntry, UpdateDietaryPreferencePayload, UpdateUserPayload, UserProfile } from '../shared/types'

const GENDERS = ['男', '女', '其他']
const GOALS = ['減脂', '增肌', '維持']
const ACTIVITY_LEVELS = ['久坐', '輕度', '中度', '高度']

const GOAL_TYPE_LABELS: Record<string, string> = {
  weight: '體重',
  body_fat: '體脂率',
  waist_circumference: '腰圍',
}

const GOAL_TYPE_UNITS: Record<string, string> = {
  weight: 'kg',
  body_fat: '%',
  waist_circumference: 'cm',
}

const { activeUser, config, setUsers } = useHouseholdConfig()

const loading = ref(true)
const error = ref<string | null>(null)
const profile = ref<UserProfile | null>(null)

const historyLoading = ref(true)
const historyError = ref<string | null>(null)
const history = ref<GoalHistoryEntry[]>([])

const editing = ref(false)
const saving = ref(false)
const saveError = ref<string | null>(null)
const form = reactive<UpdateUserPayload>({})

async function load(userId: number) {
  loading.value = true
  error.value = null
  try {
    profile.value = await fetchUser(userId)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '讀取個人資料失敗'
  } finally {
    loading.value = false
  }

  historyLoading.value = true
  historyError.value = null
  try {
    const entries = await fetchUserGoalHistory(userId)
    history.value = [...entries].sort((a, b) => b.set_date.localeCompare(a.set_date))
  } catch (e) {
    historyError.value = e instanceof Error ? e.message : '讀取目標歷史失敗'
  } finally {
    historyLoading.value = false
  }
}

const dietaryPref = ref<DietaryPreference | null>(null)
const dietaryLoading = ref(true)
const dietaryEditing = ref(false)
const dietarySaving = ref(false)
const dietaryError = ref<string | null>(null)
const dietaryForm = reactive<UpdateDietaryPreferencePayload>({})

async function loadDietaryPreferences(userId: number) {
  dietaryLoading.value = true
  try {
    dietaryPref.value = await fetchDietaryPreferences(userId)
  } catch (e) {
    dietaryError.value = e instanceof Error ? e.message : '讀取飲食偏好失敗'
  } finally {
    dietaryLoading.value = false
  }
}

function startDietaryEditing() {
  Object.assign(dietaryForm, {
    allergies: dietaryPref.value?.allergies ?? '',
    restrictions: dietaryPref.value?.restrictions ?? '',
    preferences: dietaryPref.value?.preferences ?? '',
  })
  dietaryError.value = null
  dietaryEditing.value = true
}

async function saveDietaryPreferences() {
  if (!activeUser.value) return
  dietarySaving.value = true
  dietaryError.value = null
  try {
    dietaryPref.value = await updateDietaryPreferences(activeUser.value.id, dietaryForm)
    dietaryEditing.value = false
  } catch (e) {
    dietaryError.value = e instanceof Error ? e.message : '儲存失敗，請稍後再試'
  } finally {
    dietarySaving.value = false
  }
}

watchEffect(() => {
  if (activeUser.value) {
    load(activeUser.value.id)
    loadDietaryPreferences(activeUser.value.id)
  }
})

function startEditing() {
  if (!profile.value) return
  Object.assign(form, {
    name: profile.value.name,
    gender: profile.value.gender,
    age: profile.value.age,
    height_cm: profile.value.height_cm,
    primary_goal: profile.value.primary_goal,
    activity_level: profile.value.activity_level,
    notes: profile.value.notes ?? '',
    last_menstrual_date: profile.value.last_menstrual_date ?? '',
    menstrual_cycle_length_days: profile.value.menstrual_cycle_length_days ?? 28,
    menstrual_cycle_irregular: profile.value.menstrual_cycle_irregular ?? false,
  })
  saveError.value = null
  editing.value = true
}

function cancelEditing() {
  editing.value = false
  saveError.value = null
}

async function save() {
  if (!activeUser.value) return
  saving.value = true
  saveError.value = null
  try {
    // 後端的日期欄位只接受合法日期或 null，空字串會被 Pydantic 拒絕
    const payload = { ...form, last_menstrual_date: form.last_menstrual_date || null }
    profile.value = await updateUser(activeUser.value.id, payload)
    if (profile.value.name !== activeUser.value.name) {
      setUsers(config.value.users.map((u) => (u.id === profile.value!.id ? { ...u, name: profile.value!.name } : u)))
    }
    editing.value = false
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : '儲存失敗，請稍後再試'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-2xl px-4 py-8">
    <div v-if="!activeUser" class="rounded-2xl border border-dashed border-ink/20 p-6 text-center text-tea">
      請先在上方完成使用者設定
    </div>

    <template v-else>
      <section class="rounded-2xl border border-ink/10 bg-surface p-6">
        <header class="flex items-end justify-between">
          <div>
            <p class="text-[11.5px] font-semibold uppercase tracking-wide text-muted">個人資料</p>
            <h1 class="font-serif text-3xl text-ink">{{ profile?.name ?? activeUser.name }}</h1>
          </div>
          <button
            v-if="!editing"
            class="text-sm font-semibold text-tea underline decoration-1 underline-offset-4 hover:text-ink"
            @click="startEditing"
          >
            編輯
          </button>
          <div v-else class="flex gap-3">
            <button class="text-sm font-semibold text-tea hover:text-ink" :disabled="saving" @click="cancelEditing">
              取消
            </button>
            <button
              class="rounded-full bg-accent px-3 py-1 text-sm font-semibold text-on-accent hover:bg-accent-bright"
              :disabled="saving"
              @click="save"
            >
              {{ saving ? '儲存中…' : '儲存' }}
            </button>
          </div>
        </header>

        <p v-if="loading" class="py-8 text-center text-sm text-tea">載入中…</p>
        <p v-else-if="error" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ error }}</p>

        <dl v-else-if="profile" class="mt-2">
          <p v-if="saveError" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ saveError }}</p>

          <FactsRow label="姓名" :editing="editing">
            {{ profile.name }}
            <template #input>
              <input
                v-model="form.name"
                type="text"
                class="w-full rounded border border-ink/15 bg-bg px-2 py-1 text-right text-ink"
              />
            </template>
          </FactsRow>

          <FactsRow label="性別" :editing="editing">
            {{ profile.gender }}
            <template #input>
              <select v-model="form.gender" class="w-full rounded border border-ink/15 bg-bg px-2 py-1 text-right text-ink">
                <option v-for="g in GENDERS" :key="g" :value="g">{{ g }}</option>
              </select>
            </template>
          </FactsRow>

          <FactsRow label="年齡" :editing="editing">
            {{ profile.age }} 歲
            <template #input>
              <input
                v-model.number="form.age"
                type="number"
                min="1"
                max="150"
                class="w-24 rounded border border-ink/15 bg-bg px-2 py-1 text-right text-ink"
              />
            </template>
          </FactsRow>

          <FactsRow label="身高" :editing="editing">
            {{ profile.height_cm }} cm
            <template #input>
              <input
                v-model.number="form.height_cm"
                type="number"
                min="100"
                max="250"
                class="w-24 rounded border border-ink/15 bg-bg px-2 py-1 text-right text-ink"
              />
            </template>
          </FactsRow>

          <FactsRow label="目標" :editing="editing">
            {{ profile.primary_goal }}
            <template #input>
              <select v-model="form.primary_goal" class="w-full rounded border border-ink/15 bg-bg px-2 py-1 text-right text-ink">
                <option v-for="g in GOALS" :key="g" :value="g">{{ g }}</option>
              </select>
            </template>
          </FactsRow>

          <FactsRow label="活動量" :editing="editing">
            {{ profile.activity_level }}
            <template #input>
              <select
                v-model="form.activity_level"
                class="w-full rounded border border-ink/15 bg-bg px-2 py-1 text-right text-ink"
              >
                <option v-for="a in ACTIVITY_LEVELS" :key="a" :value="a">{{ a }}</option>
              </select>
            </template>
          </FactsRow>

          <FactsRow label="備註" :editing="editing">
            {{ profile.notes || '—' }}
            <template #input>
              <textarea
                v-model="form.notes"
                rows="2"
                class="w-full rounded border border-ink/15 bg-bg px-2 py-1 text-right text-ink"
              />
            </template>
          </FactsRow>

          <template v-if="profile.gender === '女'">
            <FactsRow label="最後經期日期" :editing="editing">
              {{ profile.last_menstrual_date || '—' }}
              <template #input>
                <input
                  v-model="form.last_menstrual_date"
                  type="date"
                  class="w-full rounded border border-ink/15 bg-bg px-2 py-1 text-right text-ink"
                />
              </template>
            </FactsRow>
            <FactsRow label="週期天數" :editing="editing">
              {{ profile.menstrual_cycle_length_days || '—' }}
              <template #input>
                <input
                  v-model.number="form.menstrual_cycle_length_days"
                  type="number"
                  min="15"
                  max="60"
                  class="w-24 rounded border border-ink/15 bg-bg px-2 py-1 text-right text-ink"
                />
              </template>
            </FactsRow>
            <FactsRow label="週期不規律" :editing="editing">
              {{ profile.menstrual_cycle_irregular ? '是' : '否' }}
              <template #input>
                <input v-model="form.menstrual_cycle_irregular" type="checkbox" class="align-middle" />
              </template>
            </FactsRow>
          </template>
        </dl>
      </section>

      <section class="mt-6 rounded-2xl border border-ink/10 bg-surface p-4">
        <header class="flex items-center justify-between">
          <h3 class="text-[11.5px] font-semibold uppercase tracking-wide text-muted">過敏 / 飲食限制 / 偏好</h3>
          <button
            v-if="!dietaryEditing"
            class="text-xs font-semibold text-tea underline decoration-1 underline-offset-4 hover:text-ink"
            @click="startDietaryEditing"
          >
            編輯
          </button>
          <div v-else class="flex gap-2">
            <button class="text-xs font-semibold text-tea hover:text-ink" :disabled="dietarySaving" @click="dietaryEditing = false">取消</button>
            <button
              class="rounded-full bg-accent px-3 py-1 text-xs font-semibold text-on-accent hover:bg-accent-bright"
              :disabled="dietarySaving"
              @click="saveDietaryPreferences"
            >
              {{ dietarySaving ? '儲存中…' : '儲存' }}
            </button>
          </div>
        </header>
        <p v-if="dietaryLoading" class="mt-2 text-sm text-tea">載入中…</p>
        <p v-if="dietaryError" class="mt-2 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ dietaryError }}</p>
        <dl v-if="!dietaryLoading" class="mt-2">
          <FactsRow label="過敏原" :editing="dietaryEditing">
            {{ dietaryPref?.allergies || '—' }}
            <template #input>
              <input v-model="dietaryForm.allergies" type="text" placeholder="逗號分隔，例：堅果, 海鮮" class="w-full rounded border border-ink/15 bg-bg px-2 py-1 text-right text-ink" />
            </template>
          </FactsRow>
          <FactsRow label="飲食限制" :editing="dietaryEditing">
            {{ dietaryPref?.restrictions || '—' }}
            <template #input>
              <input v-model="dietaryForm.restrictions" type="text" placeholder="例：素食" class="w-full rounded border border-ink/15 bg-bg px-2 py-1 text-right text-ink" />
            </template>
          </FactsRow>
          <FactsRow label="偏好" :editing="dietaryEditing">
            {{ dietaryPref?.preferences || '—' }}
            <template #input>
              <input v-model="dietaryForm.preferences" type="text" placeholder="例：喜歡清淡" class="w-full rounded border border-ink/15 bg-bg px-2 py-1 text-right text-ink" />
            </template>
          </FactsRow>
        </dl>
      </section>

      <section class="mt-8">
        <h2 class="font-serif text-xl text-ink">目標歷史</h2>
        <p v-if="historyLoading" class="mt-3 text-sm text-tea">載入中…</p>
        <p v-else-if="historyError" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ historyError }}</p>
        <p v-else-if="history.length === 0" class="mt-3 text-sm text-tea">尚無目標變更紀錄</p>
        <ol v-else class="mt-3 space-y-3 border-l-2 border-accent pl-4">
          <li v-for="(entry, i) in history" :key="i">
            <p class="text-xs font-semibold uppercase tracking-wide text-muted">{{ entry.set_date }}</p>
            <p class="text-sm text-ink">
              {{ GOAL_TYPE_LABELS[entry.goal_type] ?? entry.goal_type }}
              <span v-if="entry.previous_value !== null" class="text-tea">
                {{ entry.previous_value }}{{ GOAL_TYPE_UNITS[entry.goal_type] ?? '' }} →
              </span>
              <span class="font-serif">{{ entry.target_value }}{{ GOAL_TYPE_UNITS[entry.goal_type] ?? '' }}</span>
              <span v-if="entry.achieved" class="ml-2 text-xs font-semibold text-accent">
                已達成 {{ entry.achievement_date }}
              </span>
            </p>
          </li>
        </ol>
      </section>
    </template>
  </div>
</template>

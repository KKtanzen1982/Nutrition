<script setup lang="ts">
import { ref } from 'vue'
import { fetchUser } from '../users/users_api'
import { useHouseholdConfig } from './useHouseholdConfig'

const { config, isConfigured, setUsers, setActiveUser, userIcon } = useHouseholdConfig()

const formUserAId = ref('')
const formUserBId = ref('')
const submitting = ref(false)
const submitError = ref<string | null>(null)

async function submitSetup() {
  const ids = [formUserAId.value, formUserBId.value].filter((v) => v).map(Number)
  if (ids.length === 0) return
  submitting.value = true
  submitError.value = null
  try {
    const profiles = await Promise.all(ids.map((id) => fetchUser(id)))
    setUsers(profiles.map((p) => ({ id: p.id, name: p.name })))
  } catch (e) {
    submitError.value = e instanceof Error ? e.message : '找不到對應的使用者，請確認 ID 是否正確'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div v-if="!isConfigured" class="rounded-2xl border border-dashed border-ink/20 bg-surface p-4">
    <p class="mb-3 text-sm text-tea">
      首次使用，請輸入兩位使用者的 ID（對應後端 <code>/users/:id</code>）。顯示名稱會直接從個人資料抓取，之後改個人資料的姓名也會自動同步。
    </p>
    <div class="grid grid-cols-2 gap-3">
      <input
        v-model="formUserAId"
        type="number"
        placeholder="使用者 A ID"
        class="rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
      />
      <input
        v-model="formUserBId"
        type="number"
        placeholder="使用者 B ID"
        class="rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
      />
    </div>
    <p v-if="submitError" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ submitError }}</p>
    <button
      class="mt-3 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-on-accent hover:bg-accent-bright disabled:opacity-50"
      :disabled="submitting"
      @click="submitSetup"
    >
      {{ submitting ? '確認中…' : '儲存設定' }}
    </button>
  </div>

  <div v-else class="flex items-center gap-2">
    <button
      v-for="user in config.users"
      :key="user.id"
      class="rounded-full px-4 py-1.5 text-sm font-medium transition"
      :class="
        user.id === config.activeUserId
          ? 'bg-accent text-on-accent'
          : 'bg-accent-tint text-tea hover:text-ink'
      "
      @click="setActiveUser(user.id)"
    >
      <span aria-hidden="true">{{ userIcon(user.id) }}</span> {{ user.name }}
    </button>
  </div>
</template>

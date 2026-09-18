<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getBaseUrl } from './http'
import { getAccessKey, setAccessKey } from './accessKey'

const checking = ref(true)
const unlocked = ref(false)
const password = ref('')
const submitting = ref(false)
const errorMsg = ref<string | null>(null)

async function tryKey(key: string | null): Promise<boolean> {
  try {
    const res = await fetch(`${getBaseUrl()}/users`, {
      headers: key ? { 'X-App-Key': key } : {},
    })
    return res.ok
  } catch {
    return false
  }
}

onMounted(async () => {
  // 先用存好的密碼（或沒設密碼也試試看，後端沒設 APP_ACCESS_KEY 時本來就會直接放行）試一次，
  // 過了就不用讓使用者每次重整都要重新輸入
  unlocked.value = await tryKey(getAccessKey())
  checking.value = false
})

async function submit() {
  if (!password.value || submitting.value) return
  submitting.value = true
  errorMsg.value = null
  const ok = await tryKey(password.value)
  if (ok) {
    setAccessKey(password.value)
    unlocked.value = true
  } else {
    errorMsg.value = '密碼錯誤，請再確認一次'
  }
  submitting.value = false
}
</script>

<template>
  <div v-if="checking" class="flex min-h-screen items-center justify-center bg-bg text-sm text-tea">載入中…</div>
  <div v-else-if="!unlocked" class="flex min-h-screen items-center justify-center bg-bg px-4">
    <div class="w-full max-w-sm rounded-2xl border border-ink/10 bg-surface p-6">
      <p class="mb-1 font-serif text-lg text-ink">飲食管理</p>
      <p class="mb-4 text-sm text-tea">請輸入存取密碼</p>
      <input
        v-model="password"
        type="password"
        placeholder="密碼"
        autofocus
        class="w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
        @keyup.enter="submit"
      />
      <p v-if="errorMsg" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ errorMsg }}</p>
      <button
        class="mt-3 w-full rounded-lg bg-accent px-4 py-2 text-sm font-medium text-on-accent hover:bg-accent-bright disabled:opacity-50"
        :disabled="submitting || !password"
        @click="submit"
      >
        {{ submitting ? '確認中…' : '進入' }}
      </button>
    </div>
  </div>
  <slot v-else />
</template>

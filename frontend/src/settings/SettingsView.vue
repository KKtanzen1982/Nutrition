<script setup lang="ts">
import { reactive, ref } from 'vue'
import { backupExportUrl, importBackup } from './backup_api'
import {
  createPurchaseLocation,
  deletePurchaseLocation,
  listPurchaseLocations,
  updatePurchaseLocation,
} from '../shopping/purchase_location_api'
import { fetchUser } from '../users/users_api'
import { useConfirmDialog } from '../shared/useConfirmDialog'
import { useHouseholdConfig, type KnownUser } from '../shared/useHouseholdConfig'
import type { PurchaseLocation } from '../shared/types'

const { config, setUsers, userIcon } = useHouseholdConfig()
const { confirmDialog } = useConfirmDialog()

interface UserRow {
  id: string
  name: string
  verifying: boolean
  verifyError: string | null
  verified: boolean
}

function toRow(user: KnownUser): UserRow {
  return { id: String(user.id), name: user.name, verifying: false, verifyError: null, verified: true }
}

const userRows = ref<UserRow[]>(config.value.users.map(toRow))
const userSaveMessage = ref<string | null>(null)

function addUserRow() {
  userRows.value.push({ id: '', name: '', verifying: false, verifyError: null, verified: false })
}

function removeUserRow(index: number) {
  userRows.value.splice(index, 1)
}

function onIdChange(row: UserRow) {
  row.verified = false
  row.name = ''
  row.verifyError = null
}

async function verifyUserRow(row: UserRow) {
  const id = Number(row.id)
  if (!id) return
  row.verifying = true
  row.verifyError = null
  try {
    const user = await fetchUser(id)
    row.name = user.name
    row.verified = true
  } catch (e) {
    row.verified = false
    row.verifyError = e instanceof Error ? e.message : '查無此使用者'
  } finally {
    row.verifying = false
  }
}

function saveUsers() {
  const users: KnownUser[] = userRows.value
    .filter((r) => r.verified && r.id.trim() && r.name.trim())
    .map((r) => ({ id: Number(r.id), name: r.name.trim() }))
  setUsers(users)
  userRows.value = users.map(toRow)
  userSaveMessage.value = '已儲存'
  setTimeout(() => {
    userSaveMessage.value = null
  }, 2000)
}

const locations = ref<PurchaseLocation[]>([])
const locationsLoading = ref(true)
const locationsError = ref<string | null>(null)

async function loadLocations() {
  locationsLoading.value = true
  locationsError.value = null
  try {
    locations.value = await listPurchaseLocations()
  } catch (e) {
    locationsError.value = e instanceof Error ? e.message : '讀取購買地點失敗'
  } finally {
    locationsLoading.value = false
  }
}
loadLocations()

const editingLocationId = ref<number | null>(null)
const editLocationForm = reactive({ location_name: '', description: '', priority_order: 0 })
const savingLocation = ref(false)

function startEditLocation(loc: PurchaseLocation) {
  editingLocationId.value = loc.id
  Object.assign(editLocationForm, {
    location_name: loc.location_name,
    description: loc.description ?? '',
    priority_order: loc.priority_order,
  })
}

async function submitEditLocation(loc: PurchaseLocation) {
  savingLocation.value = true
  locationsError.value = null
  try {
    await updatePurchaseLocation(loc.id, {
      location_name: editLocationForm.location_name,
      description: editLocationForm.description || null,
      priority_order: editLocationForm.priority_order,
    })
    editingLocationId.value = null
    await loadLocations()
  } catch (e) {
    locationsError.value = e instanceof Error ? e.message : '更新失敗'
  } finally {
    savingLocation.value = false
  }
}

async function removeLocation(loc: PurchaseLocation) {
  if (!(await confirmDialog(`刪除購買地點「${loc.location_name}」？`))) return
  locationsError.value = null
  try {
    await deletePurchaseLocation(loc.id)
    await loadLocations()
  } catch (e) {
    locationsError.value = e instanceof Error ? e.message : '刪除失敗'
  }
}

const newLocationForm = reactive({ location_name: '', description: '', priority_order: 99 })
const addingLocation = ref(false)

async function submitNewLocation() {
  if (!newLocationForm.location_name.trim()) return
  addingLocation.value = true
  locationsError.value = null
  try {
    await createPurchaseLocation({
      location_name: newLocationForm.location_name,
      description: newLocationForm.description || null,
      priority_order: newLocationForm.priority_order,
    })
    newLocationForm.location_name = ''
    newLocationForm.description = ''
    newLocationForm.priority_order = 99
    await loadLocations()
  } catch (e) {
    locationsError.value = e instanceof Error ? e.message : '新增失敗'
  } finally {
    addingLocation.value = false
  }
}

const importFile = ref<File | null>(null)
const importing = ref(false)
const importError = ref<string | null>(null)
const importMessage = ref<string | null>(null)

function onImportFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  importFile.value = target.files?.[0] ?? null
  importError.value = null
  importMessage.value = null
}

async function submitImport() {
  if (!importFile.value) return
  if (!(await confirmDialog('匯入備份會直接覆蓋掉目前所有資料，且無法復原，確定要繼續嗎？'))) return
  importing.value = true
  importError.value = null
  importMessage.value = null
  try {
    const result = await importBackup(importFile.value)
    importMessage.value = result.message
    importFile.value = null
    setTimeout(() => window.location.reload(), 1500)
  } catch (e) {
    importError.value = e instanceof Error ? e.message : '匯入失敗，請稍後再試'
  } finally {
    importing.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-2xl px-4 py-8">
    <h1 class="font-serif text-2xl text-ink">設定</h1>

    <section class="mt-4 rounded-2xl border border-ink/10 bg-surface p-6">
      <div class="flex items-center gap-1.5">
        <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-ink" aria-hidden="true" />
        <h2 class="border-b-[1.5px] border-accent pb-1 text-[11.5px] font-semibold uppercase tracking-wide text-muted">使用者</h2>
      </div>
      <p class="mt-2 text-xs text-tea">
        因為後端沒有「取得所有使用者」的列表端點，這裡只能手動輸入 ID；按「驗證」跟後端確認這個 ID 真的存在並帶出姓名——姓名不能手動輸入，要跟個人資料保持一致，才能儲存。
      </p>

      <div v-for="(row, i) in userRows" :key="i" class="mt-3 flex items-center gap-2">
        <span class="w-6 shrink-0 text-center">{{ config.users[i] ? userIcon(config.users[i].id) : '🙂' }}</span>
        <input
          v-model="row.id"
          type="number"
          placeholder="使用者 ID"
          class="w-28 rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
          @input="onIdChange(row)"
        />
        <span class="min-w-0 flex-1 rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm" :class="row.name ? 'text-ink' : 'text-tea'">
          {{ row.name || '（按驗證取得姓名）' }}
        </span>
        <button
          type="button"
          class="shrink-0 rounded-lg border border-ink/15 px-3 py-2 text-xs font-semibold text-ink hover:bg-bg disabled:opacity-50"
          :disabled="row.verifying || !row.id"
          @click="verifyUserRow(row)"
        >
          {{ row.verifying ? '驗證中…' : row.verified ? '✓ 已驗證' : '驗證' }}
        </button>
        <button type="button" class="shrink-0 text-xs text-tea hover:text-alert" @click="removeUserRow(i)">移除</button>
      </div>
      <p v-for="(row, i) in userRows" :key="`err-${i}`" class="mt-1 text-xs text-alert">{{ row.verifyError }}</p>

      <button type="button" class="mt-3 text-xs font-semibold text-accent hover:text-accent-bright" @click="addUserRow">+ 新增使用者</button>

      <div class="mt-4 flex items-center gap-3">
        <button
          type="button"
          class="rounded-full bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-bright"
          @click="saveUsers"
        >
          儲存
        </button>
        <span v-if="userSaveMessage" class="text-xs text-accent">{{ userSaveMessage }}</span>
      </div>
    </section>

    <section class="mt-6 rounded-2xl border border-ink/10 bg-surface p-6">
      <div class="flex items-center gap-1.5">
        <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-ink" aria-hidden="true" />
        <h2 class="border-b-[1.5px] border-accent pb-1 text-[11.5px] font-semibold uppercase tracking-wide text-muted">購買地點</h2>
      </div>

      <p v-if="locationsLoading" class="mt-3 text-sm text-tea">載入中…</p>
      <p v-if="locationsError" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ locationsError }}</p>

      <ul v-if="!locationsLoading && locations.length" class="mt-3 divide-y divide-ink/10">
        <li v-for="loc in locations" :key="loc.id" class="py-3">
          <div v-if="editingLocationId !== loc.id" class="flex items-center justify-between">
            <div>
              <p class="text-sm text-ink">{{ loc.location_name }}</p>
              <p v-if="loc.description" class="text-xs text-tea">{{ loc.description }}</p>
            </div>
            <div class="flex shrink-0 gap-3">
              <button type="button" class="text-xs font-semibold text-accent hover:text-accent-bright" @click="startEditLocation(loc)">編輯</button>
              <button type="button" class="text-xs text-tea hover:text-alert" @click="removeLocation(loc)">刪除</button>
            </div>
          </div>
          <div v-else class="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <input v-model="editLocationForm.location_name" type="text" class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink sm:col-span-2" />
            <input v-model="editLocationForm.description" type="text" placeholder="說明" class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
            <input v-model.number="editLocationForm.priority_order" type="number" placeholder="優先順序" class="rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" />
            <button type="button" class="rounded-full bg-accent px-3 py-1 text-xs font-semibold text-on-accent disabled:opacity-50" :disabled="savingLocation" @click="submitEditLocation(loc)">
              {{ savingLocation ? '儲存中…' : '儲存' }}
            </button>
            <button type="button" class="text-xs text-tea" @click="editingLocationId = null">取消</button>
          </div>
        </li>
      </ul>
      <p v-else-if="!locationsLoading" class="mt-3 text-sm text-tea">尚無購買地點</p>

      <div class="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <input v-model="newLocationForm.location_name" type="text" placeholder="地點名稱" class="rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink sm:col-span-2" />
        <input v-model="newLocationForm.description" type="text" placeholder="說明（選填）" class="rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
        <input v-model.number="newLocationForm.priority_order" type="number" placeholder="優先順序" class="rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink" />
      </div>
      <button
        type="button"
        class="mt-3 w-full rounded-full bg-accent py-2.5 text-sm font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
        :disabled="addingLocation || !newLocationForm.location_name.trim()"
        @click="submitNewLocation"
      >
        {{ addingLocation ? '新增中…' : '+ 新增購買地點' }}
      </button>
    </section>

    <section class="mt-6 rounded-2xl border border-ink/10 bg-surface p-6">
      <div class="flex items-center gap-1.5">
        <span class="h-1.5 w-1.5 shrink-0 rounded-full bg-ink" aria-hidden="true" />
        <h2 class="border-b-[1.5px] border-accent pb-1 text-[11.5px] font-semibold uppercase tracking-wide text-muted">資料備份</h2>
      </div>
      <p class="mt-2 text-xs text-tea">
        匯出整個資料庫成一個檔案，之後可以用同一個檔案還原——建議定期匯出保存，以免資料遺失。
      </p>

      <a
        :href="backupExportUrl()"
        class="mt-4 block w-full rounded-full bg-accent py-2.5 text-center text-sm font-semibold text-on-accent hover:bg-accent-bright"
      >
        匯出備份
      </a>

      <div class="mt-6 border-t border-ink/10 pt-4">
        <p class="text-xs text-tea">
          匯入備份會<span class="font-semibold text-alert">整個覆蓋</span>目前的資料，請先確認選對檔案。
        </p>
        <input
          type="file"
          accept=".json"
          class="mt-3 block w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-sm text-ink"
          @change="onImportFileChange"
        />
        <p v-if="importError" class="mt-2 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ importError }}</p>
        <p v-if="importMessage" class="mt-2 rounded-lg bg-accent-tint px-3 py-2 text-sm text-ink">{{ importMessage }}</p>
        <button
          type="button"
          class="mt-3 w-full rounded-full border border-alert px-4 py-2 text-sm font-semibold text-alert hover:bg-alert/10 disabled:opacity-50"
          :disabled="!importFile || importing"
          @click="submitImport"
        >
          {{ importing ? '匯入中…' : '匯入備份' }}
        </button>
      </div>
    </section>
  </div>
</template>

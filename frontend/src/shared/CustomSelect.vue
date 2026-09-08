<script setup lang="ts">
import { ref } from 'vue'
import { useConfirmDialog } from './useConfirmDialog'

const props = withDefaults(
  defineProps<{
    modelValue: string
    options: string[]
    manageableOptions: string[]
    label: string
    allowEmpty?: boolean
    emptyLabel?: string
    addOption: (name: string) => string | null
    renameOption: (oldName: string, newName: string) => string | null
    removeOption: (name: string) => void
  }>(),
  { allowEmpty: true, emptyLabel: '未選擇' },
)

const emit = defineEmits<{ 'update:modelValue': [string] }>()

const { confirmDialog } = useConfirmDialog()

function onSelect(e: Event) {
  emit('update:modelValue', (e.target as HTMLSelectElement).value)
}

const showManager = ref(false)
const newName = ref('')
const managerError = ref<string | null>(null)
const editingName = ref<string | null>(null)
const editNameInput = ref('')

function submitAdd() {
  const err = props.addOption(newName.value)
  if (err) {
    managerError.value = err
    return
  }
  newName.value = ''
  managerError.value = null
}

function startEdit(name: string) {
  editingName.value = name
  editNameInput.value = name
  managerError.value = null
}

function cancelEdit() {
  editingName.value = null
}

function submitEdit() {
  if (!editingName.value) return
  const err = props.renameOption(editingName.value, editNameInput.value)
  if (err) {
    managerError.value = err
    return
  }
  if (props.modelValue === editingName.value) emit('update:modelValue', editNameInput.value.trim())
  editingName.value = null
  managerError.value = null
}

async function submitRemove(name: string) {
  if (!(await confirmDialog(`刪除自訂選項「${name}」？`))) return
  props.removeOption(name)
  if (props.modelValue === name) {
    const fallback = props.allowEmpty ? '' : props.options.find((o) => o !== name) ?? ''
    emit('update:modelValue', fallback)
  }
}
</script>

<template>
  <div>
    <div class="flex items-center gap-1.5">
      <select :value="modelValue" class="w-full rounded border border-ink/15 bg-bg px-2 py-1 text-sm text-ink" @change="onSelect">
        <option v-if="allowEmpty" value="">{{ emptyLabel }}</option>
        <option v-for="o in options" :key="o" :value="o">{{ o }}</option>
      </select>
      <button
        type="button"
        class="shrink-0 text-xs text-tea hover:text-ink"
        :aria-label="`管理${label}選項`"
        @click="showManager = !showManager"
      >
        {{ showManager ? '收起' : '管理' }}
      </button>
    </div>

    <div v-if="showManager" class="mt-2 rounded-lg border border-ink/10 bg-surface p-2">
      <ul v-if="manageableOptions.length" class="divide-y divide-ink/10">
        <li v-for="o in manageableOptions" :key="o" class="flex items-center justify-between gap-2 py-1">
          <template v-if="editingName === o">
            <input
              v-model="editNameInput"
              type="text"
              class="min-w-0 flex-1 rounded border border-ink/15 bg-bg px-1.5 py-0.5 text-xs text-ink"
            />
            <button type="button" class="shrink-0 text-xs font-semibold text-accent hover:text-accent-bright" @click="submitEdit">存</button>
            <button type="button" class="shrink-0 text-xs text-tea" @click="cancelEdit">取消</button>
          </template>
          <template v-else>
            <span class="text-xs text-ink">{{ o }}</span>
            <div class="flex shrink-0 gap-2">
              <button type="button" class="text-xs font-semibold text-accent hover:text-accent-bright" @click="startEdit(o)">編輯</button>
              <button type="button" class="text-xs text-tea hover:text-alert" @click="submitRemove(o)">刪除</button>
            </div>
          </template>
        </li>
      </ul>
      <p v-else class="text-xs text-tea">尚無自訂選項</p>

      <div class="mt-2 flex items-center gap-1.5">
        <input
          v-model="newName"
          type="text"
          :placeholder="`新增${label}`"
          class="min-w-0 flex-1 rounded border border-ink/15 bg-bg px-1.5 py-0.5 text-xs text-ink"
          @keyup.enter="submitAdd"
        />
        <button type="button" class="shrink-0 rounded-full bg-accent px-2 py-0.5 text-xs font-semibold text-on-accent hover:bg-accent-bright" @click="submitAdd">
          新增
        </button>
      </div>
      <p v-if="managerError" class="mt-1 text-xs text-alert">{{ managerError }}</p>
    </div>
  </div>
</template>

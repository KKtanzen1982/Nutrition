<script setup lang="ts">
import { ref, watch } from 'vue'
import Modal from '../shared/Modal.vue'
import { updateDailyStepsRecord } from '../fitness/exercise_api'
import type { DailyStepsRecord } from '../shared/types'

const props = defineProps<{
  modelValue: boolean
  record: DailyStepsRecord | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  saved: [record: DailyStepsRecord]
}>()

const stepCount = ref<number | null>(null)
const saving = ref(false)
const error = ref<string | null>(null)

watch(
  () => [props.modelValue, props.record],
  () => {
    if (props.modelValue && props.record) {
      stepCount.value = props.record.step_count
      error.value = null
    }
  },
  { immediate: true },
)

async function save() {
  if (!props.record || stepCount.value === null) return
  saving.value = true
  error.value = null
  try {
    const updated = await updateDailyStepsRecord(props.record.id, { step_count: stepCount.value })
    emit('saved', updated)
    emit('update:modelValue', false)
  } catch (e) {
    error.value = e instanceof Error ? e.message : '更新失敗，請稍後再試'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <Modal :model-value="modelValue" title="今天已經記錄過步數了" @update:model-value="(v) => emit('update:modelValue', v)">
    <template v-if="record">
      <p class="text-sm text-tea">{{ record.date }} 已經有一筆步數紀錄，一天只能有一筆，直接修改成新的數字：</p>
      <label class="mt-3 block text-xs text-tea">
        步數
        <input
          v-model.number="stepCount"
          type="number"
          min="0"
          class="mt-1 w-full rounded-lg border border-ink/15 bg-bg px-3 py-2 text-2xl font-semibold text-ink"
        />
      </label>
      <p v-if="error" class="mt-3 rounded-lg bg-alert/10 px-3 py-2 text-sm text-alert">{{ error }}</p>
      <button
        type="button"
        class="mt-4 w-full rounded-full bg-accent py-2.5 text-sm font-semibold text-on-accent hover:bg-accent-bright disabled:opacity-50"
        :disabled="saving || stepCount === null"
        @click="save"
      >
        {{ saving ? '儲存中…' : '更新這天的紀錄' }}
      </button>
    </template>
  </Modal>
</template>

import { reactive } from 'vue'

interface ConfirmDialogState {
  open: boolean
  message: string
  resolve: ((value: boolean) => void) | null
}

// 全域單例狀態：window.confirm() 在部分內嵌瀏覽器/PWA 環境下會被靜默阻擋且不拋錯，
// 改用 App 內建對話框才能保證使用者一定看得到確認提示。
const state = reactive<ConfirmDialogState>({ open: false, message: '', resolve: null })

export function useConfirmDialog() {
  function confirmDialog(message: string): Promise<boolean> {
    state.message = message
    state.open = true
    return new Promise<boolean>((resolve) => {
      state.resolve = resolve
    })
  }

  function respond(value: boolean) {
    state.open = false
    state.resolve?.(value)
    state.resolve = null
  }

  return { state, confirmDialog, respond }
}

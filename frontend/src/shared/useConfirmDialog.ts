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
    // 如果上一個對話框還沒被回應就再叫一次（例如呼叫端忘記 await、或使用者連點兩次觸發鍵），
    // 舊的 Promise 會被下面這行的 resolve 蓋掉、永遠卡住不會 resolve，呼叫端的 await 就這樣掛住，
    // 使用者只會看到「按下確定好像沒反應」，要再操作一次才會生效。所以先把舊的用 false 結掉，
    // 保證任何一次 confirmDialog() 呼叫最後都一定會被 resolve。
    state.resolve?.(false)
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

export type ToastTone = 'info' | 'success' | 'error'
export type Toast = { id: number; message: string; tone: ToastTone; durationMs: number }

type Listener = (toasts: Toast[]) => void

const listeners = new Set<Listener>()
let toasts: Toast[] = []
let nextId = 1

function emit() {
  for (const listener of listeners) listener(toasts)
}

/** Shows a short message; errors stay longer because they carry a next step. */
export function toast(message: string, tone: ToastTone = 'info', durationMs = tone === 'error' ? 7000 : 4000): number {
  const id = nextId++
  toasts = [...toasts.slice(-2), { id, message, tone, durationMs }]
  emit()
  return id
}

export function dismissToast(id: number) {
  if (!toasts.some((item) => item.id === id)) return
  toasts = toasts.filter((item) => item.id !== id)
  emit()
}

export function subscribeToasts(listener: Listener): () => void {
  listeners.add(listener)
  listener(toasts)
  return () => { listeners.delete(listener) }
}

/** Test helper: wipes the queue so one test cannot leak into the next. */
export function resetToasts() {
  toasts = []
  emit()
}

import { create } from 'zustand'

export type ToastKind = 'success' | 'info' | 'error'

export interface Toast {
  id: number
  kind: ToastKind
  title: string
  message?: string
}

interface ToastState {
  toasts: Toast[]
  push(kind: ToastKind, title: string, message?: string): void
  dismiss(id: number): void
}

let nextId = 1

export const useToasts = create<ToastState>((set, get) => ({
  toasts: [],
  push: (kind, title, message) => {
    const id = nextId++
    set((s) => ({ toasts: [...s.toasts.slice(-3), { id, kind, title, message }] }))
    setTimeout(() => get().dismiss(id), kind === 'error' ? 7000 : 3500)
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
}))

export const toast = {
  success: (title: string, message?: string) => useToasts.getState().push('success', title, message),
  info: (title: string, message?: string) => useToasts.getState().push('info', title, message),
  error: (title: string, message?: string) => useToasts.getState().push('error', title, message)
}

export function errorMessage(error: unknown): string {
  const text = error instanceof Error ? error.message : String(error)
  // Erros vindos do processo principal chegam com esse prefixo técnico.
  return text.replace(/^Error invoking remote method '[^']+': (Error: )?/, '')
}

import { create } from 'zustand'
import type { ToastAction, ToastType } from '../components/ui/Toast'

export interface ToastItem {
  id: string
  type: ToastType
  message: string
  actions?: ToastAction[]
}

interface ToastState {
  toasts: ToastItem[]
  add: (type: ToastType, message: string, actions?: ToastAction[]) => void
  dismiss: (id: string) => void
}

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],

  add: (type, message, actions) => {
    const id = Date.now().toString()
    set((s) => ({ toasts: [...s.toasts, { id, type, message, actions }] }))

    // Auto-dismiss after 4 seconds
    setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
    }, actions?.length ? 8000 : 4000)
  },

  dismiss: (id) => {
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
  },
}))

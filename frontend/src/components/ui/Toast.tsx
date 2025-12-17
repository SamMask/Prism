import { useEffect, useState } from 'react'
import { CheckCircle, XCircle, AlertCircle, Info, X } from 'lucide-react'
import { createPortal } from 'react-dom'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

interface Toast {
  id: string
  type: ToastType
  message: string
}

// Toast state management
let toastListeners: ((toasts: Toast[]) => void)[] = []
let toasts: Toast[] = []

const notify = (type: ToastType, message: string) => {
  const id = Date.now().toString()
  toasts = [...toasts, { id, type, message }]
  toastListeners.forEach((listener) => listener(toasts))

  // Auto dismiss after 4 seconds
  setTimeout(() => {
    toasts = toasts.filter((t) => t.id !== id)
    toastListeners.forEach((listener) => listener(toasts))
  }, 4000)
}

export const toast = {
  success: (message: string) => notify('success', message),
  error: (message: string) => notify('error', message),
  warning: (message: string) => notify('warning', message),
  info: (message: string) => notify('info', message),
}

export function ToastContainer() {
  const [items, setItems] = useState<Toast[]>([])

  useEffect(() => {
    toastListeners.push(setItems)
    return () => {
      toastListeners = toastListeners.filter((l) => l !== setItems)
    }
  }, [])

  const dismiss = (id: string) => {
    toasts = toasts.filter((t) => t.id !== id)
    toastListeners.forEach((listener) => listener(toasts))
  }

  if (items.length === 0) return null

  const icons = {
    success: CheckCircle,
    error: XCircle,
    warning: AlertCircle,
    info: Info,
  }

  const colors = {
    success: 'bg-success/10 border-success/30 text-success',
    error: 'bg-danger/10 border-danger/30 text-danger',
    warning: 'bg-warning/10 border-warning/30 text-warning',
    info: 'bg-primary/10 border-primary/30 text-primary',
  }

  return createPortal(
    <div className="fixed bottom-4 right-4 z-[100] space-y-2">
      {items.map((t) => {
        const Icon = icons[t.type]
        return (
          <div
            key={t.id}
            className={`
              flex items-center gap-3 px-4 py-3 rounded-lg
              border backdrop-blur-sm
              ${colors[t.type]}
              animate-in slide-in-from-right-5 duration-300
            `}
          >
            <Icon size={18} />
            <span className="text-sm font-medium text-text-primary">{t.message}</span>
            <button
              onClick={() => dismiss(t.id)}
              className="ml-2 p-1 rounded hover:bg-bg-hover transition-colors"
            >
              <X size={14} />
            </button>
          </div>
        )
      })}
    </div>,
    document.body
  )
}

import { createPortal } from 'react-dom'
import { CheckCircle, XCircle, AlertCircle, Info, X } from 'lucide-react'
import { useToastStore } from '../../stores/toastStore'
import { IconButton } from './IconButton'
import { t as translate } from '../../i18n'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

// Public API — same call signature as before, no import changes needed in callers
export const toast = {
  success: (message: string) => useToastStore.getState().add('success', message),
  error:   (message: string) => useToastStore.getState().add('error',   message),
  warning: (message: string) => useToastStore.getState().add('warning', message),
  info:    (message: string) => useToastStore.getState().add('info',    message),
}

export function ToastContainer() {
  const { toasts, dismiss } = useToastStore()

  if (toasts.length === 0) return null

  const icons = {
    success: CheckCircle,
    error:   XCircle,
    warning: AlertCircle,
    info:    Info,
  }

  const colors = {
    success: 'bg-success/10 border-success/30 text-success',
    error:   'bg-danger/10 border-danger/30 text-danger',
    warning: 'bg-warning/10 border-warning/30 text-warning',
    info:    'bg-primary/10 border-primary/30 text-primary',
  }

  return createPortal(
    <div className="fixed bottom-4 right-4 z-[100] space-y-2" role="region" aria-label={translate('ui.toast.region')}>
      {toasts.map((t) => {
        const Icon = icons[t.type]
        return (
          <div
            key={t.id}
            role="status"
            aria-live="polite"
            className={`
              flex items-center gap-3 px-4 py-3 rounded-lg
              border backdrop-blur-sm
              ${colors[t.type]}
              animate-in slide-in-from-right-5 duration-300
            `}
          >
            <Icon size={18} />
            <span className="text-sm font-medium text-text-primary">{t.message}</span>
            <IconButton
              size="xs"
              onClick={() => dismiss(t.id)}
              aria-label={translate('ui.toast.close')}
              className="ml-2"
            >
              <X size={14} />
            </IconButton>
          </div>
        )
      })}
    </div>,
    document.body
  )
}

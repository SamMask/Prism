import { useEffect, useRef, useState, useCallback } from 'react'
import { AlertTriangle } from 'lucide-react'
import { createPortal } from 'react-dom'

interface ConfirmOptions {
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  variant?: 'danger' | 'warning'
}

// Module-level state — same pattern as Toast (simple, works)
let showConfirm: ((options: ConfirmOptions) => Promise<boolean>) | null = null

/**
 * Imperative confirm() replacement.
 * Usage: const ok = await confirm({ title: '刪除', message: '確定？' })
 */
export const confirm = (options: ConfirmOptions): Promise<boolean> => {
  if (!showConfirm) {
    // Fallback to native if ConfirmDialogProvider not mounted
    return Promise.resolve(window.confirm(options.message))
  }
  return showConfirm(options)
}

export function ConfirmDialogProvider() {
  const [state, setState] = useState<{
    options: ConfirmOptions
    resolve: (value: boolean) => void
  } | null>(null)

  const confirmBtnRef = useRef<HTMLButtonElement>(null)

  const handleShow = useCallback((options: ConfirmOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      setState({ options, resolve })
    })
  }, [])

  useEffect(() => {
    showConfirm = handleShow
    return () => { showConfirm = null }
  }, [handleShow])

  // Focus confirm button when dialog opens
  useEffect(() => {
    if (state) confirmBtnRef.current?.focus()
  }, [state])

  // ESC to cancel
  useEffect(() => {
    if (!state) return
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        state.resolve(false)
        setState(null)
      }
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [state])

  if (!state) return null

  const { options, resolve } = state
  const isDanger = options.variant === 'danger'

  const handleConfirm = () => { resolve(true); setState(null) }
  const handleCancel = () => { resolve(false); setState(null) }

  return createPortal(
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center p-4
                 bg-black/60 backdrop-blur-sm animate-in fade-in duration-150"
      onClick={(e) => { if (e.target === e.currentTarget) handleCancel() }}
    >
      <div className="w-full max-w-md bg-bg-surface border border-border-default
                      rounded-xl shadow-2xl shadow-black/50
                      animate-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-start gap-3 px-6 pt-6 pb-2">
          <div className={`p-2 rounded-lg ${isDanger ? 'bg-danger/10' : 'bg-warning/10'}`}>
            <AlertTriangle size={20} className={isDanger ? 'text-danger' : 'text-warning'} />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-text-primary">{options.title}</h3>
            <p className="mt-1 text-sm text-text-secondary whitespace-pre-line">{options.message}</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-3 px-6 py-4">
          <button
            onClick={handleCancel}
            className="px-4 py-2 text-sm font-medium rounded-lg
                       text-text-secondary hover:text-text-primary
                       hover:bg-bg-hover transition-colors"
          >
            {options.cancelText || '取消'}
          </button>
          <button
            ref={confirmBtnRef}
            onClick={handleConfirm}
            className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors
              ${isDanger
                ? 'bg-danger text-white hover:bg-danger/80'
                : 'bg-warning text-white hover:bg-warning/80'
              }`}
          >
            {options.confirmText || '確定'}
          </button>
        </div>
      </div>
    </div>,
    document.body
  )
}

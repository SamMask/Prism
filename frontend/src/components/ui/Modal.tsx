import { ReactNode, RefObject, useEffect, useId, useRef, useState } from 'react'
import { X } from 'lucide-react'
import { createPortal } from 'react-dom'
import { IconButton } from './IconButton'
import { t } from '../../i18n'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
}

// Open dialogs, bottom to top. Only the topmost one reacts to Escape/Tab.
const dialogStack: { id: string; el: HTMLElement | null }[] = []
// Which dialog was topmost when the current keydown started (captured before any handler runs,
// so a dialog that closes itself mid-event cannot hand the same Escape to the one beneath it).
let topAtKeydown: string | undefined
if (typeof window !== 'undefined') {
  window.addEventListener('keydown', () => { topAtKeydown = dialogStack[dialogStack.length - 1]?.id }, true)
}

const FOCUSABLE =
  'a[href],button,input:not([type="hidden"]),select,textarea,summary,iframe,audio[controls],video[controls],' +
  '[contenteditable]:not([contenteditable="false"]),[tabindex]'

// tabIndex < 0 (tabindex="-1" on any element) is reachable by script only, so it is not in the cycle.
const focusablesIn = (root: HTMLElement) =>
  Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (el) => el.tabIndex >= 0 && !el.matches(':disabled') && el.getClientRects().length > 0,
  )

/**
 * Modal-dialog behavior shared by Modal and ConfirmDialog: focus moves in on open, Tab cycles
 * inside the topmost dialog only, Escape goes to the topmost dialog only, and focus returns to
 * the opener on close.
 */
export function useDialogLayer(open: boolean, dialogRef: RefObject<HTMLElement>, onEscape: () => void) {
  const id = useId()
  const escapeRef = useRef(onEscape)
  escapeRef.current = onEscape
  // Read during render, before children autofocus anything, so it is the element that opened us.
  // Set once per open and cleared only when closed, so StrictMode's extra effect pass keeps it.
  const openerRef = useRef<HTMLElement | null>(null)
  if (!open) openerRef.current = null
  else if (!openerRef.current) openerRef.current = document.activeElement as HTMLElement | null

  useEffect(() => {
    if (!open) return
    const opener = openerRef.current
    const dialog = dialogRef.current
    dialogStack.push({ id, el: dialog })
    if (dialog && !dialog.contains(document.activeElement)) (focusablesIn(dialog)[0] ?? dialog).focus()

    const onKeyDown = (e: KeyboardEvent) => {
      if (topAtKeydown !== id) return
      if (e.key === 'Escape') {
        escapeRef.current()
        return
      }
      if (e.key !== 'Tab' || !dialog) return
      const items = focusablesIn(dialog)
      const active = document.activeElement as HTMLElement | null
      const first = items[0]
      const last = items[items.length - 1]
      if (!first || !active || !items.includes(active)) {
        e.preventDefault()
        ;((e.shiftKey ? last : first) ?? dialog).focus()
      } else if (e.shiftKey && active === first) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && active === last) {
        e.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      dialogStack.splice(dialogStack.findIndex((layer) => layer.id === id), 1)
      // Opener gone, disabled or body: keep focus inside the dialog layer below, if any.
      opener?.focus()
      if (opener === document.body || document.activeElement !== opener) dialogStack[dialogStack.length - 1]?.el?.focus()
    }
  }, [open, id, dialogRef])
}

export function Modal({ isOpen, onClose, title, children, size = 'md' }: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null)
  const dialogRef = useRef<HTMLDivElement>(null)
  const titleId = useId()
  // Without a title prop, label the dialog by its first heading (editor, reading view, history).
  const [headingId, setHeadingId] = useState<string>()

  useDialogLayer(isOpen, dialogRef, onClose)

  useEffect(() => {
    if (!isOpen) return
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [isOpen])

  useEffect(() => {
    if (!isOpen || title) return
    const heading = dialogRef.current?.querySelector('h1,h2,h3')
    if (heading) {
      heading.id ||= titleId
      setHeadingId(heading.id)
    }
  }, [isOpen, title, titleId])

  // Handle click outside
  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) onClose()
  }

  if (!isOpen) return null

  const sizes = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    full: 'max-w-[90vw] max-h-[90vh]',
  }

  return createPortal(
    <div
      ref={overlayRef}
      onClick={handleOverlayClick}
      className="fixed inset-0 z-50 flex items-center justify-center p-4
                 bg-black/60 backdrop-blur-sm
                 animate-in fade-in duration-200"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : headingId}
        tabIndex={-1}
        className={`
          outline-none w-full ${sizes[size]}
          bg-bg-surface border border-border-default rounded-xl
          shadow-2xl shadow-black/50
          animate-in zoom-in-95 duration-200
        `}
      >
        {/* Header */}
        {title && (
          <div className="flex items-center justify-between px-6 py-4 border-b border-border-subtle">
            <h2 id={titleId} className="text-lg font-semibold text-text-primary">{title}</h2>
            <IconButton size="sm" onClick={onClose} aria-label={t('ui.modal.close')}>
              <X size={20} />
            </IconButton>
          </div>
        )}

        {/* Content */}
        <div className={title ? '' : 'pt-4'}>
          {children}
        </div>
      </div>
    </div>,
    document.body
  )
}

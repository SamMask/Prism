import { ReactNode, useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import { createPortal } from 'react-dom'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: ReactNode
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full'
}

export function Modal({ isOpen, onClose, title, children, size = 'md' }: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null)

  // Handle ESC key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEsc)
      document.body.style.overflow = 'hidden'
    }

    return () => {
      document.removeEventListener('keydown', handleEsc)
      document.body.style.overflow = ''
    }
  }, [isOpen, onClose])

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
        className={`
          w-full ${sizes[size]}
          bg-bg-surface border border-border-default rounded-xl
          shadow-2xl shadow-black/50
          animate-in zoom-in-95 duration-200
        `}
      >
        {/* Header */}
        {title && (
          <div className="flex items-center justify-between px-6 py-4 border-b border-border-subtle">
            <h2 className="text-lg font-semibold text-text-primary">{title}</h2>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-text-muted
                         hover:bg-bg-hover hover:text-text-primary
                         transition-colors duration-200"
            >
              <X size={20} />
            </button>
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

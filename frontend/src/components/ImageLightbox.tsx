import { ChevronLeft, ChevronRight, Copy, ExternalLink, X } from 'lucide-react'
import { useCallback, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { useTranslation } from '../hooks/useTranslation'
import { toast } from './ui/Toast'

export interface LightboxImage {
  src: string
  alt?: string
}

interface ImageLightboxProps {
  images: LightboxImage[]
  activeIndex: number
  onActiveIndexChange: (index: number) => void
  onClose: () => void
}

export function ImageLightbox({
  images,
  activeIndex,
  onActiveIndexChange,
  onClose,
}: ImageLightboxProps) {
  const { t } = useTranslation()
  const currentIndex = Math.min(Math.max(activeIndex, 0), images.length - 1)
  const currentImage = images[currentIndex]
  const hasMultipleImages = images.length > 1

  const goToPrevious = useCallback(() => {
    if (!hasMultipleImages) return
    onActiveIndexChange((currentIndex - 1 + images.length) % images.length)
  }, [currentIndex, hasMultipleImages, images.length, onActiveIndexChange])

  const goToNext = useCallback(() => {
    if (!hasMultipleImages) return
    onActiveIndexChange((currentIndex + 1) % images.length)
  }, [currentIndex, hasMultipleImages, images.length, onActiveIndexChange])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        event.stopPropagation()
        event.stopImmediatePropagation()
        onClose()
      } else if (event.key === 'ArrowLeft') {
        event.preventDefault()
        event.stopPropagation()
        event.stopImmediatePropagation()
        goToPrevious()
      } else if (event.key === 'ArrowRight') {
        event.preventDefault()
        event.stopPropagation()
        event.stopImmediatePropagation()
        goToNext()
      }
    }

    document.addEventListener('keydown', handleKeyDown, true)
    return () => document.removeEventListener('keydown', handleKeyDown, true)
  }, [goToNext, goToPrevious, onClose])

  if (!currentImage) return null

  const handleCopyPath = async () => {
    try {
      await navigator.clipboard.writeText(currentImage.src)
      toast.success(t('reading.lightboxCopySuccess'))
    } catch {
      toast.error(t('reading.lightboxCopyFailed'))
    }
  }

  const handleOpenOriginal = () => {
    window.open(currentImage.src, '_blank', 'noopener,noreferrer')
  }

  return createPortal(
    <div
      className="fixed inset-0 z-[180] flex items-center justify-center bg-black/90 p-3 backdrop-blur-sm sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-label={t('reading.lightboxTitle')}
      data-testid="image-lightbox"
      onClick={onClose}
    >
      <div className="relative flex h-full w-full max-w-6xl flex-col" onClick={(event) => event.stopPropagation()}>
        <div className="mb-3 flex shrink-0 items-center justify-between gap-3">
          <div className="rounded-md bg-black/50 px-3 py-1 text-sm text-white/80" data-testid="image-lightbox-count">
            {t('reading.lightboxCount', { current: currentIndex + 1, total: images.length })}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopyPath}
              className="rounded-md bg-white/10 p-2 text-white transition-colors hover:bg-white/20 focus:bg-white/20"
              aria-label={t('reading.lightboxCopyPath')}
              title={t('reading.lightboxCopyPath')}
            >
              <Copy size={18} />
            </button>
            <button
              type="button"
              onClick={handleOpenOriginal}
              className="rounded-md bg-white/10 p-2 text-white transition-colors hover:bg-white/20 focus:bg-white/20"
              aria-label={t('reading.lightboxOpenOriginal')}
              title={t('reading.lightboxOpenOriginal')}
            >
              <ExternalLink size={18} />
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-md bg-white/10 p-2 text-white transition-colors hover:bg-white/20 focus:bg-white/20"
              aria-label={t('reading.lightboxClose')}
              title={t('reading.lightboxClose')}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="relative flex min-h-0 flex-1 items-center justify-center">
          {hasMultipleImages && (
            <button
              type="button"
              onClick={goToPrevious}
              className="absolute left-0 z-10 rounded-full bg-black/50 p-3 text-white transition-colors hover:bg-black/70 focus:bg-black/70 sm:left-3"
              aria-label={t('reading.lightboxPrevious')}
              title={t('reading.lightboxPrevious')}
              data-testid="image-lightbox-prev"
            >
              <ChevronLeft size={26} />
            </button>
          )}
          <img
            src={currentImage.src}
            alt={currentImage.alt || t('reading.lightboxImageAlt', { index: currentIndex + 1 })}
            className="max-h-full max-w-full rounded-md object-contain shadow-2xl shadow-black/50"
            data-testid="image-lightbox-image"
          />
          {hasMultipleImages && (
            <button
              type="button"
              onClick={goToNext}
              className="absolute right-0 z-10 rounded-full bg-black/50 p-3 text-white transition-colors hover:bg-black/70 focus:bg-black/70 sm:right-3"
              aria-label={t('reading.lightboxNext')}
              title={t('reading.lightboxNext')}
              data-testid="image-lightbox-next"
            >
              <ChevronRight size={26} />
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body,
  )
}

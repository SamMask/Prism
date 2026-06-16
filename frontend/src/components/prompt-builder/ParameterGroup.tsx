/**
 * ParameterGroup - Collapsible group of parameters
 */
import { useState } from 'react'
import { ChevronDown, Shuffle } from 'lucide-react'
import { useTranslation } from '../../hooks/useTranslation'

interface ParameterGroupProps {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
  onRandomize?: () => void
  defaultOpen?: boolean
}

export function ParameterGroup({ 
  title, 
  icon, 
  children, 
  onRandomize,
  defaultOpen = true 
}: ParameterGroupProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)
  const { t } = useTranslation()

  return (
    <div className="glass rounded-lg overflow-hidden">
      {/* Header */}
      <div
        className="flex w-full items-center justify-between bg-bg-elevated px-4 py-3 transition-colors hover:bg-bg-surface"
      >
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="flex min-w-0 flex-1 items-center gap-2 text-left"
          aria-expanded={isOpen}
        >
          {icon}
          <span className="font-medium text-text-primary">{title}</span>
        </button>
        <div className="flex shrink-0 items-center gap-2">
          {onRandomize && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                onRandomize()
              }}
              className="p-1.5 hover:bg-primary/20 rounded-lg transition-colors"
              title={t('promptBuilder.randomize')}
            >
              <Shuffle size={16} className="text-primary" />
            </button>
          )}
          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            className="rounded-md p-1 text-text-muted transition-colors hover:bg-bg-hover hover:text-text-primary"
            aria-label={isOpen ? t('promptBuilder.collapseSection') : t('promptBuilder.expandSection')}
          >
            <ChevronDown
              size={18}
              className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
            />
          </button>
        </div>
      </div>

      {/* Content */}
      {isOpen && (
        <div className="p-3 sm:p-4 space-y-4 border-t border-border-subtle">
          {children}
        </div>
      )}
    </div>
  )
}

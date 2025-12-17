/**
 * ParameterGroup - Collapsible group of parameters
 */
import { useState } from 'react'
import { ChevronDown, Shuffle } from 'lucide-react'

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

  return (
    <div className="glass rounded-xl overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center justify-between 
                   bg-bg-elevated hover:bg-bg-surface transition-colors"
      >
        <div className="flex items-center gap-2">
          {icon}
          <span className="font-medium text-text-primary">{title}</span>
        </div>
        <div className="flex items-center gap-2">
          {onRandomize && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onRandomize()
              }}
              className="p-1.5 hover:bg-primary/20 rounded-lg transition-colors"
              title="隨機填入"
            >
              <Shuffle size={16} className="text-primary" />
            </button>
          )}
          <ChevronDown 
            size={18} 
            className={`text-text-muted transition-transform duration-200 
                        ${isOpen ? 'rotate-180' : ''}`}
          />
        </div>
      </button>

      {/* Content */}
      {isOpen && (
        <div className="p-4 space-y-4 border-t border-border-subtle">
          {children}
        </div>
      )}
    </div>
  )
}

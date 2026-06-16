/**
 * QuickTemplates - Template selection panel
 */
import { Zap } from 'lucide-react'
import { useTranslation } from '../../hooks/useTranslation'

interface QuickTemplate {
  name: string
  preset: Record<string, string>
}

interface QuickTemplatesProps {
  templates: QuickTemplate[]
  onApply: (template: QuickTemplate) => void
}

export function QuickTemplates({ templates, onApply }: QuickTemplatesProps) {
  const { t } = useTranslation()

  if (templates.length === 0) return null

  return (
    <div className="glass rounded-lg p-4">
      <h3 className="text-sm font-semibold text-text-secondary mb-3 flex items-center gap-2">
        <Zap size={16} className="text-accent" />
        {t('promptBuilder.quickTemplates')}
      </h3>
      <div className="flex flex-wrap gap-2">
        {templates.map((template, idx) => (
          <button
            key={idx}
            onClick={() => onApply(template)}
            className="px-3 py-1.5 bg-bg-elevated hover:bg-bg-surface
                       border border-border-subtle hover:border-primary/50
                       rounded-md text-sm text-text-secondary hover:text-text-primary
                       transition-all duration-200"
          >
            {template.name}
          </button>
        ))}
      </div>
    </div>
  )
}

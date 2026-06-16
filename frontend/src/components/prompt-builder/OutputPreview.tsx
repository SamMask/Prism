/**
 * OutputPreview - Display generated prompt output
 */
import { Copy, Check, FileJson, AlignLeft, BookOpen, Wand2 } from 'lucide-react'
import { Button } from '../ui/Button'
import { useTranslation } from '../../hooks/useTranslation'

interface OutputPreviewProps {
  textOutput: string
  narrativeOutput: string
  jsonOutput: string
  negativePrompt: string
  outputMode: 'text' | 'narrative' | 'json'
  onModeChange: (mode: 'text' | 'narrative' | 'json') => void
  onCopy: () => void
  onOptimize: () => void
  copySuccess: boolean
}

export function OutputPreview({
  textOutput,
  narrativeOutput,
  jsonOutput,
  negativePrompt,
  outputMode,
  onModeChange,
  onCopy,
  onOptimize,
  copySuccess
}: OutputPreviewProps) {
  const { t } = useTranslation()

  const getCurrentOutput = () => {
    switch (outputMode) {
      case 'narrative':
        return narrativeOutput
      case 'json':
        return jsonOutput
      default:
        return textOutput
    }
  }

  const modes = [
    { key: 'text' as const, icon: AlignLeft, label: t('promptBuilder.output.textMode') },
    { key: 'narrative' as const, icon: BookOpen, label: t('promptBuilder.output.narrativeMode') },
    { key: 'json' as const, icon: FileJson, label: 'JSON' },
  ]

  return (
    <div className="glass rounded-lg p-4 sm:p-5 h-full flex flex-col">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h2 className="text-lg font-semibold text-text-primary">{t('promptBuilder.output.title')}</h2>
        
        {/* Mode Tabs */}
        <div className="flex gap-1 bg-bg-elevated rounded-lg p-1">
          {modes.map(({ key, icon: Icon, label }) => (
            <button
              key={key}
              onClick={() => onModeChange(key)}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-1.5
                ${outputMode === key 
                  ? 'bg-primary text-white' 
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-surface'}`}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Output Content */}
      <div className="flex-1 min-h-[18rem] bg-bg-elevated rounded-lg p-4 overflow-auto mb-4" data-testid="prompt-output-preview">
        {outputMode === 'json' ? (
          <pre className="text-sm text-text-primary font-mono whitespace-pre-wrap">
            {getCurrentOutput() || t('promptBuilder.output.emptyJson')}
          </pre>
        ) : (
          <p className="text-text-primary whitespace-pre-wrap leading-relaxed">
            {getCurrentOutput() || t('promptBuilder.output.emptyText')}
          </p>
        )}
        
        {/* Negative Prompt */}
        {negativePrompt && outputMode !== 'json' && (
          <div className="mt-4 pt-4 border-t border-border-subtle">
            <p className="text-text-muted text-sm mb-1">Negative:</p>
            <p className="text-text-secondary text-sm">{negativePrompt}</p>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <Button
          onClick={onOptimize}
          variant="secondary"
          className="flex-1 flex items-center justify-center gap-2"
          disabled={!getCurrentOutput() || outputMode === 'json'}
          title={t('promptBuilder.output.optimizeTitle')}
        >
          <Wand2 size={18} />
          {t('promptBuilder.output.optimize')}
        </Button>

        <Button
          onClick={onCopy}
          variant={copySuccess ? 'ghost' : 'primary'}
          className="flex-[2] flex items-center justify-center gap-2"
          disabled={!getCurrentOutput()}
        >
          {copySuccess ? (
            <>
              <Check size={18} />
              {t('promptBuilder.output.copied')}
            </>
          ) : (
            <>
              <Copy size={18} />
              {t('promptBuilder.output.copy')}
            </>
          )}
        </Button>
      </div>
    </div>
  )
}

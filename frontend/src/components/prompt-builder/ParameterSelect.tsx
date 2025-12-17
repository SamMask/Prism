/**
 * ParameterSelect - Reusable dropdown for prompt parameters
 */
import { ChevronDown } from 'lucide-react'

interface PromptOption {
  display: string
  displayEN?: string
  output: string
}

interface ParameterSelectProps {
  label: string
  value: string
  options: (string | PromptOption)[]
  onChange: (value: string) => void
  weight?: number
  onWeightChange?: (value: number) => void
  showWeight?: boolean
  placeholder?: string
}

const getOptOutput = (opt: string | PromptOption): string => {
  if (typeof opt === 'string') return opt
  return opt?.output || opt?.display || ''
}

const getOptDisplay = (opt: string | PromptOption): string => {
  if (typeof opt === 'string') return opt
  return opt?.display || opt?.output || ''
}

export function ParameterSelect({
  label,
  value,
  options,
  onChange,
  weight = 1.0,
  onWeightChange,
  showWeight = false,
  placeholder = '選擇...'
}: ParameterSelectProps) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium text-text-secondary">{label}</label>
      <div className="flex gap-2">
        <div className="relative flex-1">
          <select
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full bg-bg-elevated border border-border-subtle rounded-lg px-3 py-2 
                       text-text-primary appearance-none cursor-pointer
                       focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary
                       transition-colors"
          >
            <option value="">{placeholder}</option>
            {options.map((opt, idx) => (
              <option key={idx} value={getOptOutput(opt)}>
                {getOptDisplay(opt)}
              </option>
            ))}
          </select>
          <ChevronDown 
            size={16} 
            className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" 
          />
        </div>
        
        {showWeight && onWeightChange && (
          <input
            type="number"
            min="0.1"
            max="2.0"
            step="0.1"
            value={weight}
            onChange={(e) => onWeightChange(parseFloat(e.target.value) || 1.0)}
            className="w-16 bg-bg-elevated border border-border-subtle rounded-lg px-2 py-2 
                       text-text-primary text-center text-sm
                       focus:outline-none focus:ring-2 focus:ring-primary/50"
            title="權重 (0.1 - 2.0)"
          />
        )}
      </div>
    </div>
  )
}

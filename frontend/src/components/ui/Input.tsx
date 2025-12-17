import { InputHTMLAttributes, forwardRef } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = '', label, error, id, ...props }, ref) => {
    return (
      <div className="space-y-1.5">
        {label && (
          <label
            htmlFor={id}
            className="block text-sm font-medium text-text-secondary"
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={id}
          className={`
            w-full px-3 py-2.5 rounded-lg
            bg-bg-elevated border border-border-default
            text-text-primary placeholder-text-muted
            focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/50
            transition-colors duration-200
            ${error ? 'border-danger focus:border-danger focus:ring-danger/50' : ''}
            ${className}
          `}
          {...props}
        />
        {error && (
          <p className="text-sm text-danger">{error}</p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'

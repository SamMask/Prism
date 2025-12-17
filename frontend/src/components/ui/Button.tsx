import { ButtonHTMLAttributes, forwardRef } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = '', variant = 'secondary', size = 'md', children, ...props }, ref) => {
    const baseStyles = `
      inline-flex items-center justify-center gap-2
      font-medium rounded-lg transition-all duration-200
      focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-bg-base
      disabled:opacity-50 disabled:cursor-not-allowed
    `

    const variants = {
      primary: `
        bg-primary text-white
        hover:bg-primary-hover
        focus:ring-primary
      `,
      secondary: `
        bg-bg-elevated text-text-primary
        border border-border-default
        hover:bg-bg-hover hover:border-border-default
        focus:ring-primary
      `,
      ghost: `
        bg-transparent text-text-secondary
        hover:bg-bg-hover hover:text-text-primary
        focus:ring-primary
      `,
      danger: `
        bg-danger text-white
        hover:bg-red-600
        focus:ring-danger
      `,
    }

    const sizes = {
      sm: 'px-2.5 py-1.5 text-sm',
      md: 'px-4 py-2 text-sm',
      lg: 'px-6 py-3 text-base',
    }

    return (
      <button
        ref={ref}
        className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
        {...props}
      >
        {children}
      </button>
    )
  }
)

Button.displayName = 'Button'

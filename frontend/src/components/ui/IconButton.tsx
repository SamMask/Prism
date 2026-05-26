import React from 'react'

export type IconButtonSize = 'xs' | 'sm' | 'md'
export type IconButtonVariant = 'default' | 'danger' | 'success' | 'danger-solid'

const PADDING: Record<IconButtonSize, string> = {
  xs: 'p-0.5',
  sm: 'p-1.5',
  md: 'p-2',
}

const ROUNDED: Record<IconButtonSize, string> = {
  xs: 'rounded',
  sm: 'rounded',
  md: 'rounded-lg',
}

const COLOR: Record<IconButtonVariant, string> = {
  'default':      'text-text-muted hover:text-text-primary hover:bg-bg-hover',
  'danger':       'text-text-muted hover:text-danger hover:bg-danger/10',
  'success':      'text-success hover:bg-success/20',
  'danger-solid': 'text-danger hover:bg-danger/20',
}

interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  size?: IconButtonSize
  variant?: IconButtonVariant
}

export function IconButton({
  size = 'md',
  variant = 'default',
  className = '',
  ...props
}: IconButtonProps) {
  return (
    <button
      type="button"
      className={`${PADDING[size]} ${ROUNDED[size]} ${COLOR[variant]} transition-colors ${className}`}
      {...props}
    />
  )
}

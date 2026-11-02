import { Loader2 } from 'lucide-react'
import { forwardRef } from 'react'
import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { cn } from '../../lib/cn'

export type ButtonVariant =
  | 'primary'
  | 'secondary'
  | 'ghost'
  | 'danger'

export type ButtonSize = 'sm' | 'md' | 'lg'

const variants: Record<ButtonVariant, string> = {
  primary:
    'border border-accent/70 bg-accent text-[#03130d] shadow-[0_0_24px_-12px_rgba(52,211,153,0.8)] hover:bg-emerald-300',
  secondary:
    'border border-line-strong bg-panel-raised text-ink hover:border-accent/40 hover:bg-[#16212d]',
  ghost:
    'border border-transparent text-muted hover:bg-panel-raised hover:text-ink',
  danger:
    'border border-danger/30 bg-danger/10 text-rose-300 hover:bg-danger/20 hover:text-rose-200',
}

const sizes: Record<ButtonSize, string> = {
  sm: 'h-8 gap-1.5 px-3 text-xs',
  md: 'h-10 gap-2 px-4 text-sm',
  lg: 'h-11 gap-2 px-5 text-sm',
}

export function buttonStyles(
  variant: ButtonVariant = 'primary',
  size: ButtonSize = 'md',
  className?: string,
): string {
  return cn(
    'inline-flex shrink-0 items-center justify-center rounded-lg font-medium transition-colors duration-150 disabled:pointer-events-none disabled:opacity-50',
    variants[variant],
    sizes[size],
    className,
  )
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  children: ReactNode
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      disabled,
      className,
      children,
      type = 'button',
      ...props
    },
    ref,
  ) {
    return (
      <button
        ref={ref}
        type={type}
        className={buttonStyles(variant, size, className)}
        disabled={disabled || loading}
        {...props}
      >
        {loading ? <Loader2 className="size-4 animate-spin" /> : null}
        {children}
      </button>
    )
  },
)

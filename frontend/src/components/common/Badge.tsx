import type { ReactNode } from 'react'

import { cn } from '../../lib/cn'

export type BadgeVariant =
  | 'neutral'
  | 'accent'
  | 'danger'
  | 'warning'
  | 'info'

const variants: Record<BadgeVariant, string> = {
  neutral: 'border-line-strong bg-panel-raised text-muted',
  accent: 'border-accent/30 bg-accent/10 text-emerald-300',
  danger: 'border-danger/30 bg-danger/10 text-rose-300',
  warning: 'border-warning/30 bg-warning/10 text-amber-300',
  info: 'border-info/30 bg-info/10 text-sky-300',
}

const dots: Record<BadgeVariant, string> = {
  neutral: 'bg-slate-400',
  accent: 'bg-emerald-400',
  danger: 'bg-rose-400',
  warning: 'bg-amber-400',
  info: 'bg-sky-400',
}

interface BadgeProps {
  children: ReactNode
  variant?: BadgeVariant
  dot?: boolean
  className?: string
}

export function Badge({
  children,
  variant = 'neutral',
  dot = false,
  className,
}: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium tracking-wide',
        variants[variant],
        className,
      )}
    >
      {dot ? (
        <span className={cn('size-1.5 rounded-full', dots[variant])} />
      ) : null}
      {children}
    </span>
  )
}

import type { LucideIcon } from 'lucide-react'
import type { HTMLAttributes, ReactNode } from 'react'

import { cn } from '../../lib/cn'

interface PanelProps extends HTMLAttributes<HTMLElement> {
  children: ReactNode
}

export function Panel({ className, children, ...props }: PanelProps) {
  return (
    <section
      className={cn(
        'rounded-xl border border-line bg-panel/90 shadow-[0_1px_0_rgba(255,255,255,0.02)_inset]',
        className,
      )}
      {...props}
    >
      {children}
    </section>
  )
}

interface PanelHeaderProps {
  title: string
  description?: string
  icon?: LucideIcon
  action?: ReactNode
  className?: string
}

export function PanelHeader({
  title,
  description,
  icon: Icon,
  action,
  className,
}: PanelHeaderProps) {
  return (
    <div
      className={cn(
        'flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-4 sm:flex-nowrap',
        className,
      )}
    >
      <div className="flex min-w-0 items-start gap-3">
        {Icon ? (
          <span className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-lg border border-line bg-canvas-raised text-emerald-300">
            <Icon className="size-4" aria-hidden="true" />
          </span>
        ) : null}
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-ink">{title}</h2>
          {description ? (
            <p className="mt-1 text-xs leading-5 text-muted">{description}</p>
          ) : null}
        </div>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  )
}

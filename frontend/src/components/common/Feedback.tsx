import {
  AlertTriangle,
  CheckCircle2,
  Info,
  Loader2,
  RefreshCw,
  XCircle,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

import { getErrorMessage } from '../../services/api'
import { cn } from '../../lib/cn'
import { Button } from './Button'
import { Panel } from './Panel'

interface LoadingPanelProps {
  label?: string
  rows?: number
  className?: string
}

export function LoadingPanel({
  label = 'Loading data',
  rows = 3,
  className,
}: LoadingPanelProps) {
  return (
    <Panel className={cn('p-5', className)} aria-busy="true">
      <div className="flex items-center gap-2 text-xs text-muted">
        <Loader2 className="size-3.5 animate-spin text-emerald-400" />
        {label}
      </div>
      <div className="mt-5 space-y-3">
        {Array.from({ length: rows }).map((_, index) => (
          <div
            key={index}
            className="h-3 animate-pulse rounded-full bg-panel-raised"
            style={{ width: `${88 - index * 13}%` }}
          />
        ))}
      </div>
    </Panel>
  )
}

interface ErrorPanelProps {
  error: unknown
  title?: string
  onRetry?: () => void
  className?: string
}

export function ErrorPanel({
  error,
  title = 'Unable to load this view',
  onRetry,
  className,
}: ErrorPanelProps) {
  return (
    <Panel
      className={cn('border-danger/25 bg-danger/[0.04] p-5', className)}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg border border-danger/25 bg-danger/10 text-rose-300">
          <AlertTriangle className="size-4" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold text-ink">{title}</h2>
          <p className="mt-1 text-sm leading-6 text-muted">
            {getErrorMessage(error)}
          </p>
          {onRetry ? (
            <Button
              variant="secondary"
              size="sm"
              className="mt-4"
              onClick={onRetry}
            >
              <RefreshCw className="size-3.5" />
              Try again
            </Button>
          ) : null}
        </div>
      </div>
    </Panel>
  )
}

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description: string
  action?: ReactNode
  className?: string
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center px-6 py-14 text-center',
        className,
      )}
    >
      <span className="flex size-12 items-center justify-center rounded-xl border border-line bg-canvas-raised text-emerald-300">
        <Icon className="size-5" aria-hidden="true" />
      </span>
      <h2 className="mt-4 text-base font-semibold text-ink">{title}</h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-muted">
        {description}
      </p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  )
}

type NoticeVariant = 'info' | 'success' | 'warning' | 'error'

const noticeStyles: Record<
  NoticeVariant,
  { container: string; icon: string; Icon: LucideIcon }
> = {
  info: {
    container: 'border-info/25 bg-info/[0.06]',
    icon: 'text-sky-300',
    Icon: Info,
  },
  success: {
    container: 'border-accent/25 bg-accent/[0.06]',
    icon: 'text-emerald-300',
    Icon: CheckCircle2,
  },
  warning: {
    container: 'border-warning/25 bg-warning/[0.06]',
    icon: 'text-amber-300',
    Icon: AlertTriangle,
  },
  error: {
    container: 'border-danger/25 bg-danger/[0.06]',
    icon: 'text-rose-300',
    Icon: XCircle,
  },
}

interface NoticeProps {
  variant?: NoticeVariant
  title?: string
  children: ReactNode
  action?: ReactNode
  className?: string
}

export function Notice({
  variant = 'info',
  title,
  children,
  action,
  className,
}: NoticeProps) {
  const style = noticeStyles[variant]
  const Icon = style.Icon

  return (
    <div
      className={cn(
        'rounded-lg border px-4 py-3',
        style.container,
        className,
      )}
      role={variant === 'error' ? 'alert' : 'status'}
    >
      <div className="flex items-start gap-3">
        <Icon
          className={cn('mt-0.5 size-4 shrink-0', style.icon)}
          aria-hidden="true"
        />
        <div className="min-w-0 flex-1 text-sm leading-6 text-slate-300">
          {title ? (
            <p className="font-semibold text-ink">{title}</p>
          ) : null}
          <div className={title ? 'mt-1' : undefined}>{children}</div>
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
    </div>
  )
}

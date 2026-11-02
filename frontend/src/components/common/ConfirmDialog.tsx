import { AlertTriangle, X } from 'lucide-react'
import { useEffect, useId, useRef } from 'react'
import type { ReactNode } from 'react'

import { cn } from '../../lib/cn'
import { Button } from './Button'

interface ConfirmDialogProps {
  open: boolean
  title: string
  description: ReactNode
  confirmLabel?: string
  cancelLabel?: string
  loading?: boolean
  destructive?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  loading = false,
  destructive = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const titleId = useId()
  const descriptionId = useId()
  const cancelRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) {
      return
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !loading) {
        onCancel()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    cancelRef.current?.focus()

    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [loading, onCancel, open])

  if (!open) {
    return null
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-[2px]"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !loading) {
          onCancel()
        }
      }}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descriptionId}
        className="animate-fade-in w-full max-w-md rounded-xl border border-line-strong bg-panel shadow-2xl shadow-black/40"
      >
        <div className="flex items-start gap-3 border-b border-line px-5 py-4">
          <span
            className={cn(
              'flex size-9 shrink-0 items-center justify-center rounded-lg border',
              destructive
                ? 'border-danger/30 bg-danger/10 text-rose-300'
                : 'border-accent/30 bg-accent/10 text-emerald-300',
            )}
          >
            <AlertTriangle className="size-4" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <h2 id={titleId} className="text-sm font-semibold text-ink">
              {title}
            </h2>
            <div
              id={descriptionId}
              className="mt-1 text-sm leading-6 text-muted"
            >
              {description}
            </div>
          </div>
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="rounded-md p-1 text-faint transition-colors hover:bg-panel-raised hover:text-ink disabled:opacity-50"
            aria-label="Close dialog"
          >
            <X className="size-4" />
          </button>
        </div>
        <div className="flex items-center justify-end gap-2 px-5 py-4">
          <Button
            ref={cancelRef}
            variant="ghost"
            size="sm"
            onClick={onCancel}
            disabled={loading}
          >
            {cancelLabel}
          </Button>
          <Button
            variant={destructive ? 'danger' : 'primary'}
            size="sm"
            onClick={onConfirm}
            loading={loading}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  )
}

import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

import { Panel } from '../common/Panel'

interface StatCardProps {
  label: string
  value: ReactNode
  detail: string
  icon: LucideIcon
}

export function StatCard({
  label,
  value,
  detail,
  icon: Icon,
}: StatCardProps) {
  return (
    <Panel className="relative overflow-hidden p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-[0.12em] text-faint">
            {label}
          </p>
          <p className="mt-3 text-2xl font-semibold tracking-tight text-ink">
            {value}
          </p>
          <p className="mt-1.5 text-xs text-muted">{detail}</p>
        </div>
        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-line bg-canvas-raised text-emerald-300">
          <Icon className="size-4" aria-hidden="true" />
        </span>
      </div>
    </Panel>
  )
}

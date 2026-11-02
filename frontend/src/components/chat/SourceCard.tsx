import { ArrowUpRight } from 'lucide-react'
import { Link } from 'react-router-dom'

import type { ChatSource } from '../../types/api'

interface SourceCardProps {
  source: ChatSource
}

export function SourceCard({ source }: SourceCardProps) {
  return (
    <Link
      to={`/conversations/${source.conversation_id}`}
      className="group rounded-lg border border-line bg-canvas/50 p-3 transition-colors hover:border-accent/30 hover:bg-canvas"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="inline-flex min-w-5 items-center justify-center rounded border border-accent/25 bg-accent/10 px-1 py-0.5 font-mono text-[10px] text-emerald-300">
          {source.index}
        </span>
        <ArrowUpRight
          className="size-3.5 text-faint transition-colors group-hover:text-emerald-300"
          aria-hidden="true"
        />
      </div>
      <p className="mt-2 line-clamp-1 text-xs font-medium text-ink">
        {source.conversation_title}
      </p>
      <p className="mt-1 text-[10px] uppercase tracking-[0.1em] text-faint">
        {source.role} · message {source.message_position + 1} · chunk{' '}
        {source.chunk_index + 1}
      </p>
      <p className="mt-2 line-clamp-3 text-xs leading-5 text-muted">
        {source.text}
      </p>
    </Link>
  )
}

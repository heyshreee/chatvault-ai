import {
  Activity,
  ArrowRight,
  ChevronRight,
  Clock3,
  Database,
  Import,
  Layers,
  Library,
  MessageSquare,
  MessagesSquare,
  Sparkles,
} from 'lucide-react'
import { Link } from 'react-router-dom'

import { Badge } from '../components/common/Badge'
import { buttonStyles } from '../components/common/Button'
import {
  EmptyState,
  ErrorPanel,
  LoadingPanel,
  Notice,
} from '../components/common/Feedback'
import { PageHeader } from '../components/common/PageHeader'
import { Panel, PanelHeader } from '../components/common/Panel'
import { StatCard } from '../components/dashboard/StatCard'
import { useIndexStatus, useStats } from '../hooks/queries'
import {
  formatDate,
  formatNumber,
  formatPercent,
  pluralize,
} from '../lib/format'

export function Dashboard() {
  const statsQuery = useStats()
  const indexQuery = useIndexStatus()

  const stats = statsQuery.data
  const index = indexQuery.data
  const total = stats?.conversations_total ?? 0
  const indexed = stats?.indexed_conversations ?? 0
  const coverage = total > 0 ? (indexed / total) * 100 : 0

  const indexHealthy =
    index?.vector_store_available === true && !index.rebuild_required

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Overview"
        title="Dashboard"
        description="Your local conversation knowledge base at a glance. Every number comes from SQLite and the ChromaDB index."
        actions={
          <>
            <Link
              to="/import"
              className={buttonStyles('primary', 'md')}
            >
              <Import className="size-4" aria-hidden="true" />
              Import conversation
            </Link>
            <Link
              to="/chat"
              className={buttonStyles('secondary', 'md')}
            >
              <Sparkles className="size-4" aria-hidden="true" />
              Ask AI
            </Link>
          </>
        }
      />

      {statsQuery.isLoading ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <LoadingPanel key={index} rows={2} label="Loading metric" />
            ))}
          </div>
          <div className="grid gap-6 xl:grid-cols-[1.55fr_1fr]">
            <LoadingPanel rows={5} label="Loading recent imports" />
            <LoadingPanel rows={4} label="Loading index health" />
          </div>
        </>
      ) : statsQuery.isError ? (
        <ErrorPanel
          error={statsQuery.error}
          title="Unable to load dashboard statistics"
          onRetry={() => void statsQuery.refetch()}
        />
      ) : stats ? (
        <>
          {total === 0 ? (
            <Panel className="border-accent/20 bg-gradient-to-br from-accent/[0.06] via-panel to-panel p-6">
              <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
                <div className="max-w-xl">
                  <Badge variant="accent" dot>
                    New workspace
                  </Badge>
                  <h2 className="mt-3 text-xl font-semibold tracking-tight text-ink">
                    Start your local knowledge base
                  </h2>
                  <p className="mt-2 text-sm leading-6 text-muted">
                    Import a shared ChatGPT conversation, let ChatVault index
                    it with Ollama, then ask questions with cited sources.
                    Nothing leaves this machine.
                  </p>
                </div>
                <Link
                  to="/import"
                  className={buttonStyles('primary', 'md')}
                >
                  <Import className="size-4" aria-hidden="true" />
                  Import your first conversation
                </Link>
              </div>

              <div className="mt-6 grid gap-3 sm:grid-cols-3">
                {[
                  {
                    step: '01',
                    title: 'Import a shared link',
                    detail: 'Paste a public ChatGPT share URL.',
                  },
                  {
                    step: '02',
                    title: 'Build the index',
                    detail: 'Messages are embedded locally after import.',
                  },
                  {
                    step: '03',
                    title: 'Ask with citations',
                    detail: 'Answers cite the exact source chunks.',
                  },
                ].map((item) => (
                  <div
                    key={item.step}
                    className="rounded-lg border border-line bg-canvas/40 p-4"
                  >
                    <span className="font-mono text-[10px] tracking-[0.18em] text-emerald-400/80">
                      {item.step}
                    </span>
                    <p className="mt-2 text-sm font-medium text-ink">
                      {item.title}
                    </p>
                    <p className="mt-1 text-xs leading-5 text-faint">
                      {item.detail}
                    </p>
                  </div>
                ))}
              </div>
            </Panel>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Conversations"
              value={formatNumber(stats.conversations_total)}
              detail={
                stats.not_indexed_conversations > 0
                  ? `${formatNumber(stats.not_indexed_conversations)} awaiting indexing`
                  : 'Every conversation is indexed'
              }
              icon={MessagesSquare}
            />
            <StatCard
              label="Messages"
              value={formatNumber(stats.messages_total)}
              detail="Stored in the local SQLite database"
              icon={MessageSquare}
            />
            <StatCard
              label="Indexed conversations"
              value={formatNumber(stats.indexed_conversations)}
              detail={`${formatPercent(coverage)} of your library`}
              icon={Database}
            />
            <StatCard
              label="Indexed chunks"
              value={formatNumber(stats.chunks_indexed)}
              detail={
                stats.vectors == null
                  ? 'Vector store unavailable'
                  : `${formatNumber(stats.vectors)} vectors stored`
              }
              icon={Layers}
            />
          </div>

          <div className="grid items-start gap-6 xl:grid-cols-[1.55fr_1fr]">
            <Panel>
              <PanelHeader
                title="Recent imports"
                description="The five most recently stored conversations."
                icon={Clock3}
                action={
                  <Link
                    to="/library"
                    className="inline-flex items-center gap-1 text-xs font-medium text-emerald-300 transition-colors hover:text-emerald-200"
                  >
                    View library
                    <ArrowRight className="size-3.5" aria-hidden="true" />
                  </Link>
                }
              />

              {stats.recent_imports.length === 0 ? (
                <EmptyState
                  icon={Library}
                  title="No conversations imported yet"
                  description="Import a public ChatGPT share link to populate the library and build your first searchable index."
                  action={
                    <Link
                      to="/import"
                      className={buttonStyles('primary', 'sm')}
                    >
                      <Import className="size-3.5" aria-hidden="true" />
                      Import conversation
                    </Link>
                  }
                />
              ) : (
                <ul className="divide-y divide-line">
                  {stats.recent_imports.map((conversation) => (
                    <li key={conversation.conversation_id}>
                      <Link
                        to={`/conversations/${conversation.conversation_id}`}
                        className="group flex items-center gap-4 px-5 py-4 transition-colors hover:bg-panel-raised/50"
                      >
                        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-line bg-canvas-raised text-faint transition-colors group-hover:text-emerald-300">
                          <MessageSquare
                            className="size-4"
                            aria-hidden="true"
                          />
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-ink">
                            {conversation.title}
                          </p>
                          <p className="mt-1 text-xs text-faint">
                            {pluralize(conversation.message_count, 'message')}
                            <span className="mx-1.5 text-line-strong">/</span>
                            {formatDate(conversation.created_at)}
                          </p>
                        </div>
                        <ChevronRight
                          className="size-4 shrink-0 text-faint transition-transform group-hover:translate-x-0.5 group-hover:text-muted"
                          aria-hidden="true"
                        />
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>

            <Panel>
              <PanelHeader
                title="Index health"
                description="Derived ChromaDB vectors, rebuilt from SQLite."
                icon={Activity}
                action={
                  index ? (
                    <Badge
                      variant={
                        !index.vector_store_available
                          ? 'danger'
                          : index.rebuild_required
                            ? 'warning'
                            : 'accent'
                      }
                      dot
                    >
                      {!index.vector_store_available
                        ? 'Unavailable'
                        : index.rebuild_required
                          ? 'Rebuild required'
                          : 'Healthy'}
                    </Badge>
                  ) : null
                }
              />

              {indexQuery.isLoading ? (
                <div className="p-5">
                  <LoadingPanel rows={4} label="Reading index status" />
                </div>
              ) : indexQuery.isError ? (
                <div className="p-5">
                  <ErrorPanel
                    error={indexQuery.error}
                    title="Unable to read the index"
                    onRetry={() => void indexQuery.refetch()}
                  />
                </div>
              ) : index ? (
                <div className="space-y-5 p-5">
                  <div>
                    <div className="flex items-end justify-between gap-3">
                      <p className="text-xs font-medium uppercase tracking-[0.12em] text-faint">
                        Coverage
                      </p>
                      <p className="text-sm font-semibold text-ink">
                        {formatPercent(coverage)}
                      </p>
                    </div>
                    <div
                      className="mt-2 h-2 overflow-hidden rounded-full bg-canvas"
                      role="progressbar"
                      aria-valuenow={Math.round(coverage)}
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-label="Conversation index coverage"
                    >
                      <div
                        className="h-full rounded-full bg-accent transition-[width] duration-500"
                        style={{
                          width: `${Math.min(100, Math.max(0, coverage))}%`,
                        }}
                      />
                    </div>
                    <p className="mt-2 text-xs text-faint">
                      {formatNumber(index.conversations.indexed)} of{' '}
                      {formatNumber(index.conversations.total)} conversations
                      indexed
                    </p>
                  </div>

                  <dl className="grid grid-cols-2 gap-x-4 gap-y-4 text-sm">
                    <div>
                      <dt className="text-xs text-faint">Vectors</dt>
                      <dd className="mt-1 font-medium text-ink">
                        {index.vectors == null
                          ? 'Unavailable'
                          : formatNumber(index.vectors)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-faint">Chunks recorded</dt>
                      <dd className="mt-1 font-medium text-ink">
                        {formatNumber(index.chunks_recorded)}
                      </dd>
                    </div>
                    <div className="col-span-2">
                      <dt className="text-xs text-faint">Embedding model</dt>
                      <dd className="mt-1 truncate font-mono text-xs text-slate-300">
                        {index.embedding_model}
                      </dd>
                    </div>
                    <div className="col-span-2">
                      <dt className="text-xs text-faint">Collection</dt>
                      <dd className="mt-1 truncate font-mono text-xs text-slate-300">
                        {index.collection}
                      </dd>
                    </div>
                  </dl>

                  {!index.vector_store_available ? (
                    <Notice variant="error" title="Vector store unavailable">
                      {index.vector_store_error ??
                        'ChromaDB could not be reached.'}
                    </Notice>
                  ) : index.rebuild_required ? (
                    <Notice
                      variant="warning"
                      title="Index rebuild required"
                    >
                      {index.rebuild_reason ??
                        'The index is out of date with the current configuration.'}
                    </Notice>
                  ) : indexHealthy ? (
                    <div className="flex items-center gap-2 rounded-lg border border-accent/20 bg-accent/[0.04] px-3 py-2 text-xs text-emerald-200">
                      <span className="size-1.5 rounded-full bg-emerald-400" />
                      Index configuration matches the stored vectors.
                    </div>
                  ) : null}

                  <Link
                    to="/settings"
                    className={buttonStyles('secondary', 'sm', 'w-full')}
                  >
                    Index settings
                    <ArrowRight className="size-3.5" aria-hidden="true" />
                  </Link>
                </div>
              ) : null}
            </Panel>
          </div>

          {stats.failed_conversations > 0 ||
          stats.indexing_conversations > 0 ? (
            <Notice
              variant={
                stats.failed_conversations > 0 ? 'warning' : 'info'
              }
              title="Index activity in progress"
            >
              {stats.indexing_conversations > 0
                ? `${formatNumber(stats.indexing_conversations)} conversation(s) currently indexing. `
                : ''}
              {stats.failed_conversations > 0
                ? `${formatNumber(stats.failed_conversations)} conversation(s) failed to index. Rebuild the index from Settings.`
                : ''}
            </Notice>
          ) : null}
        </>
      ) : null}
    </div>
  )
}

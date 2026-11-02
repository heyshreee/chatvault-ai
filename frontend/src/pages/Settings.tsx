import {
  Activity,
  CheckCircle2,
  Cpu,
  Database,
  HardDrive,
  Layers,
  MessageSquareText,
  RefreshCw,
  Server,
  ShieldCheck,
  Wrench,
} from 'lucide-react'
import { useState } from 'react'

import { Badge } from '../components/common/Badge'
import { Button } from '../components/common/Button'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import {
  ErrorPanel,
  LoadingPanel,
  Notice,
} from '../components/common/Feedback'
import { PageHeader } from '../components/common/PageHeader'
import { Panel, PanelHeader } from '../components/common/Panel'
import {
  useIndexStatus,
  useModelStatus,
  useRebuildIndex,
} from '../hooks/queries'
import {
  formatBytes,
  formatDate,
  formatDateTime,
  formatNumber,
  formatPercent,
} from '../lib/format'
import { cn } from '../lib/cn'
import { getErrorMessage } from '../services/api'
import type { RebuildIndexResponse } from '../types/api'

function isInstalled(configured: string, installed: string): boolean {
  return installed === configured || installed.startsWith(`${configured}:`)
}

export function Settings() {
  const modelQuery = useModelStatus()
  const indexQuery = useIndexStatus()
  const rebuildMutation = useRebuildIndex()
  const [rebuildOpen, setRebuildOpen] = useState(false)
  const [rebuildResult, setRebuildResult] =
    useState<RebuildIndexResponse | null>(null)

  const model = modelQuery.data
  const indexDetails = indexQuery.data
  const summary = model?.index
  const coverage =
    summary && summary.total > 0
      ? (summary.indexed / summary.total) * 100
      : 0

  const refresh = () => {
    void modelQuery.refetch()
    void indexQuery.refetch()
  }

  const confirmRebuild = () => {
    setRebuildResult(null)
    rebuildMutation.mutate(undefined, {
      onSuccess: (result) => {
        setRebuildOpen(false)
        setRebuildResult(result)
      },
      onError: () => {
        setRebuildOpen(false)
      },
    })
  }

  const updatedLabel = modelQuery.dataUpdatedAt
    ? new Date(modelQuery.dataUpdatedAt).toLocaleTimeString([], {
        hour: 'numeric',
        minute: '2-digit',
      })
    : null

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="System"
        title="Settings"
        description="Inspect the local Ollama connection, configured models, ChromaDB vector store, SQLite database, and index state."
        actions={
          <Button
            variant="secondary"
            size="md"
            onClick={refresh}
            loading={
              modelQuery.isFetching || indexQuery.isFetching
            }
          >
            <RefreshCw className="size-4" aria-hidden="true" />
            Refresh status
          </Button>
        }
      />

      {modelQuery.isLoading ? (
        <div className="grid gap-6 xl:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <LoadingPanel key={index} rows={5} label="Checking system status" />
          ))}
        </div>
      ) : modelQuery.isError ? (
        <ErrorPanel
          error={modelQuery.error}
          title="Unable to read system status"
          onRetry={() => void modelQuery.refetch()}
        />
      ) : model ? (
        <>
          <div className="grid items-start gap-6 xl:grid-cols-2">
            <Panel>
              <PanelHeader
                title="Ollama connection"
                description="Local model runtime used for chat and embeddings."
                icon={Server}
                action={
                  <Badge
                    variant={model.ollama.available ? 'accent' : 'danger'}
                    dot
                  >
                    {model.ollama.available ? 'Connected' : 'Unavailable'}
                  </Badge>
                }
              />
              <div className="space-y-4 p-5">
                <div>
                  <p className="text-xs text-faint">Base URL</p>
                  <p className="mt-1 break-all font-mono text-xs text-slate-300">
                    {model.ollama.base_url}
                  </p>
                </div>

                {model.ollama.available ? (
                  <div className="flex items-center gap-2 rounded-lg border border-accent/20 bg-accent/[0.04] px-3 py-2 text-xs text-emerald-200">
                    <CheckCircle2 className="size-3.5" aria-hidden="true" />
                    Ollama responded to the model list request.
                  </div>
                ) : (
                  <Notice variant="error" title="Ollama is not reachable">
                    {model.ollama.error ??
                      'Start Ollama and refresh the status.'}
                    <p className="mt-2 text-xs text-muted">
                      Start the service with{' '}
                      <code className="rounded border border-line bg-canvas px-1.5 py-0.5 font-mono text-[11px] text-emerald-200">
                        ollama serve
                      </code>
                      .
                    </p>
                  </Notice>
                )}

                <dl className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <dt className="text-xs text-faint">Installed models</dt>
                    <dd className="mt-1 font-medium text-ink">
                      {formatNumber(model.installed_models.length)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-faint">Last checked</dt>
                    <dd className="mt-1 font-medium text-ink">
                      {updatedLabel ?? 'Unknown'}
                    </dd>
                  </div>
                </dl>
              </div>
            </Panel>

            <Panel>
              <PanelHeader
                title="Configured models"
                description="Models selected by the backend environment."
                icon={Cpu}
              />
              <div className="divide-y divide-line">
                <div className="flex items-start gap-3 p-5">
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-line bg-canvas-raised text-emerald-300">
                    <MessageSquareText
                      className="size-4"
                      aria-hidden="true"
                    />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-medium text-ink">
                        Chat generation
                      </p>
                      <Badge
                        variant={
                          model.chat_model.available
                            ? 'accent'
                            : 'danger'
                        }
                        dot
                      >
                        {model.chat_model.available
                          ? 'Available'
                          : 'Missing'}
                      </Badge>
                    </div>
                    <p className="mt-1 break-all font-mono text-xs text-slate-300">
                      {model.chat_model.name}
                    </p>
                    <p className="mt-2 text-xs leading-5 text-faint">
                      Used by AI Chat after retrieval. If missing, run{' '}
                      <code className="text-emerald-200">
                        ollama pull {model.chat_model.name}
                      </code>
                      .
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-5">
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-line bg-canvas-raised text-emerald-300">
                    <Database
                      className="size-4"
                      aria-hidden="true"
                    />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-medium text-ink">
                        Embeddings
                      </p>
                      <Badge
                        variant={
                          model.embedding_model.available
                            ? 'accent'
                            : 'danger'
                        }
                        dot
                      >
                        {model.embedding_model.available
                          ? 'Available'
                          : 'Missing'}
                      </Badge>
                    </div>
                    <p className="mt-1 break-all font-mono text-xs text-slate-300">
                      {model.embedding_model.name}
                    </p>
                    <p className="mt-2 text-xs leading-5 text-faint">
                      Used for indexing and semantic retrieval. If missing,
                      run{' '}
                      <code className="text-emerald-200">
                        ollama pull {model.embedding_model.name}
                      </code>
                      .
                    </p>
                  </div>
                </div>
              </div>
            </Panel>

            <Panel>
              <PanelHeader
                title="ChromaDB vector store"
                description="Derived index stored on disk and rebuildable from SQLite."
                icon={Database}
                action={
                  <Badge
                    variant={
                      model.vector_store.available
                        ? 'accent'
                        : 'danger'
                    }
                    dot
                  >
                    {model.vector_store.available
                      ? 'Available'
                      : 'Unavailable'}
                  </Badge>
                }
              />
              <div className="space-y-4 p-5">
                <dl className="grid grid-cols-2 gap-4 text-sm">
                  <div className="col-span-2">
                    <dt className="text-xs text-faint">Collection</dt>
                    <dd className="mt-1 break-all font-mono text-xs text-slate-300">
                      {model.vector_store.collection}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-faint">Vectors</dt>
                    <dd className="mt-1 font-medium text-ink">
                      {model.vector_store.vectors == null
                        ? 'Unavailable'
                        : formatNumber(model.vector_store.vectors)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-faint">Dimensions</dt>
                    <dd className="mt-1 font-medium text-ink">
                      {model.vector_store.embedding_dimension == null
                        ? 'Unknown'
                        : formatNumber(
                            model.vector_store.embedding_dimension,
                          )}
                    </dd>
                  </div>
                </dl>

                {model.vector_store.error ? (
                  <Notice variant="error" title="Vector store error">
                    {model.vector_store.error}
                  </Notice>
                ) : (
                  <p className="text-xs leading-5 text-faint">
                    Deleting this directory or rebuilding the index does not
                    delete conversations. SQLite remains the source of truth.
                  </p>
                )}
              </div>
            </Panel>

            <Panel>
              <PanelHeader
                title="SQLite database"
                description="Primary storage for conversations and messages."
                icon={HardDrive}
                action={
                  <Badge variant="accent" dot>
                    Source of truth
                  </Badge>
                }
              />
              <div className="space-y-4 p-5">
                <dl className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <dt className="text-xs text-faint">Engine</dt>
                    <dd className="mt-1 font-medium uppercase text-ink">
                      {model.database.engine}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-faint">Conversations</dt>
                    <dd className="mt-1 font-medium text-ink">
                      {formatNumber(model.database.conversations)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-faint">Messages</dt>
                    <dd className="mt-1 font-medium text-ink">
                      {formatNumber(model.database.messages)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-faint">Indexed chunks</dt>
                    <dd className="mt-1 font-medium text-ink">
                      {formatNumber(model.index.chunks_recorded)}
                    </dd>
                  </div>
                </dl>

                <div className="flex items-start gap-2 rounded-lg border border-line bg-canvas/40 px-3 py-2.5">
                  <ShieldCheck
                    className="mt-0.5 size-3.5 shrink-0 text-emerald-300"
                    aria-hidden="true"
                  />
                  <p className="text-xs leading-5 text-muted">
                    Message text is stored locally. Application logs do not
                    include conversation snippets.
                  </p>
                </div>
              </div>
            </Panel>
          </div>

          <Panel>
            <PanelHeader
              title="Indexing"
              description="Chunking, embedding, and vector coverage details."
              icon={Layers}
              action={
                <Badge
                  variant={
                    !model.vector_store.available
                      ? 'danger'
                      : model.index.rebuild_required
                        ? 'warning'
                        : 'accent'
                  }
                  dot
                >
                  {!model.vector_store.available
                    ? 'Unavailable'
                    : model.index.rebuild_required
                      ? 'Rebuild required'
                      : 'Healthy'}
                </Badge>
              }
            />
            <div className="space-y-5 p-5">
              {indexQuery.isError ? (
                <Notice variant="warning" title="Index status partially available">
                  {getErrorMessage(indexQuery.error)} The summary below still
                  comes from the system status endpoint.
                </Notice>
              ) : null}

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
                  aria-label="Index coverage"
                >
                  <div
                    className="h-full rounded-full bg-accent"
                    style={{
                      width: `${Math.min(100, Math.max(0, coverage))}%`,
                    }}
                  />
                </div>
                <p className="mt-2 text-xs text-faint">
                  {formatNumber(summary?.indexed ?? 0)} of{' '}
                  {formatNumber(summary?.total ?? 0)} conversations indexed
                </p>
              </div>

              <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
                <div>
                  <dt className="text-xs text-faint">Indexed</dt>
                  <dd className="mt-1 font-medium text-ink">
                    {formatNumber(summary?.indexed ?? 0)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-faint">Not indexed</dt>
                  <dd className="mt-1 font-medium text-ink">
                    {formatNumber(summary?.not_indexed ?? 0)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-faint">Failed</dt>
                  <dd
                    className={cn(
                      'mt-1 font-medium',
                      (summary?.failed ?? 0) > 0
                        ? 'text-rose-300'
                        : 'text-ink',
                    )}
                  >
                    {formatNumber(summary?.failed ?? 0)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-faint">Stale</dt>
                  <dd
                    className={cn(
                      'mt-1 font-medium',
                      (summary?.stale ?? 0) > 0
                        ? 'text-amber-300'
                        : 'text-ink',
                    )}
                  >
                    {formatNumber(summary?.stale ?? 0)}
                  </dd>
                </div>
              </dl>

              {indexDetails ? (
                <dl className="grid grid-cols-2 gap-4 rounded-lg border border-line bg-canvas/40 p-4 text-sm sm:grid-cols-3">
                  <div>
                    <dt className="text-xs text-faint">Chunk size</dt>
                    <dd className="mt-1 font-medium text-ink">
                      {formatNumber(indexDetails.chunk_size_tokens)} tokens
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-faint">Overlap</dt>
                    <dd className="mt-1 font-medium text-ink">
                      {formatNumber(indexDetails.chunk_overlap_tokens)} tokens
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-faint">Minimum</dt>
                    <dd className="mt-1 font-medium text-ink">
                      {formatNumber(indexDetails.chunk_min_tokens)} tokens
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-faint">Chunking version</dt>
                    <dd className="mt-1 break-all font-mono text-xs text-slate-300">
                      {indexDetails.chunking_version}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-faint">Token counting</dt>
                    <dd className="mt-1 break-all font-mono text-xs text-slate-300">
                      {indexDetails.token_counting}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-xs text-faint">Dimensions</dt>
                    <dd className="mt-1 font-medium text-ink">
                      {indexDetails.embedding_dimension == null
                        ? 'Unknown'
                        : formatNumber(
                            indexDetails.embedding_dimension,
                          )}
                    </dd>
                  </div>
                </dl>
              ) : null}

              {model.index.rebuild_required ? (
                <Notice
                  variant="warning"
                  title="Index rebuild required"
                >
                  {model.index.rebuild_reason ??
                    'The current embedding or chunking configuration no longer matches the stored vectors.'}
                </Notice>
              ) : null}

              {rebuildResult ? (
                <Notice
                  variant={
                    rebuildResult.failed > 0 ||
                    rebuildResult.status === 'failed'
                      ? 'warning'
                      : 'success'
                  }
                  title="Index rebuild finished"
                  action={
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setRebuildResult(null)}
                    >
                      Dismiss
                    </Button>
                  }
                >
                  Status {rebuildResult.status} ·{' '}
                  {formatNumber(rebuildResult.indexed)} indexed,{' '}
                  {formatNumber(rebuildResult.skipped)} skipped,{' '}
                  {formatNumber(rebuildResult.failed)} failed. Collection{' '}
                  <span className="font-mono text-xs">
                    {rebuildResult.collection}
                  </span>
                  .
                </Notice>
              ) : null}

              {rebuildMutation.isError ? (
                <Notice variant="error" title="Rebuild failed">
                  {getErrorMessage(rebuildMutation.error)}
                </Notice>
              ) : null}

              <div className="flex flex-col gap-3 border-t border-line pt-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-start gap-2">
                  <Wrench
                    className="mt-0.5 size-3.5 shrink-0 text-amber-300"
                    aria-hidden="true"
                  />
                  <p className="text-xs leading-5 text-faint">
                    Rebuilding deletes and recreates the ChromaDB collection,
                    then re-embeds every conversation. SQLite data is not
                    modified.
                  </p>
                </div>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    rebuildMutation.reset()
                    setRebuildOpen(true)
                  }}
                  disabled={rebuildMutation.isPending}
                >
                  <RefreshCw
                    className={cn(
                      'size-3.5',
                      rebuildMutation.isPending && 'animate-spin',
                    )}
                    aria-hidden="true"
                  />
                  Rebuild index
                </Button>
              </div>
            </div>
          </Panel>

          <Panel>
            <PanelHeader
              title="Installed Ollama models"
              description="Reported by the local Ollama API."
              icon={Activity}
              action={
                <Badge variant="neutral">
                  {formatNumber(model.installed_models.length)} models
                </Badge>
              }
            />
            {model.installed_models.length === 0 ? (
              <div className="px-5 py-8 text-center text-sm text-muted">
                No models reported. Check the Ollama connection above.
              </div>
            ) : (
              <ul className="divide-y divide-line">
                {model.installed_models.map((installedModel) => {
                  const isChat = isInstalled(
                    model.chat_model.name,
                    installedModel.name,
                  )
                  const isEmbedding = isInstalled(
                    model.embedding_model.name,
                    installedModel.name,
                  )

                  return (
                    <li
                      key={installedModel.name}
                      className="flex flex-wrap items-center gap-3 px-5 py-3.5"
                    >
                      <span className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-line bg-canvas-raised text-faint">
                        <Cpu className="size-3.5" aria-hidden="true" />
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-mono text-xs text-slate-200">
                          {installedModel.name}
                        </p>
                        <p className="mt-1 text-[11px] text-faint">
                          {formatBytes(installedModel.size)}
                          {installedModel.modified_at
                            ? ` · modified ${formatDate(
                                installedModel.modified_at,
                              )}`
                            : ''}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {isChat ? (
                          <Badge variant="accent">Chat</Badge>
                        ) : null}
                        {isEmbedding ? (
                          <Badge variant="info">Embeddings</Badge>
                        ) : null}
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
            {indexDetails ? (
              <p className="border-t border-line px-5 py-3 text-[11px] text-faint">
                Index status read at{' '}
                {formatDateTime(
                  new Date(indexQuery.dataUpdatedAt).toISOString(),
                )}
                . Model metadata is read from the local Ollama API.
              </p>
            ) : null}
          </Panel>
        </>
      ) : null}

      <ConfirmDialog
        open={rebuildOpen}
        title="Rebuild the vector index?"
        description={
          <>
            This deletes the current ChromaDB collection and re-embeds every
            conversation with{' '}
            <span className="font-mono text-xs text-ink">
              {model?.embedding_model.name ?? 'the configured model'}
            </span>
            . The SQLite conversations remain untouched. Rebuilding can take
            a few minutes.
          </>
        }
        confirmLabel="Rebuild index"
        loading={rebuildMutation.isPending}
        destructive
        onConfirm={confirmRebuild}
        onCancel={() => {
          if (!rebuildMutation.isPending) {
            setRebuildOpen(false)
          }
        }}
      />
    </div>
  )
}

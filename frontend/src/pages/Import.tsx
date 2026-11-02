import { useMutation } from '@tanstack/react-query'
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  Circle,
  Database,
  Import as ImportIcon,
  Link2,
  Loader2,
  MessageSquare,
  RefreshCw,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { Badge } from '../components/common/Badge'
import { Button, buttonStyles } from '../components/common/Button'
import { ErrorPanel, Notice } from '../components/common/Feedback'
import { PageHeader } from '../components/common/PageHeader'
import { Panel, PanelHeader } from '../components/common/Panel'
import { useInvalidateWorkspace } from '../hooks/queries'
import { cn } from '../lib/cn'
import { formatNumber, pluralize } from '../lib/format'
import { getErrorMessage } from '../services/api'
import {
  importConversation,
  indexConversation,
} from '../services/conversations'
import type {
  ImportResponse,
  IndexConversationResponse,
} from '../types/api'

type Stage =
  | 'idle'
  | 'importing'
  | 'indexing'
  | 'done'
  | 'index_failed'
  | 'error'

type StepState = 'pending' | 'active' | 'done' | 'error'

interface ImportOutcome {
  imported: ImportResponse
  indexed: IndexConversationResponse | null
  indexError: string | null
}

function validateShareUrl(value: string): string {
  if (!value.trim()) {
    return 'Enter a public ChatGPT shared conversation URL.'
  }

  let url: URL

  try {
    url = new URL(value.trim())
  } catch {
    return 'Enter a valid URL.'
  }

  if (url.protocol !== 'https:') {
    return 'Only HTTPS URLs are allowed.'
  }

  if (url.hostname !== 'chatgpt.com') {
    return 'Only chatgpt.com share URLs are allowed.'
  }

  if (!/^\/share\/[A-Za-z0-9_-]+\/?$/.test(url.pathname)) {
    return 'The URL must point to a /share/ conversation.'
  }

  return ''
}

function WorkflowStep({
  number,
  title,
  description,
  state,
}: {
  number: number
  title: string
  description: string
  state: StepState
}) {
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <span
          className={cn(
            'flex size-8 items-center justify-center rounded-full border text-xs font-semibold',
            state === 'done' &&
              'border-accent/40 bg-accent/10 text-emerald-300',
            state === 'active' &&
              'border-accent/40 bg-accent-deep text-emerald-300',
            state === 'error' &&
              'border-danger/40 bg-danger/10 text-rose-300',
            state === 'pending' &&
              'border-line-strong bg-canvas text-faint',
          )}
        >
          {state === 'done' ? (
            <CheckCircle2 className="size-4" />
          ) : state === 'active' ? (
            <Loader2 className="size-4 animate-spin" />
          ) : state === 'error' ? (
            <AlertCircle className="size-4" />
          ) : (
            number
          )}
        </span>
        {number < 3 ? (
          <span
            className={cn(
              'mt-1 h-8 w-px',
              state === 'done' ? 'bg-accent/30' : 'bg-line',
            )}
          />
        ) : null}
      </div>
      <div className="pb-2">
        <p
          className={cn(
            'text-sm font-medium',
            state === 'pending' ? 'text-muted' : 'text-ink',
          )}
        >
          {title}
        </p>
        <p className="mt-0.5 text-xs leading-5 text-faint">
          {description}
        </p>
      </div>
    </div>
  )
}

export function Import() {
  const invalidate = useInvalidateWorkspace()
  const [url, setUrl] = useState('')
  const [stage, setStage] = useState<Stage>('idle')
  const [validationError, setValidationError] = useState('')
  const [importedPreview, setImportedPreview] =
    useState<ImportResponse | null>(null)
  const [outcome, setOutcome] = useState<ImportOutcome | null>(null)

  const importMutation = useMutation({
    mutationFn: async (shareUrl: string): Promise<ImportOutcome> => {
      setStage('importing')
      setOutcome(null)
      setImportedPreview(null)

      const imported = await importConversation(shareUrl)
      setImportedPreview(imported)
      setStage('indexing')

      try {
        const indexed = await indexConversation(imported.conversation_id)

        return {
          imported,
          indexed,
          indexError: null,
        }
      } catch (error) {
        return {
          imported,
          indexed: null,
          indexError: getErrorMessage(error),
        }
      }
    },
    onSuccess: (result) => {
      setOutcome(result)
      setStage(result.indexError ? 'index_failed' : 'done')
      invalidate()
    },
    onError: () => {
      setStage('error')
    },
  })

  const retryIndex = useMutation({
    mutationFn: (conversationId: string) =>
      indexConversation(conversationId),
    onSuccess: (indexed) => {
      setOutcome((current) =>
        current
          ? { ...current, indexed, indexError: null }
          : current,
      )
      setStage('done')
      invalidate()
    },
  })

  const busy = importMutation.isPending || retryIndex.isPending

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const error = validateShareUrl(url)

    if (error) {
      setValidationError(error)
      return
    }

    setValidationError('')
    importMutation.mutate(url.trim())
  }

  const reset = () => {
    setUrl('')
    setStage('idle')
    setValidationError('')
    setImportedPreview(null)
    setOutcome(null)
    importMutation.reset()
    retryIndex.reset()
  }

  const stepOneState: StepState =
    stage === 'importing'
      ? 'active'
      : stage === 'error'
        ? 'error'
        : stage === 'idle'
          ? 'pending'
          : 'done'

  const stepTwoState: StepState =
    stage === 'importing'
      ? 'pending'
      : stage === 'error'
        ? 'pending'
        : stage === 'idle'
          ? 'pending'
          : 'done'

  const stepThreeState: StepState =
    stage === 'indexing'
      ? 'active'
      : stage === 'done'
        ? 'done'
        : stage === 'index_failed'
          ? 'error'
          : 'pending'

  const imported = outcome?.imported ?? importedPreview
  const indexed = outcome?.indexed ?? null
  const indexError = outcome?.indexError ?? null

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Ingestion"
        title="Import Conversation"
        description="Paste a public ChatGPT share link. ChatVault fetches the conversation, stores it in SQLite, and builds its local vector index."
        actions={
          <Link to="/library" className={buttonStyles('secondary', 'md')}>
            Browse library
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        }
      />

      <div className="grid items-start gap-6 xl:grid-cols-[1.35fr_1fr]">
        <div className="space-y-6">
          <Panel>
            <PanelHeader
              title="Shared conversation URL"
              description="Only public chatgpt.com/share links are accepted."
              icon={Link2}
              action={
                <Badge variant="info">HTTPS only</Badge>
              }
            />
            <form onSubmit={submit} className="space-y-4 p-5">
              <div>
                <label
                  htmlFor="share-url"
                  className="mb-2 block text-xs font-medium text-muted"
                >
                  ChatGPT share URL
                </label>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <input
                    id="share-url"
                    type="url"
                    inputMode="url"
                    value={url}
                    onChange={(event) => {
                      setUrl(event.target.value)
                      if (validationError) {
                        setValidationError('')
                      }
                    }}
                    placeholder="https://chatgpt.com/share/…"
                    disabled={busy}
                    autoComplete="off"
                    spellCheck={false}
                    aria-invalid={Boolean(validationError)}
                    aria-describedby={
                      validationError ? 'share-url-error' : 'share-url-help'
                    }
                    className={cn(
                      'h-11 min-w-0 flex-1 rounded-lg border bg-canvas px-3.5 font-mono text-[13px] text-ink placeholder:font-sans placeholder:text-faint/80 focus:outline-none focus:ring-2',
                      validationError
                        ? 'border-danger/50 focus:border-danger/60 focus:ring-danger/15'
                        : 'border-line focus:border-accent/50 focus:ring-accent/20',
                    )}
                  />
                  <Button
                    type="submit"
                    size="lg"
                    loading={importMutation.isPending}
                    disabled={busy}
                  >
                    <ImportIcon className="size-4" aria-hidden="true" />
                    {importMutation.isPending
                      ? stage === 'indexing'
                        ? 'Indexing…'
                        : 'Importing…'
                      : 'Import conversation'}
                  </Button>
                </div>
                {validationError ? (
                  <p
                    id="share-url-error"
                    className="mt-2 text-xs text-rose-300"
                    role="alert"
                  >
                    {validationError}
                  </p>
                ) : (
                  <p
                    id="share-url-help"
                    className="mt-2 text-xs leading-5 text-faint"
                  >
                    Example: https://chatgpt.com/share/&lt;share-id&gt; The
                    backend validates the URL before fetching it.
                  </p>
                )}
              </div>

              {importMutation.isError ? (
                <ErrorPanel
                  error={importMutation.error}
                  title="Import failed"
                  onRetry={() => importMutation.mutate(url.trim())}
                />
              ) : null}
            </form>
          </Panel>

          <Panel>
            <PanelHeader
              title="Workflow"
              description="Import and indexing status for this request."
              icon={Database}
              action={
                <Badge
                  variant={
                    stage === 'done'
                      ? 'accent'
                      : stage === 'index_failed' || stage === 'error'
                        ? 'danger'
                        : stage === 'idle'
                          ? 'neutral'
                          : 'info'
                  }
                  dot
                >
                  {stage === 'idle'
                    ? 'Ready'
                    : stage === 'importing'
                      ? 'Importing'
                      : stage === 'indexing'
                        ? 'Indexing'
                        : stage === 'done'
                          ? 'Complete'
                          : stage === 'index_failed'
                            ? 'Index failed'
                            : 'Failed'}
                </Badge>
              }
            />
            <div className="p-5">
              <div className="space-y-1">
                <WorkflowStep
                  number={1}
                  title="Fetch and extract"
                  description="Download the public page and parse the message tree."
                  state={stepOneState}
                />
                <WorkflowStep
                  number={2}
                  title="Save to SQLite"
                  description="Store the conversation and its messages as the source of truth."
                  state={stepTwoState}
                />
                <WorkflowStep
                  number={3}
                  title="Build the vector index"
                  description="Chunk messages, embed them with nomic-embed-text, and store vectors in ChromaDB."
                  state={stepThreeState}
                />
              </div>

              {stage === 'indexing' && imported ? (
                <div className="mt-4 rounded-lg border border-info/25 bg-info/[0.05] px-4 py-3">
                  <p className="text-xs font-medium text-ink">
                    Extracted “{imported.title}”
                  </p>
                  <p className="mt-1 text-xs text-faint">
                    {pluralize(imported.message_count, 'message')} saved.
                    Generating local embeddings…
                  </p>
                </div>
              ) : null}

              {stage === 'error' && importMutation.isError ? (
                <p className="mt-4 text-xs leading-5 text-rose-300">
                  {getErrorMessage(importMutation.error)}
                </p>
              ) : null}

              {stage === 'done' && indexed ? (
                <div className="mt-4 rounded-lg border border-accent/25 bg-accent/[0.05] px-4 py-3">
                  <p className="text-xs font-medium text-emerald-200">
                    Index ready · {formatNumber(indexed.chunks)} chunks
                  </p>
                  <p className="mt-1 text-xs text-faint">
                    {indexed.embedding_model} · chunking{' '}
                    {indexed.chunking_version} ·{' '}
                    {indexed.status === 'already_indexed'
                      ? 'existing index reused'
                      : 'new vectors stored'}
                  </p>
                </div>
              ) : null}
            </div>
          </Panel>

          {outcome ? (
            <Panel className="border-accent/20">
              <PanelHeader
                title={
                  stage === 'index_failed'
                    ? 'Conversation saved — indexing needs attention'
                    : 'Conversation imported and indexed'
                }
                description="The SQLite record is durable. The vector index can be rebuilt at any time."
                icon={
                  stage === 'index_failed' ? AlertCircle : CheckCircle2
                }
                action={
                  <Badge
                    variant={
                      stage === 'index_failed' ? 'warning' : 'accent'
                    }
                    dot
                  >
                    {stage === 'index_failed'
                      ? 'Index failed'
                      : 'Ready for chat'}
                  </Badge>
                }
              />
              <div className="space-y-4 p-5">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-semibold text-ink">
                      {outcome.imported.title}
                    </h3>
                    <Badge variant="neutral">
                      {outcome.imported.status === 'already_exists'
                        ? 'Already in library'
                        : 'New import'}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-faint">
                    {pluralize(
                      outcome.imported.message_count,
                      'message',
                    )}{' '}
                    stored locally
                  </p>
                </div>

                {indexError ? (
                  <Notice
                    variant="warning"
                    title="The conversation was saved, but indexing failed"
                    action={
                      <Button
                        variant="secondary"
                        size="sm"
                        loading={retryIndex.isPending}
                        onClick={() =>
                          retryIndex.mutate(
                            outcome.imported.conversation_id,
                          )
                        }
                      >
                        <RefreshCw className="size-3.5" />
                        Retry index
                      </Button>
                    }
                  >
                    {indexError}
                    {retryIndex.isError ? (
                      <p className="mt-2 text-rose-300">
                        {getErrorMessage(retryIndex.error)}
                      </p>
                    ) : null}
                  </Notice>
                ) : indexed ? (
                  <dl className="grid grid-cols-2 gap-4 rounded-lg border border-line bg-canvas/50 p-4 text-sm sm:grid-cols-4">
                    <div>
                      <dt className="text-xs text-faint">Chunks</dt>
                      <dd className="mt-1 font-medium text-ink">
                        {formatNumber(indexed.chunks)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-faint">Messages</dt>
                      <dd className="mt-1 font-medium text-ink">
                        {formatNumber(outcome.imported.message_count)}
                      </dd>
                    </div>
                    <div className="col-span-2">
                      <dt className="text-xs text-faint">
                        Embedding model
                      </dt>
                      <dd className="mt-1 truncate font-mono text-xs text-slate-300">
                        {indexed.embedding_model}
                      </dd>
                    </div>
                  </dl>
                ) : null}

                <div className="flex flex-wrap gap-2">
                  <Link
                    to={`/conversations/${outcome.imported.conversation_id}`}
                    className={buttonStyles('primary', 'sm')}
                  >
                    <MessageSquare
                      className="size-3.5"
                      aria-hidden="true"
                    />
                    Open conversation
                  </Link>
                  <Link
                    to="/chat"
                    className={buttonStyles('secondary', 'sm')}
                  >
                    <Sparkles
                      className="size-3.5"
                      aria-hidden="true"
                    />
                    Ask AI
                  </Link>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={reset}
                  >
                    Import another
                  </Button>
                </div>
              </div>
            </Panel>
          ) : null}
        </div>

        <div className="space-y-6 xl:sticky xl:top-24">
          <Panel>
            <PanelHeader
              title="What happens locally"
              description="The import pipeline runs on this machine."
              icon={ShieldCheck}
            />
            <ol className="space-y-4 p-5">
              {[
                {
                  icon: Link2,
                  title: 'Validated source',
                  detail:
                    'Only public chatgpt.com/share URLs are fetched. Credentials and custom ports are rejected.',
                },
                {
                  icon: Database,
                  title: 'SQLite is the source of truth',
                  detail:
                    'The imported conversation and messages are persisted before indexing begins.',
                },
                {
                  icon: MessageSquare,
                  title: 'Message-aware chunking',
                  detail:
                    'Chunks never cross message boundaries. Code blocks are preserved where possible.',
                },
                {
                  icon: Sparkles,
                  title: 'Local embeddings',
                  detail:
                    'nomic-embed-text runs through Ollama. ChromaDB stores the derived vectors.',
                },
              ].map((item) => {
                const Icon = item.icon

                return (
                  <li key={item.title} className="flex gap-3">
                    <span className="mt-0.5 flex size-8 shrink-0 items-cms-center justify-center rounded-lg border border-line bg-canvas-raised text-emerald-300">
                      <Icon className="size-4" aria-hidden="true" />
                    </span>
                    <div>
                      <p className="text-sm font-medium text-ink">
                        {item.title}
                      </p>
                      <p className="mt-1 text-xs leading-5 text-muted">
                        {item.detail}
                      </p>
                    </div>
                  </li>
                )
              })}
            </ol>
          </Panel>

          <Notice variant="info" title="Indexing failures are recoverable">
            If Ollama is unavailable, the conversation stays in SQLite and
            the index can be retried without importing again.
          </Notice>

          {stage === 'idle' ? (
            <div className="flex items-center gap-2 px-1 text-xs text-faint">
              <Circle className="size-2 fill-current" aria-hidden="true" />
              Waiting for a shared conversation URL.
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

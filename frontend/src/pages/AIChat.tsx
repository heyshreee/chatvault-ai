import { useMutation } from '@tanstack/react-query'
import {
  AlertCircle,
  ArrowUpRight,
  Bot,
  Compass,
  Import,
  RotateCcw,
  Send,
  Sparkles,
  UserRound,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { Link } from 'react-router-dom'

import { Badge } from '../components/common/Badge'
import { Button, buttonStyles } from '../components/common/Button'
import { Notice } from '../components/common/Feedback'
import { Markdown } from '../components/common/Markdown'
import { PageHeader } from '../components/common/PageHeader'
import { Panel } from '../components/common/Panel'
import { SourceCard } from '../components/chat/SourceCard'
import { useStats } from '../hooks/queries'
import { cn } from '../lib/cn'
import { formatNumber } from '../lib/format'
import { askQuestion } from '../services/chat'
import { getErrorMessage } from '../services/api'
import type {
  ChatRequest,
  ChatResponse,
  ChatSource,
  ChatTurn,
} from '../types/api'

interface ChatEntry {
  id: string
  role: 'user' | 'assistant'
  content: string
  status?: 'answered' | 'no_sources' | 'error'
  sources?: ChatSource[]
  model?: string | null
  error?: string
  retryMessage?: string
  retryHistory?: ChatTurn[]
}

const starterPrompts = [
  'Summarize the most important ideas in my recent conversations.',
  'Which commands and tools have I saved?',
  'What did I learn about a specific topic?',
]

function makeId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function buildHistory(entries: ChatEntry[]): ChatTurn[] {
  return entries
    .filter(
      (entry) =>
        entry.status !== 'error' && entry.status !== 'no_sources',
    )
    .map((entry) => ({
      role: entry.role,
      content: entry.content,
    }))
    .filter((entry) => entry.content.trim().length > 0)
    .slice(-10)
}

function ChatEntryView({
  entry,
  onRetry,
  retryDisabled,
}: {
  entry: ChatEntry
  onRetry: (entry: ChatEntry) => void
  retryDisabled: boolean
}) {
  if (entry.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[88%] sm:max-w-[75%]">
          <div className="mb-1.5 flex items-center justify-end gap-1.5 text-[10px] uppercase tracking-[0.12em] text-faint">
            You
            <UserRound className="size-3" aria-hidden="true" />
          </div>
          <div className="whitespace-pre-wrap break-words rounded-xl rounded-tr-sm border border-accent/25 bg-accent-deep/60 px-4 py-3 text-sm leading-6 text-slate-100">
            {entry.content}
          </div>
        </div>
      </div>
    )
  }

  if (entry.status === 'error') {
    return (
      <div className="flex gap-3">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-danger/30 bg-danger/10 text-rose-300">
          <AlertCircle className="size-4" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="mb-2 text-xs font-semibold text-ink">ChatVault</p>
          <Notice
            variant="error"
            title="The answer could not be generated"
            action={
              entry.retryMessage ? (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => onRetry(entry)}
                  disabled={retryDisabled}
                >
                  Retry
                </Button>
              ) : null
            }
          >
            {entry.error}
          </Notice>
        </div>
      </div>
    )
  }

  if (entry.status === 'no_sources') {
    return (
      <div className="flex gap-3">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-warning/30 bg-warning/10 text-amber-300">
          <Compass className="size-4" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <p className="text-xs font-semibold text-ink">ChatVault</p>
            <Badge variant="warning" dot>
              No sources
            </Badge>
          </div>
          <Notice
            variant="warning"
            title="No indexed context matched this question"
            action={
              <Link
                to="/import"
                className={buttonStyles('secondary', 'sm')}
              >
                <Import className="size-3.5" aria-hidden="true" />
                Import
              </Link>
            }
          >
            {entry.content}
          </Notice>
        </div>
      </div>
    )
  }

  const sources = entry.sources ?? []

  return (
    <div className="flex gap-3">
      <span className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-accent/25 bg-accent-deep text-emerald-300">
        <Bot className="size-4" aria-hidden="true" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="mb-2 flex flex-wrap items-center gap-2">
          <p className="text-xs font-semibold text-ink">ChatVault</p>
          {entry.model ? (
            <Badge variant="neutral">{entry.model}</Badge>
          ) : null}
          <Badge variant="accent" dot>
            {sources.length}{' '}
            {sources.length === 1 ? 'source' : 'sources'}
          </Badge>
        </div>

        <div className="rounded-xl border border-line bg-canvas/45 px-4 py-3.5">
          <Markdown content={entry.content} />
        </div>

        {sources.length > 0 ? (
          <div className="mt-3">
            <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-faint">
              Sources
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {sources.map((source) => (
                <SourceCard key={source.index} source={source} />
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}

function EmptyChat({
  hasIndex,
  statsLoading,
  onUsePrompt,
}: {
  hasIndex: boolean
  statsLoading: boolean
  onUsePrompt: (prompt: string) => void
}) {
  return (
    <div className="mx-auto flex min-h-full max-w-2xl flex-col items-center justify-center py-8 text-center">
      <span className="flex size-12 items-center justify-center rounded-xl border border-accent/25 bg-accent-deep text-emerald-300">
        <Sparkles className="size-5" aria-hidden="true" />
      </span>
      <h2 className="mt-4 text-xl font-semibold tracking-tight text-ink">
        Ask across your library
      </h2>
      <p className="mt-2 max-w-md text-sm leading-6 text-muted">
        ChatVault retrieves the closest indexed chunks from your imported
        conversations, asks the local chat model for an answer, and returns
        the sources it used.
      </p>

      {!statsLoading && !hasIndex ? (
        <div className="mt-5 w-full">
          <Notice
            variant="warning"
            title="No indexed conversations yet"
            action={
              <Link
                to="/import"
                className={buttonStyles('secondary', 'sm')}
              >
                <Import className="size-3.5" aria-hidden="true" />
                Import
              </Link>
            }
          >
            Import a conversation and let indexing finish before asking a
            question.
          </Notice>
        </div>
      ) : null}

      <div className="mt-6 grid w-full gap-2 sm:grid-cols-3">
        {starterPrompts.map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => onUsePrompt(prompt)}
            className="group rounded-lg border border-line bg-canvas/40 p-3 text-left text-xs leading-5 text-muted transition-colors hover:border-accent/30 hover:bg-panel-raised hover:text-ink"
          >
            <span className="flex items-start justify-between gap-2">
              {prompt}
              <ArrowUpRight
                className="mt-0.5 size-3.5 shrink-0 text-faint transition-colors group-hover:text-emerald-300"
                aria-hidden="true"
              />
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}

export function AIChat() {
  const [messages, setMessages] = useState<ChatEntry[]>([])
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const statsQuery = useStats()

  const mutation = useMutation<ChatResponse, unknown, ChatRequest>({
    mutationFn: askQuestion,
    onSuccess: (data) => {
      setMessages((current) => [
        ...current,
        {
          id: makeId(),
          role: 'assistant',
          content: data.answer,
          status: data.status,
          sources: data.sources,
          model: data.model,
        },
      ])
    },
    onError: (error, variables) => {
      setMessages((current) => [
        ...current,
        {
          id: makeId(),
          role: 'assistant',
          content: '',
          status: 'error',
          error: getErrorMessage(error),
          retryMessage: variables.message,
          retryHistory: variables.history ?? [],
        },
      ])
    },
  })

  const indexedCount = statsQuery.data?.indexed_conversations ?? 0
  const hasIndex = indexedCount > 0

  useEffect(() => {
    const container = scrollRef.current

    if (container) {
      container.scrollTo({
        top: container.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [messages.length, mutation.isPending])

  const send = (raw: string) => {
    const text = raw.trim()

    if (!text || mutation.isPending) {
      return
    }

    const history = buildHistory(messages)

    setMessages((current) => [
      ...current,
      {
        id: makeId(),
        role: 'user',
        content: text,
      },
    ])
    setInput('')
    mutation.mutate({
      message: text,
      history,
      top_k: 5,
    })
    window.requestAnimationFrame(() => inputRef.current?.focus())
  }

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    send(input)
  }

  const handleKeyDown = (
    event: KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      send(input)
    }
  }

  const retry = (entry: ChatEntry) => {
    if (mutation.isPending || !entry.retryMessage) {
      return
    }

    setMessages((current) =>
      current.filter((item) => item.id !== entry.id),
    )
    mutation.mutate({
      message: entry.retryMessage,
      history: entry.retryHistory ?? [],
      top_k: 5,
    })
  }

  const clearChat = () => {
    if (mutation.isPending) {
      return
    }

    setMessages([])
    setInput('')
    mutation.reset()
    inputRef.current?.focus()
  }

  const usePrompt = (prompt: string) => {
    setInput(prompt)
    inputRef.current?.focus()
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Retrieval-augmented chat"
        title="AI Chat"
        description="Ask questions across your indexed conversations. Answers are generated locally and cite the source chunks they used."
        actions={
          <Button
            variant="secondary"
            size="md"
            onClick={clearChat}
            disabled={messages.length === 0 || mutation.isPending}
          >
            <RotateCcw className="size-4" aria-hidden="true" />
            Clear chat
          </Button>
        }
      />

      <Panel className="flex min-h-[560px] flex-col overflow-hidden lg:h-[calc(100vh-13rem)]">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3 sm:px-5">
          <div className="flex flex-wrap items-center gap-2">
            <span className="size-1.5 rounded-full bg-emerald-400" />
            <span className="text-sm font-medium text-ink">
              Local RAG chat
            </span>
            {statsQuery.isLoading ? (
              <Badge variant="neutral">Checking index</Badge>
            ) : statsQuery.isError ? (
              <Badge variant="danger" dot>
                Index status unavailable
              </Badge>
            ) : (
              <Badge
                variant={hasIndex ? 'accent' : 'warning'}
                dot
              >
                {hasIndex
                  ? `${formatNumber(indexedCount)} indexed`
                  : 'No indexed conversations'}
              </Badge>
            )}
          </div>
          <p className="text-[11px] text-faint">
            Sources link back to your library
          </p>
        </div>

        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto px-4 py-5 sm:px-6"
          aria-live="polite"
          aria-relevant="additions"
        >
          {messages.length === 0 && !mutation.isPending ? (
            <EmptyChat
              hasIndex={hasIndex}
              statsLoading={statsQuery.isLoading}
              onUsePrompt={usePrompt}
            />
          ) : (
            <div className="space-y-5">
              {messages.map((entry) => (
                <ChatEntryView
                  key={entry.id}
                  entry={entry}
                  onRetry={retry}
                  retryDisabled={mutation.isPending}
                />
              ))}

              {mutation.isPending ? (
                <div className="flex gap-3" aria-label="Generating answer">
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-lg border border-accent/25 bg-accent-deep text-emerald-300">
                    <Bot className="size-4" aria-hidden="true" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="mb-2 text-xs font-semibold text-ink">
                      ChatVault
                    </p>
                    <div className="inline-flex items-center gap-3 rounded-xl border border-line bg-canvas/45 px-4 py-3">
                      <span className="flex items-center gap-1">
                        <span className="thinking-dot size-1.5 rounded-full bg-emerald-400" />
                        <span className="thinking-dot size-1.5 rounded-full bg-emerald-400" />
                        <span className="thinking-dot size-1.5 rounded-full bg-emerald-400" />
                      </span>
                      <span className="text-xs text-muted">
                        Searching the index and generating an answer…
                      </span>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>

        <div className="border-t border-line bg-canvas-raised/40 p-3 sm:p-4">
          {!statsQuery.isLoading && !hasIndex ? (
            <div className="mb-3">
              <Notice
                variant="warning"
                title="AI Chat needs indexed context"
                action={
                  <Link
                    to="/import"
                    className={buttonStyles('secondary', 'sm')}
                  >
                    <Import className="size-3.5" aria-hidden="true" />
                    Import
                  </Link>
                }
              >
                Import a conversation and wait for indexing to finish. The
                chat model is not called when no sources match.
              </Notice>
            </div>
          ) : null}

          <form
            onSubmit={submit}
            className={cn(
              'rounded-xl border border-line bg-canvas p-2 transition-colors focus-within:border-accent/40 focus-within:ring-2 focus-within:ring-accent/10',
              mutation.isPending && 'opacity-70',
            )}
          >
            <label htmlFor="chat-input" className="sr-only">
              Ask a question about your conversations
            </label>
            <textarea
              id="chat-input"
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your conversations…"
              disabled={mutation.isPending}
              className="max-h-40 min-h-11 w-full resize-none bg-transparent px-2 py-2 text-sm leading-6 text-ink placeholder:text-faint/80 focus:outline-none disabled:cursor-not-allowed"
            />
            <div className="flex items-center justify-between gap-3 px-1 pb-1">
              <p className="hidden text-[10px] text-faint sm:block">
                Enter to send · Shift + Enter for a new line
              </p>
              <Button
                type="submit"
                size="sm"
                disabled={!input.trim() || mutation.isPending}
                className="ml-auto"
              >
                <Send className="size-3.5" aria-hidden="true" />
                {mutation.isPending ? 'Thinking…' : 'Send'}
              </Button>
            </div>
          </form>

          <p className="mt-2 px-1 text-[10px] leading-4 text-faint">
            Answers come from the configured local Ollama chat model and the
            indexed source chunks. Verify important details.
          </p>
        </div>
      </Panel>
    </div>
  )
}

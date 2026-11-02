import {
  ArrowLeft,
  Bot,
  CalendarDays,
  Check,
  Copy,
  ExternalLink,
  FileDown,
  FileText,
  MessageSquare,
  Sparkles,
  UserRound,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Badge } from '../components/common/Badge'
import { Button, buttonStyles } from '../components/common/Button'
import {
  ErrorPanel,
  LoadingPanel,
  Notice,
} from '../components/common/Feedback'
import { Markdown } from '../components/common/Markdown'
import { PageHeader } from '../components/common/PageHeader'
import { Panel } from '../components/common/Panel'
import { useConversation } from '../hooks/queries'
import { cn } from '../lib/cn'
import {
  formatDate,
  formatDateTime,
  hostnameFromUrl,
  pluralize,
} from '../lib/format'
import { getErrorMessage } from '../services/api'
import type { ExportFormat } from '../services/export'
import { downloadConversationExport } from '../services/export'

export function Conversation() {
  const { conversationId = '' } = useParams<{
    conversationId: string
  }>()
  const conversationQuery = useConversation(conversationId)
  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  const [exporting, setExporting] = useState<ExportFormat | null>(null)
  const [exportError, setExportError] = useState<string | null>(null)
  const copyTimerRef = useRef<number | null>(null)

  useEffect(() => {
    return () => {
      if (copyTimerRef.current !== null) {
        window.clearTimeout(copyTimerRef.current)
      }
    }
  }, [])

  const conversation = conversationQuery.data

  const copyMessage = async (key: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedKey(key)

      if (copyTimerRef.current !== null) {
        window.clearTimeout(copyTimerRef.current)
      }

      copyTimerRef.current = window.setTimeout(
        () => setCopiedKey(null),
        1_600,
      )
    } catch {
      setCopiedKey(null)
    }
  }

  const exportConversation = async (format: ExportFormat) => {
    if (!conversation) {
      return
    }

    setExportError(null)
    setExporting(format)

    try {
      await downloadConversationExport(
        conversation.conversation_id,
        format,
      )
    } catch (error) {
      setExportError(getErrorMessage(error))
    } finally {
      setExporting(null)
    }
  }

  if (conversationQuery.isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Conversation"
          title="Loading conversation"
          description="Reading the stored messages and metadata."
        />
        <LoadingPanel rows={7} label="Loading conversation" />
      </div>
    )
  }

  if (conversationQuery.isError) {
    return (
      <div className="space-y-6">
        <Link
          to="/library"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted transition-colors hover:text-ink"
        >
          <ArrowLeft className="size-3.5" aria-hidden="true" />
          Back to library
        </Link>
        <ErrorPanel
          error={conversationQuery.error}
          title="Unable to open this conversation"
          onRetry={() => void conversationQuery.refetch()}
        />
        <Link
          to="/library"
          className={buttonStyles('secondary', 'sm', 'w-fit')}
        >
          Return to library
        </Link>
      </div>
    )
  }

  if (!conversation) {
    return null
  }

  return (
    <div className="space-y-6">
      <div>
        <Link
          to="/library"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted transition-colors hover:text-ink"
        >
          <ArrowLeft className="size-3.5" aria-hidden="true" />
          Back to library
        </Link>

        <PageHeader
          className="mt-4"
          eyebrow="Conversation"
          title={conversation.title}
          description={`${pluralize(
            conversation.message_count,
            'message',
          )} · Imported ${formatDate(conversation.created_at)}`}
          actions={
            <>
              <Link
                to="/chat"
                className={buttonStyles('secondary', 'md')}
              >
                <Sparkles className="size-4" aria-hidden="true" />
                Ask AI
              </Link>
              <Button
                variant="secondary"
                size="md"
                loading={exporting === 'pdf'}
                disabled={Boolean(exporting)}
                onClick={() => void exportConversation('pdf')}
              >
                <FileText className="size-4" aria-hidden="true" />
                Export PDF
              </Button>
              <Button
                variant="secondary"
                size="md"
                loading={exporting === 'docx'}
                disabled={Boolean(exporting)}
                onClick={() => void exportConversation('docx')}
              >
                <FileDown className="size-4" aria-hidden="true" />
                Export DOCX
              </Button>
            </>
          }
        />

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Badge variant="accent" dot>
            Stored locally
          </Badge>
          <Badge variant="neutral">
            {pluralize(conversation.message_count, 'message')}
          </Badge>
          <span className="inline-flex items-center gap-1.5 text-xs text-faint">
            <CalendarDays className="size-3.5" aria-hidden="true" />
            {formatDateTime(conversation.created_at)}
          </span>
          <a
            href={conversation.source_url}
            target="_blank"
            rel="noreferrer noopener"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-300 transition-colors hover:text-emerald-200"
          >
            <ExternalLink className="size-3.5" aria-hidden="true" />
            {hostnameFromUrl(conversation.source_url)}
          </a>
        </div>
      </div>

      {exportError ? (
        <Notice
          variant="error"
          title="Export failed"
          action={
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setExportError(null)}
            >
              Dismiss
            </Button>
          }
        >
          {exportError}
        </Notice>
      ) : null}

      <div className="flex items-center gap-2 px-1 text-xs text-faint">
        <MessageSquare className="size-3.5" aria-hidden="true" />
        Full transcript, rendered from SQLite
      </div>

      <div className="space-y-4">
        {conversation.messages.map((message, index) => {
          const isUser = message.role === 'user'
          const key = `${message.position}-${index}`

          return (
            <article
              key={key}
              className={cn(
                'rounded-xl border p-4 sm:p-5',
                isUser
                  ? 'border-accent/15 bg-accent/[0.035]'
                  : 'border-line bg-panel/90',
              )}
            >
              <header className="flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-2.5">
                  <span
                    className={cn(
                      'flex size-8 shrink-0 items-center justify-center rounded-lg border',
                      isUser
                        ? 'border-line-strong bg-canvas-raised text-slate-300'
                        : 'border-accent/25 bg-accent-deep text-emerald-300',
                    )}
                  >
                    {isUser ? (
                      <UserRound
                        className="size-4"
                        aria-hidden="true"
                      />
                    ) : (
                      <Bot className="size-4" aria-hidden="true" />
                    )}
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-ink">
                      {isUser ? 'You' : 'Assistant'}
                    </p>
                    <p className="text-[10px] uppercase tracking-[0.12em] text-faint">
                      Message {message.position + 1}
                    </p>
                  </div>
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() =>
                    void copyMessage(key, message.content)
                  }
                  aria-label={
                    copiedKey === key
                      ? 'Message copied'
                      : 'Copy message'
                  }
                >
                  {copiedKey === key ? (
                    <Check className="size-3.5 text-emerald-300" />
                  ) : (
                    <Copy className="size-3.5" />
                  )}
                  {copiedKey === key ? 'Copied' : 'Copy'}
                </Button>
              </header>

              <div className="mt-4">
                <Markdown content={message.content} />
              </div>
            </article>
          )
        })}
      </div>

      <div className="flex items-center gap-3 py-2">
        <span className="h-px flex-1 bg-line" />
        <span className="text-[10px] uppercase tracking-[0.16em] text-faint">
          End of conversation
        </span>
        <span className="h-px flex-1 bg-line" />
      </div>

      <Panel className="flex flex-col gap-3 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium text-ink">
            Continue in AI Chat
          </p>
          <p className="mt-1 text-xs text-muted">
            Ask questions across this conversation and the rest of your
            indexed library.
          </p>
        </div>
        <Link to="/chat" className={buttonStyles('primary', 'sm')}>
          <Sparkles className="size-3.5" aria-hidden="true" />
          Open AI Chat
        </Link>
      </Panel>
    </div>
  )
}

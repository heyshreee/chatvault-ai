import {
  ArrowUpDown,
  CalendarDays,
  ChevronRight,
  Import,
  Library as LibraryIcon,
  MessageSquare,
  Search,
  SearchX,
  Trash2,
} from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { Badge } from '../components/common/Badge'
import { Button, buttonStyles } from '../components/common/Button'
import { ConfirmDialog } from '../components/common/ConfirmDialog'
import {
  EmptyState,
  ErrorPanel,
  LoadingPanel,
  Notice,
} from '../components/common/Feedback'
import { PageHeader } from '../components/common/PageHeader'
import { Panel } from '../components/common/Panel'
import { useConversations, useDeleteConversation } from '../hooks/queries'
import { cn } from '../lib/cn'
import { formatDate, pluralize } from '../lib/format'
import { getErrorMessage } from '../services/api'
import type { ConversationListItem } from '../types/api'

type SortOption = 'newest' | 'oldest' | 'title' | 'messages'
type FilterOption = 'all' | 'week' | 'long'

const sortLabels: Record<SortOption, string> = {
  newest: 'Newest first',
  oldest: 'Oldest first',
  title: 'Title A–Z',
  messages: 'Most messages',
}

const filters: Array<{ value: FilterOption; label: string }> = [
  { value: 'all', label: 'All' },
  { value: 'week', label: 'Last 7 days' },
  { value: 'long', label: '10+ messages' },
]

export function Library() {
  const conversationsQuery = useConversations(100)
  const deleteMutation = useDeleteConversation()
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<SortOption>('newest')
  const [filter, setFilter] = useState<FilterOption>('all')
  const [pendingDelete, setPendingDelete] =
    useState<ConversationListItem | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const conversations = conversationsQuery.data?.items ?? []
  const total = conversationsQuery.data?.total ?? 0

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase()
    const now = Date.now()
    const weekMs = 7 * 24 * 60 * 60 * 1000

    return conversations
      .filter((conversation) => {
        if (
          query &&
          !conversation.title.toLowerCase().includes(query)
        ) {
          return false
        }

        if (filter === 'week') {
          const created = new Date(conversation.created_at).getTime()

          if (Number.isNaN(created) || now - created > weekMs) {
            return false
          }
        }

        if (filter === 'long' && conversation.message_count < 10) {
          return false
        }

        return true
      })
      .sort((a, b) => {
        if (sort === 'title') {
          return a.title.localeCompare(b.title)
        }

        if (sort === 'messages') {
          return b.message_count - a.message_count
        }

        const aTime = new Date(a.created_at).getTime()
        const bTime = new Date(b.created_at).getTime()

        return sort === 'oldest' ? aTime - bTime : bTime - aTime
      })
  }, [conversations, filter, search, sort])

  const hasFilters = search.trim().length > 0 || filter !== 'all'
  const isFilteredEmpty = visible.length === 0 && conversations.length > 0

  const clearFilters = () => {
    setSearch('')
    setFilter('all')
  }

  const confirmDelete = () => {
    if (!pendingDelete) {
      return
    }

    deleteMutation.mutate(pendingDelete.conversation_id, {
      onSuccess: () => {
        setSuccessMessage(
          `Deleted “${pendingDelete.title}” and its indexed vectors.`,
        )
        setPendingDelete(null)
      },
    })
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Knowledge base"
        title="Conversation Library"
        description="Browse, search, sort, and manage every conversation stored in SQLite. Deleting a conversation also removes its derived vectors."
        actions={
          <Link to="/import" className={buttonStyles('primary', 'md')}>
            <Import className="size-4" aria-hidden="true" />
            Import conversation
          </Link>
        }
      />

      {successMessage ? (
        <Notice
          variant="success"
          title="Conversation deleted"
          action={
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSuccessMessage(null)}
            >
              Dismiss
            </Button>
          }
        >
          {successMessage}
        </Notice>
      ) : null}

      {deleteMutation.isError && !pendingDelete ? (
        <Notice variant="error" title="Delete failed">
          {getErrorMessage(deleteMutation.error)}
        </Notice>
      ) : null}

      <Panel className="p-3 sm:p-4">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
          <div className="relative min-w-0 flex-1">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-faint"
              aria-hidden="true"
            />
            <label htmlFor="library-search" className="sr-only">
              Search conversations by title
            </label>
            <input
              id="library-search"
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search by title…"
              className="h-10 w-full rounded-lg border border-line bg-canvas px-9 text-sm text-ink placeholder:text-faint/80 focus:border-accent/50 focus:outline-none focus:ring-2 focus:ring-accent/20"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1 rounded-lg border border-line bg-canvas p-1">
              {filters.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setFilter(option.value)}
                  className={cn(
                    'rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors',
                    filter === option.value
                      ? 'bg-panel-raised text-ink'
                      : 'text-faint hover:text-ink',
                  )}
                >
                  {option.label}
                </button>
              ))}
            </div>

            <div className="relative">
              <ArrowUpDown
                className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-faint"
                aria-hidden="true"
              />
              <label htmlFor="library-sort" className="sr-only">
                Sort conversations
              </label>
              <select
                id="library-sort"
                value={sort}
                onChange={(event) =>
                  setSort(event.target.value as SortOption)
                }
                className="h-10 appearance-none rounded-lg border border-line bg-canvas pl-8 pr-8 text-xs font-medium text-muted focus:border-accent/50 focus:outline-none focus:ring-2 focus:ring-accent/20"
              >
                {Object.entries(sortLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 px-1 text-xs text-faint">
          <span>
            {visible.length === total
              ? pluralize(total, 'conversation')
              : `${visible.length} of ${pluralize(total, 'conversation')}`}
          </span>
          {hasFilters ? (
            <button
              type="button"
              onClick={clearFilters}
              className="text-emerald-300 transition-colors hover:text-emerald-200"
            >
              Clear filters
            </button>
          ) : null}
        </div>
      </Panel>

      {conversationsQuery.isLoading ? (
        <LoadingPanel rows={8} label="Loading conversations" />
      ) : conversationsQuery.isError ? (
        <ErrorPanel
          error={conversationsQuery.error}
          title="Unable to load the conversation library"
          onRetry={() => void conversationsQuery.refetch()}
        />
      ) : conversations.length === 0 ? (
        <Panel>
          <EmptyState
            icon={LibraryIcon}
            title="Your library is empty"
            description="Import a public ChatGPT shared conversation to store it locally, index it, and make it available to AI Chat."
            action={
              <Link to="/import" className={buttonStyles('primary', 'sm')}>
                <Import className="size-3.5" aria-hidden="true" />
                Import conversation
              </Link>
            }
          />
        </Panel>
      ) : isFilteredEmpty ? (
        <Panel>
          <EmptyState
            icon={SearchX}
            title="No conversations match these filters"
            description="Try a different title, remove the date or message-count filter, or clear the search."
            action={
              <Button variant="secondary" size="sm" onClick={clearFilters}>
                Clear filters
              </Button>
            }
          />
        </Panel>
      ) : (
        <Panel className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-line px-5 py-3">
            <div className="flex items-center gap-2">
              <LibraryIcon
                className="size-4 text-emerald-300"
                aria-hidden="true"
              />
              <h2 className="text-sm font-semibold text-ink">
                {hasFilters ? 'Filtered conversations' : 'All conversations'}
              </h2>
            </div>
            {total > conversations.length ? (
              <Badge variant="neutral">
                Showing {conversations.length} of {total}
              </Badge>
            ) : null}
          </div>

          <ul className="divide-y divide-line">
            {visible.map((conversation) => (
              <li
                key={conversation.conversation_id}
                className="group flex items-center gap-2 px-4 py-3 transition-colors hover:bg-panel-raised/50 sm:px-5"
              >
                <Link
                  to={`/conversations/${conversation.conversation_id}`}
                  className="flex min-w-0 flex-1 items-center gap-4 rounded-lg py-1"
                >
                  <span className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-line bg-canvas-raised text-faint transition-colors group-hover:border-accent/25 group-hover:text-emerald-300">
                    <MessageSquare
                      className="size-4"
                      aria-hidden="true"
                    />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink">
                      {conversation.title}
                    </p>
                    <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-faint">
                      <span className="inline-flex items-center gap-1.5">
                        <MessageSquare
                          className="size-3"
                          aria-hidden="true"
                        />
                        {pluralize(
                          conversation.message_count,
                          'message',
                        )}
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <CalendarDays
                          className="size-3"
                          aria-hidden="true"
                        />
                        {formatDate(conversation.created_at)}
                      </span>
                    </div>
                  </div>
                  <ChevronRight
                    className="hidden size-4 shrink-0 text-faint transition-transform group-hover:translate-x-0.5 group-hover:text-muted sm:block"
                    aria-hidden="true"
                  />
                </Link>

                <button
                  type="button"
                  onClick={() => {
                    deleteMutation.reset()
                    setPendingDelete(conversation)
                  }}
                  className="rounded-md p-2 text-faint transition-colors hover:bg-danger/10 hover:text-rose-300"
                  aria-label={`Delete ${conversation.title}`}
                >
                  <Trash2 className="size-4" />
                </button>
              </li>
            ))}
          </ul>

          {total > conversations.length ? (
            <p className="border-t border-line px-5 py-3 text-xs text-faint">
              Showing the {conversations.length} most recent conversations of{' '}
              {total}. Title search and filters apply to the loaded set.
            </p>
          ) : null}
        </Panel>
      )}

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete this conversation?"
        description={
          <>
            This permanently removes{' '}
            <span className="font-medium text-ink">
              “{pendingDelete?.title}”
            </span>
            , all {pluralize(pendingDelete?.message_count ?? 0, 'message')},
            and its vectors from ChromaDB. This cannot be undone.
            {deleteMutation.isError ? (
              <span className="mt-3 block rounded-md border border-danger/25 bg-danger/10 px-3 py-2 text-xs text-rose-200">
                {getErrorMessage(deleteMutation.error)}
              </span>
            ) : null}
          </>
        }
        confirmLabel="Delete conversation"
        loading={deleteMutation.isPending}
        destructive
        onConfirm={confirmDelete}
        onCancel={() => {
          if (!deleteMutation.isPending) {
            setPendingDelete(null)
            deleteMutation.reset()
          }
        }}
      />
    </div>
  )
}

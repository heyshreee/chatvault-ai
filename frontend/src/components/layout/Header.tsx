import { ChevronRight, Menu, Plus, Sparkles } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'

import { buttonStyles } from '../common/Button'

function pageTitle(pathname: string): string {
  if (pathname === '/') {
    return 'Dashboard'
  }

  if (pathname.startsWith('/chat')) {
    return 'AI Chat'
  }

  if (pathname === '/library') {
    return 'Library'
  }

  if (pathname.startsWith('/conversations/')) {
    return 'Conversation'
  }

  if (pathname.startsWith('/import')) {
    return 'Import'
  }

  if (pathname.startsWith('/settings')) {
    return 'Settings'
  }

  return 'Workspace'
}

interface HeaderProps {
  onOpenMenu: () => void
}

export function Header({ onOpenMenu }: HeaderProps) {
  const { pathname } = useLocation()
  const title = pageTitle(pathname)

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-canvas/85 backdrop-blur-md">
      <div className="flex h-16 items-center gap-3 px-4 sm:px-6 lg:px-8">
        <button
          type="button"
          onClick={onOpenMenu}
          className="rounded-md p-2 text-muted transition-colors hover:bg-panel-raised hover:text-ink lg:hidden"
          aria-label="Open navigation"
        >
          <Menu className="size-5" />
        </button>

        <div className="hidden min-w-0 items-center gap-2 text-xs text-faint sm:flex">
          <span>Workspace</span>
          <ChevronRight className="size-3.5" aria-hidden="true" />
          <span className="truncate font-medium text-ink">{title}</span>
        </div>

        <span className="truncate text-sm font-semibold text-ink sm:hidden">
          {title}
        </span>

        <div className="ml-auto flex items-center gap-2">
          <Link
            to="/import"
            className={buttonStyles(
              'secondary',
              'sm',
              'hidden sm:inline-flex',
            )}
          >
            <Plus className="size-3.5" aria-hidden="true" />
            Import
          </Link>
          <Link to="/chat" className={buttonStyles('primary', 'sm')}>
            <Sparkles className="size-3.5" aria-hidden="true" />
            Ask AI
          </Link>
        </div>
      </div>
    </header>
  )
}

import {
  Import,
  LayoutDashboard,
  Library,
  MessageSquareText,
  Settings,
  ShieldCheck,
  Vault,
  X,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'

import { cn } from '../../lib/cn'

interface NavItem {
  label: string
  to: string
  icon: LucideIcon
  active: (pathname: string) => boolean
}

const navItems: NavItem[] = [
  {
    label: 'Dashboard',
    to: '/',
    icon: LayoutDashboard,
    active: (pathname) => pathname === '/',
  },
  {
    label: 'AI Chat',
    to: '/chat',
    icon: MessageSquareText,
    active: (pathname) => pathname.startsWith('/chat'),
  },
  {
    label: 'Library',
    to: '/library',
    icon: Library,
    active: (pathname) =>
      pathname === '/library' || pathname.startsWith('/conversations/'),
  },
  {
    label: 'Import',
    to: '/import',
    icon: Import,
    active: (pathname) => pathname.startsWith('/import'),
  },
  {
    label: 'Settings',
    to: '/settings',
    icon: Settings,
    active: (pathname) => pathname.startsWith('/settings'),
  },
]

interface SidebarProps {
  open: boolean
  onClose: () => void
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const { pathname } = useLocation()

  return (
    <>
      {open ? (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-40 bg-black/70 backdrop-blur-[1px] lg:hidden"
          onClick={onClose}
        />
      ) : null}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-line bg-canvas-raised transition-transform duration-200 lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-16 items-center gap-3 border-b border-line px-5">
          <Link
            to="/"
            onClick={onClose}
            className="flex min-w-0 items-center gap-3 rounded-lg"
          >
            <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-accent/30 bg-accent-deep text-emerald-300">
              <Vault className="size-[18px]" aria-hidden="true" />
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-semibold tracking-tight text-ink">
                ChatVault AI
              </span>
              <span className="block text-[11px] text-faint">
                Local knowledge base
              </span>
            </span>
          </Link>
          <button
            type="button"
            onClick={onClose}
            className="ml-auto rounded-md p-1.5 text-faint transition-colors hover:bg-panel-raised hover:text-ink lg:hidden"
            aria-label="Close navigation"
          >
            <X className="size-4" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-5">
          <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-faint/80">
            Workspace
          </p>
          <ul className="space-y-1">
            {navItems.map((item) => {
              const isActive = item.active(pathname)
              const Icon = item.icon

              return (
                <li key={item.to}>
                  <Link
                    to={item.to}
                    onClick={onClose}
                    aria-current={isActive ? 'page' : undefined}
                    className={cn(
                      'group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
                      isActive
                        ? 'bg-panel-raised text-ink'
                        : 'text-muted hover:bg-panel/70 hover:text-ink',
                    )}
                  >
                    {isActive ? (
                      <span className="absolute inset-y-2 left-0 w-0.5 rounded-full bg-accent" />
                    ) : null}
                    <Icon
                      className={cn(
                        'size-[17px] shrink-0',
                        isActive
                          ? 'text-emerald-300'
                          : 'text-faint group-hover:text-muted',
                      )}
                      aria-hidden="true"
                    />
                    <span className="font-medium">{item.label}</span>
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>

        <div className="border-t border-line p-4">
          <div className="rounded-lg border border-line bg-panel/60 p-3.5">
            <div className="flex items-center gap-2 text-emerald-300">
              <ShieldCheck className="size-4" aria-hidden="true" />
              <p className="text-xs font-semibold text-ink">
                Private by default
              </p>
            </div>
            <p className="mt-2 text-[11px] leading-5 text-faint">
              Conversations, vectors, and answers stay on this machine.
            </p>
          </div>
          <p className="mt-3 px-1 text-[10px] uppercase tracking-[0.16em] text-faint/70">
            Local-first workspace
          </p>
        </div>
      </aside>
    </>
  )
}

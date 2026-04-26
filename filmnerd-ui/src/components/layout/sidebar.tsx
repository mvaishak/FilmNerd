'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import useSWR from 'swr'
import { api } from '@/lib/api'

const NAV_ITEMS = [
  { href: '/chat', label: 'chat' },
  { href: '/taste', label: 'taste' },
  { href: '/log', label: 'log' },
  { href: '/browse', label: 'browse' },
]

export function Sidebar() {
  const pathname = usePathname()
  const { data: health } = useSWR('health', api.getHealth, { refreshInterval: 30000 })

  return (
    <aside className="w-[240px] flex-shrink-0 border-r border-[#27272a] flex flex-col h-screen sticky top-0">
      <div className="px-6 pt-8 pb-6">
        <span className="text-sm font-mono text-[#71717a] tracking-widest uppercase">
          filmnerd
        </span>
      </div>

      <nav className="flex-1 px-6">
        <ul className="space-y-1">
          {NAV_ITEMS.map(({ href, label }) => {
            const active = pathname === href || pathname.startsWith(href + '/')
            return (
              <li key={href}>
                <Link
                  href={href}
                  className={[
                    'block text-sm py-1 pl-3',
                    active
                      ? 'text-white border-l border-white'
                      : 'text-[#71717a] border-l border-transparent hover:text-white',
                  ].join(' ')}
                >
                  {label}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      <div className="px-6 pb-8 space-y-1">
        <p className="text-xs font-mono text-[#71717a]">
          {health?.corpus_size ?? '—'} films
        </p>
        <p className="text-xs font-mono text-[#3f3f46]">
          model v{health?.model_version ?? '—'}
        </p>
      </div>
    </aside>
  )
}

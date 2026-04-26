'use client'

import { useState } from 'react'
import { ChevronUp, ChevronDown, ChevronLeft, ChevronRight } from 'lucide-react'
import { posterUrl } from '@/lib/api'
import type { CraftAnnotation } from '@/lib/types'

type SortKey = 'title' | 'year' | 'user_rating'
type SortDir = 'asc' | 'desc'

interface FilmTableProps {
  films: CraftAnnotation[]
  total: number
  page: number
  perPage: number
  onPageChange: (page: number) => void
}

const COLS: { key: keyof CraftAnnotation; label: string; sortable?: boolean }[] = [
  { key: 'title', label: 'title', sortable: true },
  { key: 'year', label: 'year', sortable: true },
  { key: 'user_rating', label: 'rating', sortable: true },
  { key: 'pacing_signature', label: 'pacing' },
  { key: 'tone_primary', label: 'tone' },
  { key: 'body_experience', label: 'body' },
  { key: 'director_lineage', label: 'dir. lineage' },
]

export function FilmTable({ films, total, page, perPage, onPageChange }: FilmTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('title')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [search, setSearch] = useState('')

  const filtered = search
    ? films.filter(f => f.title?.toLowerCase().includes(search.toLowerCase()))
    : films

  const sorted = [...filtered].sort((a, b) => {
    const av = a[sortKey]
    const bv = b[sortKey]
    if (av == null && bv == null) return 0
    if (av == null) return 1
    if (bv == null) return -1
    const cmp = av < bv ? -1 : av > bv ? 1 : 0
    return sortDir === 'asc' ? cmp : -cmp
  })

  const totalPages = Math.ceil(total / perPage)

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  function SortIcon({ col }: { col: SortKey }) {
    if (sortKey !== col) return null
    return sortDir === 'asc'
      ? <ChevronUp size={10} className="inline ml-1" />
      : <ChevronDown size={10} className="inline ml-1" />
  }

  return (
    <div className="flex-1 space-y-4">
      <input
        type="text"
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder="filter by title"
        className="w-full bg-transparent border-b border-[#27272a] text-sm py-2 outline-none placeholder-[#3f3f46]"
      />

      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-[#27272a]">
              <th className="w-8 pb-2" />
              {COLS.map(col => (
                <th
                  key={col.key}
                  className={[
                    'text-left text-xs uppercase tracking-[0.12em] text-[#71717a] pb-2 pr-4 font-normal',
                    col.sortable ? 'cursor-pointer hover:text-white' : '',
                  ].join(' ')}
                  onClick={col.sortable ? () => toggleSort(col.key as SortKey) : undefined}
                >
                  {col.label}
                  {col.sortable && <SortIcon col={col.key as SortKey} />}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map(film => (
              <FilmRow key={film.tmdb_id} film={film} />
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center gap-4 pt-4">
          <button
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            className="text-xs font-mono text-[#71717a] disabled:opacity-30 flex items-center gap-1"
          >
            <ChevronLeft size={12} /> previous
          </button>
          <span className="text-xs font-mono text-[#71717a]">
            page {page} of {totalPages}
          </span>
          <button
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            className="text-xs font-mono text-[#71717a] disabled:opacity-30 flex items-center gap-1"
          >
            next <ChevronRight size={12} />
          </button>
        </div>
      )}
    </div>
  )
}

function FilmRow({ film }: { film: CraftAnnotation }) {
  const url = posterUrl(film.poster_path, 'w92')

  function truncate(val: string | null | undefined) {
    if (!val) return '—'
    const s = val.replace(/_/g, ' ')
    return s.length > 18 ? s.slice(0, 17) + '…' : s
  }

  return (
    <tr className="border-b border-[#27272a] group">
      <td className="py-1 pr-2 w-8">
        {url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={url}
            alt={film.title}
            width={32}
            height={48}
            className="object-cover"
            style={{ width: 32, height: 48 }}
          />
        ) : (
          <div className="w-8 h-12 bg-[#27272a]" />
        )}
      </td>
      <td className="py-1 pr-4 text-sm group-hover:underline underline-offset-4 decoration-1">
        {film.title?.toLowerCase()}
      </td>
      <td className="py-1 pr-4 text-xs font-mono text-[#71717a]">{film.year ?? '—'}</td>
      <td className="py-1 pr-4 text-sm font-mono text-white">
        {film.user_rating != null ? film.user_rating.toFixed(1) : '—'}
      </td>
      <td
        className="py-1 pr-4 text-xs font-mono text-[#71717a]"
        title={film.pacing_signature ?? ''}
      >
        {truncate(film.pacing_signature)}
      </td>
      <td
        className="py-1 pr-4 text-xs font-mono text-[#71717a]"
        title={film.tone_primary ?? ''}
      >
        {truncate(film.tone_primary)}
      </td>
      <td
        className="py-1 pr-4 text-xs font-mono text-[#71717a]"
        title={film.body_experience ?? ''}
      >
        {truncate(film.body_experience)}
      </td>
      <td
        className="py-1 pr-4 text-xs font-mono text-[#71717a]"
        title={film.director_lineage ?? ''}
      >
        {truncate(film.director_lineage)}
      </td>
    </tr>
  )
}

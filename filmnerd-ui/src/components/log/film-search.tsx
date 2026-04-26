'use client'

import { useState, useRef, useEffect } from 'react'
import { X } from 'lucide-react'
import { api } from '@/lib/api'
import type { FilmSearchResult } from '@/lib/types'

interface FilmSearchProps {
  onSelect: (film: FilmSearchResult | null) => void
  selected: FilmSearchResult | null
}

export function FilmSearch({ onSelect, selected }: FilmSearchProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<FilmSearchResult[]>([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const timer = useRef<NodeJS.Timeout>()

  useEffect(() => {
    if (!query.trim()) {
      setResults([])
      setOpen(false)
      return
    }
    clearTimeout(timer.current)
    timer.current = setTimeout(async () => {
      setLoading(true)
      try {
        const data = await api.searchFilms(query)
        setResults(data)
        setOpen(true)
      } finally {
        setLoading(false)
      }
    }, 300)
    return () => clearTimeout(timer.current)
  }, [query])

  if (selected) {
    return (
      <div className="flex items-center gap-3 border border-[#27272a] p-3">
        <span className="text-sm font-mono flex-1">
          {selected.title} ({selected.year})
        </span>
        <button onClick={() => onSelect(null)} className="text-[#71717a] hover:text-white">
          <X size={12} />
        </button>
      </div>
    )
  }

  return (
    <div className="relative">
      <input
        type="text"
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder="search by title"
        className="w-full bg-transparent border border-[#27272a] px-3 py-2 text-sm font-mono outline-none placeholder-[#3f3f46] rounded-sm"
      />
      {loading && (
        <span className="absolute right-3 top-2.5 text-xs text-[#71717a] font-mono">…</span>
      )}
      {open && results.length > 0 && (
        <div className="absolute z-10 w-full mt-1 bg-[#09090b] border border-[#27272a]">
          {results.map(r => (
            <button
              key={r.tmdb_id}
              className="w-full text-left px-3 py-2 text-sm font-mono text-[#71717a] hover:text-white hover:bg-[#27272a]"
              onClick={() => {
                onSelect(r)
                setQuery('')
                setOpen(false)
              }}
            >
              {r.title} ({r.year}){r.in_corpus && ' ·'}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

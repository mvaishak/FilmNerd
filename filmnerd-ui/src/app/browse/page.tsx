'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { api } from '@/lib/api'
import type { CorpusFilters, CorpusResponse } from '@/lib/types'
import { FilterPanel } from '@/components/browse/filter-panel'
import { FilmTable } from '@/components/browse/film-table'
import { LoadingSkeleton } from '@/components/shared/loading-skeleton'

export default function BrowsePage() {
  const [filters, setFilters] = useState<CorpusFilters>({})
  const [page, setPage] = useState(1)

  const fetcher = () => api.getCorpus(filters, page)
  const key = JSON.stringify({ filters, page })

  const { data, isLoading, error } = useSWR<CorpusResponse>(key, fetcher)

  function handleFilterChange(newFilters: CorpusFilters) {
    setFilters(newFilters)
    setPage(1)
  }

  return (
    <div className="px-8 py-12 space-y-8">
      <h1 className="text-2xl font-light lowercase tracking-[-0.05em]">browse</h1>

      <div className="flex gap-8">
        {data && (
          <FilterPanel
            films={data.films}
            filters={filters}
            onFilterChange={handleFilterChange}
          />
        )}

        <div className="flex-1">
          {isLoading && (
            <div className="space-y-2">
              {Array.from({ length: 10 }).map((_, i) => (
                <LoadingSkeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          )}

          {error && (
            <p className="text-xs text-[#71717a] font-mono">
              failed to load corpus — <button onClick={() => setFilters({})}>retry</button>
            </p>
          )}

          {data && (
            <FilmTable
              films={data.films}
              total={data.total}
              page={data.page}
              perPage={data.per_page}
              onPageChange={setPage}
            />
          )}
        </div>
      </div>
    </div>
  )
}

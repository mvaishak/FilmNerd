'use client'

import type { CorpusFilters, CraftAnnotation } from '@/lib/types'

const FILTER_DIMS: { key: keyof CorpusFilters; label: string }[] = [
  { key: 'pacing_signature', label: 'pacing' },
  { key: 'tone_primary', label: 'tone' },
  { key: 'body_experience', label: 'body' },
  { key: 'reality_register', label: 'reality' },
  { key: 'moral_complexity', label: 'moral' },
  { key: 'production_register', label: 'production' },
  { key: 'director_lineage', label: 'director lineage' },
  { key: 'ending_valence', label: 'ending' },
]

interface FilterPanelProps {
  films: CraftAnnotation[]
  filters: CorpusFilters
  onFilterChange: (filters: CorpusFilters) => void
}

export function FilterPanel({ films, filters, onFilterChange }: FilterPanelProps) {
  const hasFilters = Object.values(filters).some(v => v && v !== '')

  function countValues(key: keyof CraftAnnotation) {
    const counts: Record<string, number> = {}
    for (const film of films) {
      const val = film[key] as string | null
      if (val) counts[val] = (counts[val] ?? 0) + 1
    }
    return counts
  }

  return (
    <div className="w-[200px] flex-shrink-0 border-r border-[#27272a] pr-6 space-y-6">
      {hasFilters && (
        <button
          onClick={() => onFilterChange({})}
          className="text-xs text-[#71717a] underline underline-offset-4 decoration-1"
        >
          clear filters
        </button>
      )}
      {FILTER_DIMS.map(({ key, label }) => {
        const counts = countValues(key as keyof CraftAnnotation)
        const values = Object.keys(counts).sort()
        const activeVal = filters[key]

        return (
          <div key={key} className="space-y-2">
            <p className="text-xs uppercase tracking-[0.12em] text-[#71717a]">{label}</p>
            <div className="space-y-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <span
                  className={[
                    'w-3 h-3 rounded-full border border-[#27272a] flex-shrink-0',
                    !activeVal ? 'bg-white' : '',
                  ].join(' ')}
                />
                <span className="text-xs font-mono text-[#71717a]">all</span>
              </label>
              {values.map((val) => (
                <label
                  key={val}
                  className="flex items-center gap-2 cursor-pointer"
                  onClick={() => onFilterChange({ ...filters, [key]: activeVal === val ? undefined : val })}
                >
                  <span
                    className={[
                      'w-3 h-3 rounded-full border border-[#27272a] flex-shrink-0',
                      activeVal === val ? 'bg-white' : '',
                    ].join(' ')}
                  />
                  <span className="text-xs font-mono text-[#71717a]">
                    {val.replace(/_/g, ' ')}
                  </span>
                  <span className="text-xs font-mono text-[#3f3f46] ml-auto">
                    {counts[val]}
                  </span>
                </label>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

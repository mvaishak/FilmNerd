'use client'

import { useState } from 'react'
import { api } from '@/lib/api'
import type { FilmSearchResult, LogResult } from '@/lib/types'
import { FilmSearch } from '@/components/log/film-search'
import { RatingInput } from '@/components/log/rating-input'
import { AnnotationPreview } from '@/components/log/annotation-preview'

export default function LogPage() {
  const [selected, setSelected] = useState<FilmSearchResult | null>(null)
  const [rating, setRating] = useState<number | null>(null)
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<LogResult | null>(null)
  const [confirmMsg, setConfirmMsg] = useState('')

  async function handleSubmit() {
    if (!selected || rating === null) return
    setSubmitting(true)
    try {
      const res: LogResult = await api.logWatch(selected.tmdb_id, rating, notes || undefined)
      setResult(res)
      setConfirmMsg('logged')
      setTimeout(() => {
        setConfirmMsg('')
        setSelected(null)
        setRating(null)
        setNotes('')
        setResult(null)
      }, 3000)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="px-8 py-12">
      <div className="max-w-[560px] space-y-8">
        <h1 className="text-2xl font-light lowercase tracking-[-0.05em]">log a watch</h1>
        <div className="border-b border-[#27272a]" />

        <FilmSearch selected={selected} onSelect={setSelected} />

        {selected && <AnnotationPreview film={selected} />}

        <RatingInput value={rating} onChange={setRating} />

        <textarea
          value={notes}
          onChange={e => setNotes(e.target.value)}
          placeholder="notes (optional)"
          rows={3}
          className="w-full bg-transparent border border-[#27272a] text-sm p-3 outline-none placeholder-[#3f3f46] resize-none rounded-sm"
        />

        <button
          onClick={handleSubmit}
          disabled={!selected || rating === null || submitting}
          className="border border-[#27272a] px-4 py-2 text-xs font-mono text-[#71717a] hover:text-white hover:border-white disabled:opacity-30"
        >
          {submitting ? 'logging...' : confirmMsg || 'log watch'}
        </button>

        {result && result.predicted_rating != null && (
          <div className="space-y-1 pt-4">
            <div className="flex gap-8">
              <span className="text-xs font-mono text-[#71717a] w-20">predicted</span>
              <span className="text-xs font-mono text-white">{result.predicted_rating.toFixed(1)}</span>
            </div>
            <div className="flex gap-8">
              <span className="text-xs font-mono text-[#71717a] w-20">actual</span>
              <span className="text-xs font-mono text-white">{result.rating.toFixed(1)}</span>
            </div>
            <div className="flex gap-8">
              <span className="text-xs font-mono text-[#71717a] w-20">error</span>
              <span className="text-xs font-mono text-white">
                {result.prediction_error != null
                  ? (result.prediction_error > 0 ? '+' : '') + result.prediction_error.toFixed(1)
                  : '—'}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

import type { CorpusFilters, Message } from './types'

const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function buildParams(filters?: CorpusFilters, page = 1): string {
  const p = new URLSearchParams()
  if (filters) {
    for (const [k, v] of Object.entries(filters)) {
      if (v) p.set(k, v)
    }
  }
  p.set('page', String(page))
  return p.toString()
}

export const api = {
  chat: (message: string, history: Message[]) =>
    fetch(`${BASE}/chat`, {
      method: 'POST',
      body: JSON.stringify({ message, history }),
      headers: { 'Content-Type': 'application/json' },
    }),

  getTasteProfile: () =>
    fetch(`${BASE}/taste/profile`).then(r => r.json()),

  retrainTasteModel: () =>
    fetch(`${BASE}/taste/retrain`, { method: 'POST' }).then(r => r.json()),

  searchFilms: (q: string) =>
    fetch(`${BASE}/search?q=${encodeURIComponent(q)}`).then(r => r.json()),

  logWatch: (tmdbId: number, rating: number, notes?: string) =>
    fetch(`${BASE}/log`, {
      method: 'POST',
      body: JSON.stringify({ tmdb_id: tmdbId, rating, notes }),
      headers: { 'Content-Type': 'application/json' },
    }).then(r => r.json()),

  getCorpus: (filters?: CorpusFilters, page = 1) =>
    fetch(`${BASE}/corpus?${buildParams(filters, page)}`).then(r => r.json()),

  getFilm: (tmdbId: number) =>
    fetch(`${BASE}/films/${tmdbId}`).then(r => r.json()),

  getHealth: () =>
    fetch(`${BASE}/health`).then(r => r.json()),
}

export function posterUrl(posterPath: string | null, size: 'w92' | 'w342' = 'w342'): string | null {
  if (!posterPath) return null
  return `https://image.tmdb.org/t/p/${size}${posterPath}`
}

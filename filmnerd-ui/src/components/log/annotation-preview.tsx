import { FilmPoster } from '@/components/shared/film-poster'
import type { FilmSearchResult } from '@/lib/types'
import { formatDimension } from '@/lib/utils'

const PREVIEW_DIMS = [
  'pacing_signature', 'tone_primary', 'body_experience',
  'moral_complexity', 'ending_valence',
] as const

interface AnnotationPreviewProps {
  film: FilmSearchResult
}

export function AnnotationPreview({ film }: AnnotationPreviewProps) {
  const ann = film.annotation

  return (
    <div className="flex gap-6 border border-[#27272a] p-6">
      <FilmPoster
        posterPath={film.poster_path}
        title={film.title}
        size="w342"
        className="w-[80px]"
      />
      <div className="flex-1 space-y-3">
        {ann ? (
          <>
            <p className="text-xs font-mono text-[#71717a]">already in corpus</p>
            <div className="space-y-1">
              {PREVIEW_DIMS.map(dim => (
                <div key={dim} className="flex gap-4">
                  <span className="text-xs font-mono text-[#71717a] w-32">{dim.replace(/_/g, ' ')}</span>
                  <span className="text-xs font-mono text-white">
                    {formatDimension((ann as Record<string, unknown>)[dim] as string)}
                  </span>
                </div>
              ))}
            </div>
            {ann.user_rating != null && (
              <p className="text-xs font-mono text-[#71717a] pt-2">
                your previous rating{' '}
                <span className="text-white">{ann.user_rating.toFixed(1)}</span>
              </p>
            )}
          </>
        ) : (
          <p className="text-xs font-mono text-[#71717a]">
            new film — will be annotated after logging
          </p>
        )}
      </div>
    </div>
  )
}

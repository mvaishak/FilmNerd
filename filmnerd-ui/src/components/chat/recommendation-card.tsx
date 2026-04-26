import { FilmPoster } from '@/components/shared/film-poster'
import type { Recommendation } from '@/lib/types'
import { formatDimension } from '@/lib/utils'

interface RecommendationCardProps {
  rec: Recommendation
}

export function RecommendationCard({ rec }: RecommendationCardProps) {
  const dims = rec.craft_dimensions
  const dimEntries = Object.entries(dims).filter(([, v]) => v != null).slice(0, 4)

  return (
    <div className="border border-[#27272a] my-4">
      <div className="flex gap-6 p-6">
        <div className="flex-shrink-0 self-stretch">
          <FilmPoster
            posterPath={rec.poster_path}
            title={rec.title}
            size="w342"
            className="w-[100px] h-full"
          />
        </div>
        <div className="flex-1 min-w-0 space-y-4">
          <div>
            <p className="text-base lowercase tracking-[-0.05em]">{rec.title}</p>
            <p className="text-sm font-mono text-[#71717a]">{rec.year}</p>
          </div>
          <p className="text-sm leading-7 text-[#71717a]">{rec.explanation}</p>

          {dimEntries.length > 0 && (
            <div className="border-t border-[#27272a] pt-4">
              <p className="text-xs font-mono text-[#71717a]">
                {dimEntries.map(([k, v]) => (
                  <span key={k} className="mr-4">
                    {k.replace(/_/g, ' ')} · {formatDimension(v as string)}
                  </span>
                ))}
              </p>
            </div>
          )}

          {rec.predicted_rating != null && (
            <div className="border-t border-[#27272a] pt-4 mt-4">
              <p className="text-xs font-mono text-[#71717a]">
                predicted rating{' '}
                <span className="text-base font-mono text-white">
                  {rec.predicted_rating.toFixed(1)}
                </span>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

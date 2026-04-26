import Image from 'next/image'
import { Film } from 'lucide-react'
import { posterUrl } from '@/lib/api'

interface FilmPosterProps {
  posterPath: string | null
  title: string
  size: 'w92' | 'w342'
  className?: string
}

export function FilmPoster({ posterPath, title, size, className = '' }: FilmPosterProps) {
  const url = posterUrl(posterPath, size)
  const dims = size === 'w92' ? { width: 92, height: 138 } : { width: 342, height: 513 }

  if (!url) {
    return (
      <div
        className={`bg-[#09090b] border border-[#27272a] flex items-center justify-center flex-shrink-0 ${className}`}
        style={{ width: dims.width, aspectRatio: '2/3' }}
      >
        <Film size={16} className="text-[#3f3f46]" />
      </div>
    )
  }

  return (
    <div
      className={`relative flex-shrink-0 overflow-hidden ${className}`}
      style={{ width: dims.width, aspectRatio: '2/3' }}
    >
      <Image
        src={url}
        alt={title}
        fill
        className="object-cover"
        unoptimized={false}
      />
    </div>
  )
}

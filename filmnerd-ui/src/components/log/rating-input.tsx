'use client'

const RATINGS = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]

interface RatingInputProps {
  value: number | null
  onChange: (rating: number) => void
}

export function RatingInput({ value, onChange }: RatingInputProps) {
  return (
    <div className="flex gap-4 flex-wrap">
      {RATINGS.map(r => (
        <button
          key={r}
          onClick={() => onChange(r)}
          className={[
            'text-sm font-mono pb-1',
            value === r
              ? 'text-white border-b border-white'
              : 'text-[#3f3f46] hover:text-[#71717a]',
          ].join(' ')}
        >
          {r.toFixed(1)}
        </button>
      ))}
    </div>
  )
}

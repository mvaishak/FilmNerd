import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatRating(rating: number | null | undefined): string {
  if (rating == null) return '—'
  return rating.toFixed(1)
}

export function formatDimension(value: string | null | undefined): string {
  if (!value) return '—'
  return value.replace(/_/g, ' ')
}

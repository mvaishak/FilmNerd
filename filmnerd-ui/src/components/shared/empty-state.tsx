interface EmptyStateProps {
  message: string
}

export function EmptyState({ message }: EmptyStateProps) {
  return (
    <div className="flex items-center justify-center py-24">
      <p className="text-sm text-[#71717a]">{message}</p>
    </div>
  )
}

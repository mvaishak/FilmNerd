interface LoadingSkeletonProps {
  className?: string
}

export function LoadingSkeleton({ className = '' }: LoadingSkeletonProps) {
  return (
    <div className={`bg-[#27272a] animate-pulse ${className}`} />
  )
}

import type { Message } from '@/lib/types'
import { RecommendationCard } from './recommendation-card'

interface MessageBubbleProps {
  message: Message
  streaming?: boolean
}

export function MessageBubble({ message, streaming }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex flex-col items-end gap-1">
        <p className="text-sm">{message.content}</p>
        <span className="text-xs font-mono text-[#71717a]">
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="text-sm leading-7">
        {message.content}
        {streaming && <span className="cursor-blink ml-0.5">_</span>}
      </div>
      {message.recommendations?.map(rec => (
        <RecommendationCard key={rec.tmdb_id ?? rec.title} rec={rec} />
      ))}
    </div>
  )
}

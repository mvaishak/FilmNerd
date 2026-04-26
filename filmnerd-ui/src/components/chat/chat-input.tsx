'use client'

import { useRef, useEffect } from 'react'
import { ArrowRight } from 'lucide-react'
import useSWR from 'swr'
import { api } from '@/lib/api'

interface ChatInputProps {
  value: string
  onChange: (v: string) => void
  onSubmit: () => void
  disabled?: boolean
}

export function ChatInput({ value, onChange, onSubmit, disabled }: ChatInputProps) {
  const ref = useRef<HTMLTextAreaElement>(null)
  const { data: health } = useSWR('health', api.getHealth, { revalidateOnFocus: false })

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 96) + 'px'
  }, [value])

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!disabled && value.trim()) onSubmit()
    }
  }

  return (
    <div className="border-t border-[#27272a] px-8 py-4 space-y-2">
      <div className="flex items-end gap-3">
        <textarea
          ref={ref}
          rows={1}
          value={value}
          onChange={e => onChange(e.target.value)}
          onKeyDown={handleKey}
          placeholder="ask anything"
          disabled={disabled}
          className="flex-1 bg-transparent text-sm outline-none resize-none placeholder-[#3f3f46] leading-6"
          style={{ maxHeight: 96 }}
        />
        <button
          onClick={onSubmit}
          disabled={disabled || !value.trim()}
          className="flex-shrink-0 pb-0.5"
        >
          <ArrowRight
            size={14}
            className={value.trim() ? 'text-white' : 'text-[#3f3f46]'}
          />
        </button>
      </div>
      <p className="text-xs font-mono text-[#3f3f46]">
        taste model v2 · {health?.corpus_size ?? '—'} films · gradient boosting
      </p>
    </div>
  )
}

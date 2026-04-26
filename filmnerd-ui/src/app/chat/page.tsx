'use client'

import { useState, useRef, useEffect } from 'react'
import { api } from '@/lib/api'
import type { Message, Recommendation } from '@/lib/types'
import { MessageBubble } from '@/components/chat/message-bubble'
import { ChatInput } from '@/components/chat/chat-input'
import useSWR from 'swr'

const EXAMPLE_PROMPTS = [
  'slow and visually dense',
  'something like jeanne dielman but less punishing',
  'a film with an ambiguous ending i haven\'t seen',
]

function makeId() {
  return Math.random().toString(36).slice(2)
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const { data: health } = useSWR('health-chat', api.getHealth)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [messages])

  async function sendMessage(text: string) {
    if (!text.trim() || streaming) return

    const userMsg: Message = {
      id: makeId(),
      role: 'user',
      content: text.trim(),
      timestamp: new Date().toISOString(),
    }

    const assistantId = makeId()
    const assistantMsg: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      recommendations: [],
      timestamp: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMsg, assistantMsg])
    setInput('')
    setStreaming(true)

    try {
      const response = await api.chat(text.trim(), messages)
      const reader = response.body?.getReader()
      if (!reader) return

      const decoder = new TextDecoder()
      let buf = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop() ?? ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const event = JSON.parse(line.slice(6))
            if (event.type === 'token') {
              setMessages(prev => prev.map(m =>
                m.id === assistantId
                  ? { ...m, content: m.content + event.content }
                  : m
              ))
            } else if (event.type === 'recommendation') {
              const rec: Recommendation = event.data
              setMessages(prev => prev.map(m =>
                m.id === assistantId
                  ? { ...m, recommendations: [...(m.recommendations ?? []), rec] }
                  : m
              ))
            } else if (event.type === 'done') {
              break
            }
          } catch {}
        }
      }
    } catch (e) {
      setMessages(prev => prev.map(m =>
        m.id === assistantId
          ? { ...m, content: `Error: ${e}` }
          : m
      ))
    } finally {
      setStreaming(false)
    }
  }

  function clearConversation() {
    setMessages([])
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="flex items-center justify-between px-8 py-6 border-b border-[#27272a]">
        <h1 className="text-2xl font-light lowercase tracking-[-0.05em]">chat</h1>
        {messages.length > 0 && (
          <button
            onClick={clearConversation}
            className="text-xs text-[#71717a] underline underline-offset-4 decoration-1 hover:text-white"
          >
            new conversation
          </button>
        )}
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-8 py-8 space-y-8">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-6">
            <p className="text-2xl font-light lowercase tracking-[-0.05em]">
              what do you want to watch?
            </p>
            <div className="space-y-2 text-center">
              {EXAMPLE_PROMPTS.map(p => (
                <button
                  key={p}
                  onClick={() => sendMessage(p)}
                  className="block text-sm text-[#71717a] hover:text-white w-full"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              streaming={streaming && i === messages.length - 1 && msg.role === 'assistant'}
            />
          ))
        )}
      </div>

      {/* Input */}
      <ChatInput
        value={input}
        onChange={setInput}
        onSubmit={() => sendMessage(input)}
        disabled={streaming}
      />
    </div>
  )
}

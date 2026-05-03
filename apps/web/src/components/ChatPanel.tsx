import { useState, useRef, useEffect } from 'react'
import { Send, Sparkles, Bot, User, Loader2 } from 'lucide-react'
import { usePipeline, usePipelineActions } from '../state/pipelineStore'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  status?: 'pending' | 'done' | 'error'
}

const SUGGESTIONS = [
  'Make the intro more dramatic',
  'Add a title card before the demo',
  'Speed up the middle section',
  'Add background music',
  'Remove the last beat',
  'Make it shorter overall',
]

export function ChatPanel() {
  const { projectId, plan, manifest, pipelineStages } = usePipeline()
  const { editPlanPrompt } = usePipelineActions()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const isEditing = pipelineStages['edit-plan'] === 'running'

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (!isEditing) {
      setMessages((prev) => {
        const last = prev[prev.length - 1]
        if (last?.role === 'assistant' && last.status === 'pending') {
          const beatCount = plan?.beats?.length ?? 0
          const summary = plan
            ? `Done! Plan updated — now ${beatCount} beat${beatCount === 1 ? '' : 's'}. Check the timeline to see changes.`
            : 'Done! The plan has been updated.'
          return prev.map((m) =>
            m.id === last.id ? { ...m, status: 'done' as const, content: summary } : m
          )
        }
        return prev
      })
    }
  }, [isEditing, plan])

  const buildHistory = (currentMessages: ChatMessage[]): { role: 'user' | 'assistant'; content: string }[] => {
    return currentMessages
      .filter((m) => m.status !== 'pending')
      .map((m) => ({ role: m.role, content: m.content }))
  }

  const handleSend = async (text?: string) => {
    const msg = (text ?? input).trim()
    if (!msg || !projectId || !plan) return

    const userMsg: ChatMessage = {
      id: `msg_${Date.now()}_u`,
      role: 'user',
      content: msg,
      timestamp: new Date().toISOString(),
    }
    const assistantMsg: ChatMessage = {
      id: `msg_${Date.now()}_a`,
      role: 'assistant',
      content: 'Working on it...',
      timestamp: new Date().toISOString(),
      status: 'pending',
    }

    const history = buildHistory(messages)
    setMessages((prev) => [...prev, userMsg, assistantMsg])
    setInput('')

    try {
      await editPlanPrompt(msg, history)
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsg.id ? { ...m, status: 'error' as const, content: 'Something went wrong. Try again.' } : m
        )
      )
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const disabled = !projectId || !plan || isEditing

  const contextLine = plan
    ? `${plan.beats.length} beats · ${manifest?.blocks?.length ?? 0} blocks`
    : null

  return (
    <div className="chat-panel">
      {contextLine && (
        <div className="chat-context-bar">
          Current: {plan?.title ?? 'Untitled'} — {contextLine}
        </div>
      )}

      <div className="chat-messages" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="chat-empty">
            <Sparkles size={24} className="chat-empty-icon" />
            <h4>Edit with AI</h4>
            <p>Describe changes to your video plan in natural language. The AI remembers your conversation.</p>
            {plan && (
              <div className="chat-suggestions">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    className="chat-suggestion-chip"
                    onClick={() => handleSend(s)}
                    disabled={disabled}
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}
            {!plan && (
              <p className="chat-hint">Run the pipeline first to generate a plan.</p>
            )}
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`chat-message chat-message-${msg.role}`}>
            <div className="chat-avatar">
              {msg.role === 'user' ? <User size={14} /> : <Bot size={14} />}
            </div>
            <div className="chat-bubble">
              {msg.status === 'pending' && (
                <Loader2 size={12} className="chat-spinner" />
              )}
              <span>{msg.content}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="chat-input-area">
        <textarea
          ref={inputRef}
          className="chat-input"
          placeholder={disabled ? 'Generate a plan first...' : 'Describe a change...'}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
        />
        <button
          className="chat-send-btn"
          onClick={() => handleSend()}
          disabled={disabled || !input.trim()}
          aria-label="Send"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  )
}

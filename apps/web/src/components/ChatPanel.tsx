import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { Send, Sparkles, Bot, User, Loader2, PlusSquare } from 'lucide-react'
import { usePipeline, usePipelineActions } from '../state/pipelineStore'
import { DiffReviewBar } from './DiffReviewBar'
import { computePlanDiff } from '../utils/planDiff'

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

function chatStorageKey(projectId: string): string {
  return `directorloop:chat:${projectId}`
}

function loadChatHistory(projectId: string): ChatMessage[] {
  try {
    const raw = localStorage.getItem(chatStorageKey(projectId))
    if (!raw) return []
    return JSON.parse(raw)
  } catch {
    return []
  }
}

function saveChatHistory(projectId: string, messages: ChatMessage[]) {
  try {
    const persistable = messages.filter((m) => m.status !== 'pending')
    localStorage.setItem(chatStorageKey(projectId), JSON.stringify(persistable))
  } catch {
    // localStorage full or unavailable; skip persistence
  }
}

export function ChatPanel() {
  const { projectId, plan, manifest, pipelineStages, proposedPlan } = usePipeline()
  const { editPlanPreview, acceptProposedPlan, rejectProposedPlan } = usePipelineActions()
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const isProjectLoading = useRef(false)

  const isEditing = pipelineStages['edit-plan'] === 'running'

  useEffect(() => {
    if (projectId) {
      isProjectLoading.current = true
      setMessages(loadChatHistory(projectId))
    } else {
      setMessages([])
    }
  }, [projectId])

  useEffect(() => {
    if (isProjectLoading.current) {
      isProjectLoading.current = false
      return
    }
    if (projectId) {
      saveChatHistory(projectId, messages)
    }
  }, [messages, projectId])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (!isEditing) {
      setMessages((prev) => {
        const last = prev[prev.length - 1]
        if (last?.role === 'assistant' && last.status === 'pending') {
          // If proposedPlan is null at this point, this is the accept flow
          // (proposedPlan was cleared by acceptProposedPlan before the job ran).
          if (!proposedPlan) {
            return prev.map((m) =>
              m.id === last.id ? { ...m, status: 'done' as const, content: 'Changes applied. Rebuilding manifest...' } : m,
            )
          }
          const proposedBeatCount = proposedPlan.beats.length
          const summary = `I drafted an updated plan with ${proposedBeatCount} beat${proposedBeatCount === 1 ? '' : 's'}. Review it below.`
          return prev.map((m) =>
            m.id === last.id ? { ...m, status: 'done' as const, content: summary } : m,
          )
        }
        return prev
      })
    }
  }, [isEditing, proposedPlan])

  const buildHistory = (currentMessages: ChatMessage[]): { role: 'user' | 'assistant'; content: string }[] => {
    return currentMessages
      .filter((m) => m.status !== 'pending')
      .map((m) => ({ role: m.role, content: m.content }))
  }

  const handleSend = useCallback(async (text?: string) => {
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
      content: 'Previewing plan changes...',
      timestamp: new Date().toISOString(),
      status: 'pending',
    }

    const history = buildHistory(messages)
    setMessages((prev) => [...prev, userMsg, assistantMsg])
    setInput('')
    if (inputRef.current) inputRef.current.style.height = 'auto'

    try {
      await editPlanPreview(msg, history)
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsg.id ? { ...m, status: 'error' as const, content: 'Something went wrong. Try again.' } : m,
        ),
      )
    }
  }, [input, projectId, plan, messages, editPlanPreview])

  const handleNewChat = useCallback(() => {
    if (projectId) {
      localStorage.removeItem(chatStorageKey(projectId))
    }
    setMessages([])
  }, [projectId])

  const autoResize = (el: HTMLTextAreaElement) => {
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSend()
    }
  }

  const diff = useMemo(
    () => (plan && proposedPlan ? computePlanDiff(plan, proposedPlan) : null),
    [plan, proposedPlan],
  )
  const currentDuration = useMemo(
    () => plan?.beats.reduce((s, b) => s + b.duration, 0) ?? 0,
    [plan],
  )
  const proposedDuration = useMemo(
    () => proposedPlan?.beats.reduce((s, b) => s + b.duration, 0) ?? currentDuration,
    [proposedPlan, currentDuration],
  )

  const disabled = !projectId || !plan || isEditing
  const contextLine = plan
    ? `${plan.beats.length} beats · ${manifest?.blocks?.length ?? 0} blocks`
    : null

  return (
    <div className="chat-panel">
      {contextLine && (
        <div className="chat-context-bar">
          <span>Current: {plan?.title ?? 'Untitled'} - {contextLine}</span>
          <button className="chat-new-btn" onClick={handleNewChat} title="Start new chat">
            <PlusSquare size={12} /> New
          </button>
        </div>
      )}

      <div className="chat-messages" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="chat-empty">
            <Sparkles size={24} className="chat-empty-icon" />
            <h4>Edit with AI</h4>
            <p>Describe changes to your video plan. Chat will draft them first so you can review before applying.</p>
            {plan && (
              <div className="chat-suggestions">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    className="chat-suggestion-chip"
                    onClick={() => void handleSend(s)}
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

      {proposedPlan && diff && (
        <DiffReviewBar
          diff={diff}
          currentDuration={currentDuration}
          proposedDuration={proposedDuration}
          onAccept={() => void acceptProposedPlan()}
          onReject={rejectProposedPlan}
          onEditPrompt={() => {
            rejectProposedPlan()
            inputRef.current?.focus()
          }}
        />
      )}

      <div className="chat-input-area">
        <textarea
          ref={inputRef}
          className="chat-input"
          placeholder={disabled ? 'Generate a plan first...' : 'Describe a change...'}
          value={input}
          onChange={(e) => {
            setInput(e.target.value)
            autoResize(e.target)
          }}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
        />
        <button
          className="chat-send-btn"
          onClick={() => void handleSend()}
          disabled={disabled || !input.trim()}
          aria-label="Send"
        >
          <Send size={14} />
        </button>
      </div>
    </div>
  )
}

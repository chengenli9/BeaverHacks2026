import { useRef, useEffect } from 'react'
import { Info, CheckCircle, XCircle, AlertTriangle, Loader } from 'lucide-react'
import { usePipeline } from '../state/pipelineStore'

const ICON_MAP = {
  info: Info,
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  progress: Loader,
} as const

interface Props {
  embedded?: boolean
}

export function EventLog({ embedded }: Props) {
  const { eventLog } = usePipeline()
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (bottomRef.current && typeof bottomRef.current.scrollIntoView === 'function') {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [eventLog.length])

  const content = eventLog.length === 0 ? (
    <div className="empty-state">
      <Info size={28} />
      <h3>No Events</h3>
      <p>Open a project to start the pipeline</p>
    </div>
  ) : (
    <div className="event-list">
      {eventLog.map((ev) => {
        const Icon = ICON_MAP[ev.type]
        return (
          <div key={ev.id} className="event-item">
            <Icon className={`event-icon ${ev.type}`} size={13} />
            <span className="event-text">{ev.message}</span>
            <span className="event-time">
              {new Date(ev.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          </div>
        )
      })}
      <div ref={bottomRef} />
    </div>
  )

  if (embedded) return content

  return (
    <div className="panel" id="event-log-panel">
      <div className="panel-header">
        Agent Event Log
        <span className="panel-header-count">{eventLog.length}</span>
      </div>
      <div className="panel-content">{content}</div>
    </div>
  )
}

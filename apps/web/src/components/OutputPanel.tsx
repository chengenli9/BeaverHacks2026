import { useState, useEffect, useRef } from 'react'
import { MessageSquare, ScrollText, ShieldCheck } from 'lucide-react'
import { usePipeline } from '../state/pipelineStore'
import { ChatPanel } from './ChatPanel'
import { CriticPanel } from './CriticPanel'
import { EventLog } from './EventLog'
import { ProgressBar } from './ProgressBar'
import { StatusBadge } from './StatusBadge'
import type { JobStatus } from '../types/api'

type RightTab = 'events' | 'review' | 'chat'

interface VisibleJob {
  job: JobStatus
  done: boolean
}

function useVisibleJobs(activeJobs: Record<string, JobStatus>) {
  const [visible, setVisible] = useState<Record<string, VisibleJob>>({})
  const timers = useRef<Record<string, ReturnType<typeof setTimeout>>>({})

  useEffect(() => {
    setVisible((prev) => {
      const next = { ...prev }

      for (const job of Object.values(activeJobs)) {
        if (job.status === 'queued' || job.status === 'running') {
          next[job.job_id] = { job, done: false }
          if (timers.current[job.job_id]) {
            clearTimeout(timers.current[job.job_id])
            delete timers.current[job.job_id]
          }
        } else if (job.status === 'succeeded' && next[job.job_id] && !next[job.job_id].done) {
          next[job.job_id] = { job, done: true }
          timers.current[job.job_id] = setTimeout(() => {
            setVisible((p) => {
              const { [job.job_id]: _, ...rest } = p
              return rest
            })
            delete timers.current[job.job_id]
          }, 1200)
        } else if (job.status === 'failed') {
          delete next[job.job_id]
        }
      }

      return next
    })
  }, [activeJobs])

  useEffect(() => {
    const t = timers.current
    return () => { Object.values(t).forEach(clearTimeout) }
  }, [])

  return Object.values(visible)
}

export function OutputPanel() {
  const { activeJobs, criticSuggestions, projectId, renderQa } = usePipeline()
  const [tab, setTab] = useState<RightTab>('events')

  const visibleJobs = useVisibleJobs(activeJobs)

  const hasReview = Boolean(criticSuggestions || renderQa)

  // Auto-switch to review tab when suggestions arrive
  useEffect(() => {
    if (criticSuggestions && criticSuggestions.suggestions.length > 0) {
      setTab('review')
    }
  }, [criticSuggestions])

  return (
    <div className="panel" id="output-panel">
      <div className="panel-header">
        <div className="media-tabs">
          <button className={`media-tab ${tab === 'events' ? 'active' : ''}`} onClick={() => setTab('events')}>
            <ScrollText size={11} /> Events
          </button>
          <button
            className={`media-tab ${tab === 'review' ? 'active' : ''}`}
            onClick={() => setTab('review')}
            disabled={!hasReview}
            title={!hasReview ? "Run Review Render to get suggestions" : undefined}
          >
            <ShieldCheck size={11} /> Review
          </button>
          <button className={`media-tab ${tab === 'chat' ? 'active' : ''}`} onClick={() => setTab('chat')}>
            <MessageSquare size={11} /> Chat
          </button>
        </div>
      </div>

      {visibleJobs.length > 0 && (
        <div style={{ padding: '6px 8px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          {visibleJobs.map(({ job, done }) => {
            const hasRealProgress = typeof job.progress === 'number' && job.progress > 0
            return (
              <div key={job.job_id} className="card" style={{ borderColor: done ? 'var(--emerald)' : 'var(--blue)', marginBottom: 4 }}>
                <div className="card-header" style={{ marginBottom: 4 }}>
                  <span className="card-title" style={{ color: done ? 'var(--emerald)' : 'var(--blue)', fontSize: 11 }}>
                    {job.stage?.replace(/-/g, ' ') ?? 'Processing'}
                  </span>
                  <StatusBadge status={job.status} />
                </div>
                {job.message && <div className="card-body" style={{ fontSize: 10, marginBottom: 4 }}>{job.message}</div>}
                <ProgressBar progress={done ? 1 : hasRealProgress ? job.progress : undefined} durationMs={15000} />
              </div>
            )
          })}
        </div>
      )}

      <div className="panel-content">
        {tab === 'chat' && <ChatPanel />}
        {tab === 'events' && <EventLog embedded />}

        {tab === 'review' && (
          <div style={{ overflow: 'auto', flex: 1 }}>
            {renderQa && (
              <div className="card">
                <div className="card-header">
                  <span className="card-title">Render QA</span>
                </div>
                <div className="card-meta">
                  <span className="card-meta-item">{renderQa.summary.duration_seconds.toFixed(1)}s reviewed</span>
                  <span className="card-meta-item">{renderQa.issues.length} issue{renderQa.issues.length === 1 ? '' : 's'}</span>
                </div>
                {renderQa.issues.length > 0 && (
                  <div style={{ marginTop: 8, display: 'grid', gap: 6 }}>
                    {renderQa.issues.slice(0, 5).map((issue) => (
                      <div key={`${issue.code}-${issue.message}`} className="card-meta-item">
                        {issue.severity}: {issue.message}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            <CriticPanel />
            {!hasReview && (
              <div className="empty-state">
                <ShieldCheck size={28} />
                <h3>Review</h3>
                <p>{projectId ? 'Run the pipeline to get AI suggestions' : 'Open a project to begin'}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

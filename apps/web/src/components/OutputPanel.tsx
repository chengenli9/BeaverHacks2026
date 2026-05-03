import { useState, useEffect, useRef } from 'react'
import { Panel, Group, Separator } from 'react-resizable-panels'
import { Eye, ScrollText } from 'lucide-react'
import { usePipeline } from '../state/pipelineStore'
import { CriticPanel } from './CriticPanel'
import { EventLog } from './EventLog'
import { ProgressBar } from './ProgressBar'
import { RenderPreview } from './RenderPreview'
import { StatusBadge } from './StatusBadge'
import type { JobStatus } from '../types/api'

type RightTab = 'events' | 'output'

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
  const { activeJobs, criticSuggestions, mediaProbe, projectId, renderQa, renderSummary } = usePipeline()
  const [tab, setTab] = useState<RightTab>('events')

  const visibleJobs = useVisibleJobs(activeJobs)
  const runningJobs = Object.values(activeJobs).filter(
    (job) => job.status === 'queued' || job.status === 'running',
  )
  const renderJob = runningJobs.find((job) => job.stage === 'render')

  const hasOutput = Boolean(
    criticSuggestions ||
    renderSummary ||
    mediaProbe ||
    renderQa ||
    runningJobs.length > 0
  )

  return (
    <div className="panel" id="output-panel">
      <div className="panel-header">
        <div className="media-tabs">
          <button className={`media-tab ${tab === 'events' ? 'active' : ''}`} onClick={() => setTab('events')}>
            <ScrollText size={11} /> Events
          </button>
          <button 
            className={`media-tab ${tab === 'output' ? 'active' : ''}`} 
            onClick={() => setTab('output')}
            disabled={!hasOutput}
            title={!hasOutput ? "Run the pipeline to generate output" : undefined}
          >
            <Eye size={11} /> Output
          </button>
        </div>
      </div>

      {visibleJobs.length > 0 && (
        <div style={{ padding: '6px 8px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          {visibleJobs.map(({ job, done }) => (
            <div key={job.job_id} className="card" style={{ borderColor: done ? 'var(--emerald)' : 'var(--blue)', marginBottom: 4 }}>
              <div className="card-header" style={{ marginBottom: 4 }}>
                <span className="card-title" style={{ color: done ? 'var(--emerald)' : 'var(--blue)', fontSize: 11 }}>
                  {job.stage?.replace(/-/g, ' ') ?? 'Processing'}
                </span>
                <StatusBadge status={job.status} />
              </div>
              {job.message && <div className="card-body" style={{ fontSize: 10, marginBottom: 4 }}>{job.message}</div>}
              <ProgressBar progress={done ? 1 : undefined} durationMs={15000} />
            </div>
          ))}
        </div>
      )}

      <div className="panel-content">
        {tab === 'events' && <EventLog embedded />}

        {tab === 'output' && (
          <Group orientation="vertical" id="output-vertical" style={{ display: 'flex', flexDirection: 'column', height: '100%', flex: 1, minHeight: 0 }}>
            <Panel id="render-preview" defaultSize={40} minSize={20} maxSize={70} style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
              <RenderPreview />
            </Panel>

            <Separator className="resize-handle-y" />

            <Panel id="output-details" defaultSize={60} minSize={20} maxSize={80} style={{ display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'auto' }}>
{renderJob && (
  <div className="card" style={{ borderColor: 'var(--blue)' }}>
    <div className="card-header">
      <span className="card-title" style={{ color: 'var(--blue)' }}>Rendering</span>
      <StatusBadge status={renderJob.status} />
    </div>
    {renderJob.message && <div className="card-body">{renderJob.message}</div>}
    <div style={{ marginTop: 6 }}><ProgressBar progress={renderJob.progress} /></div>
  </div>
)}
{(mediaProbe || renderQa) && (
  <div className="card">
    <div className="card-header">
      <span className="card-title">Media QA</span>
    </div>
    <div className="card-meta">
      {mediaProbe && (
        <>
          <span className="card-meta-item">
            {mediaProbe.video_stream.width}x{mediaProbe.video_stream.height}
          </span>
          <span className="card-meta-item">{mediaProbe.video_stream.fps.toFixed(1)}fps</span>
          <span className="card-meta-item">{mediaProbe.has_audio ? 'Source audio' : 'No source audio'}</span>
        </>
      )}
      {renderQa && (
        <>
          <span className="card-meta-item">{renderQa.summary.duration_seconds.toFixed(1)}s review</span>
          <span className="card-meta-item">{renderQa.issues.length} issues</span>
        </>
      )}
    </div>
    {renderQa && renderQa.issues.length > 0 && (
      <div style={{ marginTop: 8, display: 'grid', gap: 6 }}>
        {renderQa.issues.slice(0, 3).map((issue) => (
          <div key={`${issue.code}-${issue.message}`} className="card-meta-item">
            {issue.severity}: {issue.message}
          </div>
        ))}
      </div>
    )}
  </div>
)}
              <CriticPanel />
              {!hasOutput && (
                <div className="empty-state">
                  <Eye size={28} />
                  <h3>Output</h3>
                  <p>{projectId ? 'Run pipeline stages' : 'Open a project to begin'}</p>
                </div>
              )}
            </Panel>
          </Group>
        )}
      </div>
    </div>
  )
}

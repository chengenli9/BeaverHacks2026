import { useState } from 'react'
import { Eye, ScrollText } from 'lucide-react'
import { usePipeline } from '../state/pipelineStore'
import { CriticPanel } from './CriticPanel'
import { RenderPreview } from './RenderPreview'
import { EventLog } from './EventLog'
import { ProgressBar } from './ProgressBar'

type RightTab = 'events' | 'output'

export function OutputPanel() {
  const { criticSuggestions, renderSummary, activeJobs, projectId } = usePipeline()
  const [tab, setTab] = useState<RightTab>('events')

  const renderJob = Object.values(activeJobs).find(
    (j) => j.stage === 'render' && j.status === 'running',
  )

  const hasOutput = criticSuggestions || renderSummary || renderJob

  return (
    <div className="panel" id="output-panel">
      <div className="panel-header">
        <div className="media-tabs">
          <button className={`media-tab ${tab === 'events' ? 'active' : ''}`} onClick={() => setTab('events')}>
            <ScrollText size={11} /> Events
          </button>
          <button className={`media-tab ${tab === 'output' ? 'active' : ''}`} onClick={() => setTab('output')}>
            <Eye size={11} /> Output
          </button>
        </div>
      </div>
      <div className="panel-content">
        {tab === 'events' && <EventLog embedded />}

        {tab === 'output' && (
          <>
            <RenderPreview />
            {renderJob && (
              <div className="card" style={{ borderColor: 'var(--blue)' }}>
                <div className="card-header">
                  <span className="card-title" style={{ color: 'var(--blue)' }}>Rendering…</span>
                  <span className="status-badge running"><span className="badge-dot" /> running</span>
                </div>
                {renderJob.message && <div className="card-body">{renderJob.message}</div>}
                <div style={{ marginTop: 6 }}><ProgressBar progress={renderJob.progress} /></div>
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
          </>
        )}
      </div>
    </div>
  )
}

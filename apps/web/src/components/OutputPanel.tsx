import { useState } from 'react'
import { Panel, Group, Separator } from 'react-resizable-panels'
import { Eye, ScrollText } from 'lucide-react'
import { usePipeline } from '../state/pipelineStore'
import { CriticPanel } from './CriticPanel'
import { EventLog } from './EventLog'
import { ProgressBar } from './ProgressBar'
import { RenderPreview } from './RenderPreview'
import { StatusBadge } from './StatusBadge'

type RightTab = 'events' | 'output'

export function OutputPanel() {
  const { activeJobs, criticSuggestions, projectId, renderSummary } = usePipeline()
  const [tab, setTab] = useState<RightTab>('events')

  const renderJob = Object.values(activeJobs).find(
    (job) => job.stage === 'render' && (job.status === 'queued' || job.status === 'running'),
  )

  const hasOutput = Boolean(criticSuggestions || renderSummary || renderJob)

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

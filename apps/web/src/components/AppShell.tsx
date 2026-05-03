import { Clapperboard, ArrowLeft } from 'lucide-react'
import { usePipeline } from '../state/pipelineStore'
import { PipelineControls } from './PipelineControls'
import { MediaBrowser } from './MediaBrowser'
import { CenterPanel } from './CenterPanel'
import { OutputPanel } from './OutputPanel'
import { Timeline } from './Timeline'

interface Props {
  onBack?: () => void
}

export function AppShell({ onBack }: Props) {
  const { projectId, projectName } = usePipeline()

  return (
    <div className="app-shell">
      {/* Header */}
      <header className="app-header">
        {onBack && (
          <button className="tl-tool-btn" onClick={onBack} title="Back to Projects" style={{ marginRight: 4 }}>
            <ArrowLeft size={16} />
          </button>
        )}
        <div className="app-logo" onClick={onBack} style={onBack ? { cursor: 'pointer' } : undefined}>
          <Clapperboard size={20} />
          DirectorLoop
        </div>

        {projectId && (
          <>
            <div className="header-divider" />
            <div className="project-badge">
              <span className="dot" />
              {projectName ?? projectId}
            </div>
          </>
        )}

        <div className="pipeline-controls">
          <PipelineControls />
        </div>
      </header>

      {/* Main area: 3-panel top + timeline bottom */}
      <div className="main-area">
        <div className="panels">
          <MediaBrowser />
          <CenterPanel />
          <OutputPanel />
        </div>
        <Timeline />
      </div>
    </div>
  )
}

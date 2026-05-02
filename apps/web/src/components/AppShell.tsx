import { Clapperboard } from 'lucide-react'
import { usePipeline } from '../state/pipelineStore'
import { PipelineControls } from './PipelineControls'
import { MediaBrowser } from './MediaBrowser'
import { CenterPanel } from './CenterPanel'
import { OutputPanel } from './OutputPanel'
import { Timeline } from './Timeline'

export function AppShell() {
  const { projectId, projectName } = usePipeline()

  return (
    <div className="app-shell">
      {/* Header */}
      <header className="app-header">
        <div className="app-logo">
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

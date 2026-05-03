import { useEffect } from 'react'
import { Clapperboard, ArrowLeft } from 'lucide-react'
import { usePipeline, usePipelineActions } from '../state/pipelineStore'
import { navigate } from '../router'
import { PipelineControls } from './PipelineControls'
import { MediaBrowser } from './MediaBrowser'
import { CenterPanel } from './CenterPanel'
import { OutputPanel } from './OutputPanel'

interface Props {
  projectId?: string
}

export function AppShell({ projectId: routeProjectId }: Props) {
  const { projectId, projectName } = usePipeline()
  const { openDemo, loadProject } = usePipelineActions()

  // Auto-load the project when navigating from home page
  useEffect(() => {
    if (routeProjectId && !projectId) {
      if (routeProjectId === 'demo_project') {
        openDemo()
      } else {
        loadProject(routeProjectId)
      }
    }
  }, [routeProjectId, projectId, openDemo, loadProject])

  return (
    <div className="app-shell">
      {/* Header */}
      <header className="app-header">
        <button
          className="back-to-projects"
          onClick={() => navigate('/')}
          id="back-to-projects"
          aria-label="Back to projects"
        >
          <ArrowLeft size={16} />
        </button>

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

      {/* Main area */}
      <div className="main-area">
        <div className="panels">
          <MediaBrowser />
          <CenterPanel />
          <OutputPanel />
        </div>
      </div>
    </div>
  )
}

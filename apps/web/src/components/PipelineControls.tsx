import {
  Search, FileText, Image, Boxes, ShieldCheck, Film,
  FolderOpen, RefreshCw, Loader, Plus,
} from 'lucide-react'
import { usePipeline, usePipelineActions } from '../state/pipelineStore'
import type { PipelineJobKind, PipelineStageKey } from '../types/api'

interface StageConfig {
  kind: PipelineJobKind
  label: string
  icon: React.ReactNode
  prereq?: PipelineStageKey
}

const STAGES: StageConfig[] = [
  { kind: 'analyze-scenes', label: 'Analyze', icon: <Search size={13} /> },
  { kind: 'generate-plan', label: 'Plan', icon: <FileText size={13} />, prereq: 'analyze-scenes' },
  { kind: 'generate-assets', label: 'Assets', icon: <Image size={13} />, prereq: 'generate-plan' },
  { kind: 'build-manifest', label: 'Manifest', icon: <Boxes size={13} />, prereq: 'generate-plan' },
  { kind: 'render', label: 'Render', icon: <Film size={13} />, prereq: 'build-manifest' },
  { kind: 'review-render', label: 'Review', icon: <ShieldCheck size={13} />, prereq: 'render' },
]

export function PipelineControls() {
  const { projectId, pipelineStages } = usePipeline()
  const { openDemo, createNewProject, runStage } = usePipelineActions()

  return (
    <>
      {!projectId ? (
        <>
          <button
            className="stage-btn stage-btn-primary"
            onClick={() => createNewProject('New Project')}
            id="new-project-btn"
          >
            <Plus size={14} /> New Project
          </button>
          <button
            className="stage-btn stage-btn-primary"
            onClick={openDemo}
            id="open-demo-btn"
          >
            <FolderOpen size={14} /> Open Demo Project
          </button>
        </>
      ) : (
        <>
          {STAGES.map(({ kind, label, icon, prereq }) => {
            const status = pipelineStages[kind] ?? 'idle'
            const prereqMet = !prereq || pipelineStages[prereq] === 'succeeded'
            const isRunning = status === 'running'
            const disabled = !prereqMet || isRunning

            return (
              <button
                key={kind}
                className={`stage-btn ${status}`}
                disabled={disabled}
                aria-label={status === 'failed' ? `Retry ${label}` : label}
                onClick={() => runStage(kind)}
                id={`stage-${kind}`}
              >
                {isRunning ? <Loader size={13} className="spin" /> : icon}
                {label}
                {status === 'failed' && <RefreshCw size={10} />}
              </button>
            )
          })}
        </>
      )}
    </>
  )
}

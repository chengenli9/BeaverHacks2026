import { Layers, Map, FileText, Boxes } from 'lucide-react'
import { usePipeline } from '../state/pipelineStore'
import { SceneCard } from './SceneCard'
import { BlockCard } from './BlockCard'
import { ProgressBar } from './ProgressBar'
import { StatusBadge } from './StatusBadge'

export function ManifestPanel() {
  const { sceneIndex, plan, manifest, activeJobs, projectId } = usePipeline()

  // Find running jobs for center panel stages
  const runningJobs = Object.values(activeJobs).filter(
    (j) => (j.status === 'queued' || j.status === 'running') && ['analyze-scenes', 'generate-plan', 'generate-tts', 'generate-assets', 'build-manifest'].includes(j.stage ?? ''),
  )

  const hasContent = sceneIndex || plan || manifest
  const totalBlocks = manifest?.blocks.length ?? 0

  return (
    <div className="panel" id="manifest-panel">
      <div className="panel-header">
        Artifacts
        {totalBlocks > 0 && <span className="panel-header-count">{totalBlocks} blocks</span>}
      </div>
      <div className="panel-content">
        {/* Running jobs */}
        {runningJobs.map((job) => (
          <div key={job.job_id} className="card" style={{ borderColor: 'var(--blue)' }}>
            <div className="card-header">
              <span className="card-title" style={{ color: 'var(--blue)' }}>
                {job.stage ?? job.job_id}
              </span>
              <StatusBadge status={job.status} />
            </div>
            {job.message && <div className="card-body">{job.message}</div>}
            <div style={{ marginTop: 6 }}>
              <ProgressBar progress={job.progress} />
            </div>
          </div>
        ))}

        {/* Scene Index */}
        {sceneIndex && (
          <>
            <div className="section-header">
              <Map size={12} /> Scenes ({sceneIndex.scenes.length})
            </div>
            {sceneIndex.scenes.map((s) => (
              <SceneCard key={s.scene_id} scene={s} />
            ))}
          </>
        )}

        {/* Plan */}
        {plan && (
          <>
            <div className="section-header">
              <FileText size={12} /> Plan - {plan.title}
            </div>
            <div className="story-arc">
              {plan.story_arc.map((step, i) => (
                <div key={i} className="arc-step">
                  <span className="arc-number">{i + 1}</span>
                  {step}
                </div>
              ))}
            </div>
            {plan.beats.map((beat) => (
              <div key={beat.beat_id} className="card">
                <div className="card-header">
                  <span className="card-title">{beat.beat_id}</span>
                  <span className={`type-badge ${beat.type}`}>{beat.type.replace('_', ' ')}</span>
                </div>
                <div className="card-body">
                  <strong>{beat.goal}</strong>
                  {beat.narration && (
                    <div style={{ marginTop: 4, fontStyle: 'italic', color: 'var(--text-muted)' }}>
                      "{beat.narration}"
                    </div>
                  )}
                  {beat.onscreen_text && (
                    <div style={{ marginTop: 4, color: 'var(--violet)' }}>
                      Text: "{beat.onscreen_text}"
                    </div>
                  )}
                </div>
                <div className="card-meta">
                  <span className="card-meta-item">{beat.duration.toFixed(1)}s</span>
                  {beat.scene_id && <span className="card-meta-item">- {beat.scene_id}</span>}
                </div>
              </div>
            ))}
          </>
        )}

        {/* Block Manifest */}
        {manifest && (
          <>
            <div className="section-header">
              <Boxes size={12} /> Block Manifest v{manifest.version}
            </div>
            <div className="card-meta" style={{ marginBottom: 8, padding: '0 4px' }}>
              <span className="card-meta-item">{manifest.render_settings.width}x{manifest.render_settings.height}</span>
              <span className="card-meta-item">{manifest.render_settings.fps}fps</span>
              <span className="card-meta-item">{manifest.render_settings.video_codec}</span>
            </div>
            {manifest.blocks.map((b) => (
              <BlockCard key={b.block_id} block={b} />
            ))}
          </>
        )}

        {/* Empty */}
        {!hasContent && !runningJobs.length && (
          <div className="empty-state">
            <Layers size={36} />
            <h3>No Artifacts</h3>
            <p>{projectId ? 'Run pipeline stages to generate artifacts' : 'Open a project to begin'}</p>
          </div>
        )}
      </div>
    </div>
  )
}

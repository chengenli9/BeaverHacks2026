import { useState } from 'react'
import { Play, Layers, FileText, Boxes, Map } from 'lucide-react'
import { usePipeline } from '../state/pipelineStore'
import { SceneCard } from './SceneCard'
import { BlockCard } from './BlockCard'
import { ProgressBar } from './ProgressBar'

type CenterTab = 'player' | 'scenes' | 'plan' | 'manifest'

export function CenterPanel() {
  const { sceneIndex, plan, manifest, renderSummary, activeJobs, projectId } = usePipeline()
  const [tab, setTab] = useState<CenterTab>('player')

  const runningJobs = Object.values(activeJobs).filter(j => j.status === 'running')

  return (
    <div className="panel center-panel" id="center-panel">
      {/* Player header with tabs */}
      <div className="panel-header center-header">
        <span style={{ fontWeight: 700, letterSpacing: 0 }}>Player</span>
        <div className="center-tabs">
          <button className={`center-tab ${tab === 'player' ? 'active' : ''}`} onClick={() => setTab('player')}>
            <Play size={11} /> Preview
          </button>
          {sceneIndex && (
            <button className={`center-tab ${tab === 'scenes' ? 'active' : ''}`} onClick={() => setTab('scenes')}>
              <Map size={11} /> Scenes
            </button>
          )}
          {plan && (
            <button className={`center-tab ${tab === 'plan' ? 'active' : ''}`} onClick={() => setTab('plan')}>
              <FileText size={11} /> Plan
            </button>
          )}
          {manifest && (
            <button className={`center-tab ${tab === 'manifest' ? 'active' : ''}`} onClick={() => setTab('manifest')}>
              <Boxes size={11} /> Manifest
            </button>
          )}
        </div>
      </div>

      <div className="panel-content center-content">
        {/* Player / Video Preview */}
        {tab === 'player' && (
          <div className="player-area">
            {renderSummary ? (
              <>
                <div className="video-viewport">
                  <video src={renderSummary.url} controls preload="metadata" id="final-video" />
                </div>
                <div className="player-info">
                  <span>{renderSummary.duration.toFixed(1)}s</span>
                  <span>{(renderSummary.bytes / (1024 * 1024)).toFixed(1)} MB</span>
                  <span>1920×1080</span>
                </div>
              </>
            ) : (
              <div className="video-viewport video-placeholder">
                <Play size={40} />
                <span>{projectId ? 'Run the pipeline and render to preview' : 'Open a project to begin'}</span>
              </div>
            )}

            {/* Running jobs */}
            {runningJobs.map(job => (
              <div key={job.job_id} className="card" style={{ borderColor: 'var(--blue)', margin: '8px 0' }}>
                <div className="card-header">
                  <span className="card-title" style={{ color: 'var(--blue)' }}>{job.stage}</span>
                  <span className="status-badge running"><span className="badge-dot" /> running</span>
                </div>
                {job.message && <div className="card-body">{job.message}</div>}
                <div style={{ marginTop: 6 }}><ProgressBar progress={job.progress} /></div>
              </div>
            ))}
          </div>
        )}

        {/* Scenes tab */}
        {tab === 'scenes' && sceneIndex && (
          <div className="artifact-scroll">
            <div className="section-header"><Map size={12} /> Scenes ({sceneIndex.scenes.length})</div>
            {sceneIndex.scenes.map(s => <SceneCard key={s.scene_id} scene={s} />)}
          </div>
        )}

        {/* Plan tab */}
        {tab === 'plan' && plan && (
          <div className="artifact-scroll">
            <div className="section-header"><FileText size={12} /> {plan.title}</div>
            <div className="story-arc">
              {plan.story_arc.map((step, i) => (
                <div key={i} className="arc-step"><span className="arc-number">{i + 1}</span>{step}</div>
              ))}
            </div>
            {plan.beats.map(beat => (
              <div key={beat.beat_id} className="card">
                <div className="card-header">
                  <span className="card-title">{beat.beat_id}</span>
                  <span className={`type-badge ${beat.type}`}>{beat.type.replace('_', ' ')}</span>
                </div>
                <div className="card-body">
                  <strong>{beat.goal}</strong>
                  {beat.narration && <div style={{ marginTop: 4, fontStyle: 'italic', color: 'var(--text-muted)' }}>"{beat.narration}"</div>}
                  {beat.onscreen_text && <div style={{ marginTop: 4, color: 'var(--violet)' }}>Text: "{beat.onscreen_text}"</div>}
                </div>
                <div className="card-meta">
                  <span className="card-meta-item">{beat.duration.toFixed(1)}s</span>
                  {beat.scene_id && <span className="card-meta-item">→ {beat.scene_id}</span>}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Manifest tab */}
        {tab === 'manifest' && manifest && (
          <div className="artifact-scroll">
            <div className="section-header"><Boxes size={12} /> Block Manifest v{manifest.version}</div>
            <div className="card-meta" style={{ marginBottom: 8, padding: '0 4px' }}>
              <span className="card-meta-item">{manifest.render_settings.width}×{manifest.render_settings.height}</span>
              <span className="card-meta-item">{manifest.render_settings.fps}fps</span>
            </div>
            {manifest.blocks.map(b => <BlockCard key={b.block_id} block={b} />)}
          </div>
        )}

        {/* Empty state */}
        {!projectId && tab !== 'player' && (
          <div className="empty-state">
            <Layers size={36} />
            <h3>No Data</h3>
            <p>Open a project and run pipeline stages</p>
          </div>
        )}
      </div>
    </div>
  )
}

import { useState } from 'react'
import { Boxes, FileText, Layers, Map, Play } from 'lucide-react'
import { getProjectFileUrl } from '../api/directorloopApi'
import { usePipeline, usePipelineActions } from '../state/pipelineStore'
import { BlockCard } from './BlockCard'
import { SceneCard } from './SceneCard'
import { Timeline } from './Timeline'

type CenterTab = 'player' | 'scenes' | 'plan' | 'manifest'

export function CenterPanel() {
  const { sceneIndex, plan, manifest, renderSummary, projectId, selectedMedia } = usePipeline()
  const { selectMedia } = usePipelineActions()
  const [tab, setTab] = useState<CenterTab>('player')
  const selectedVideoUrl = projectId && selectedMedia?.type === 'video'
    ? getProjectFileUrl(projectId, selectedMedia.path)
    : null

  return (
    <div className="panel center-panel" id="center-panel">
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
        {tab === 'player' && (
          <div className="player-area">
            {selectedVideoUrl ? (
              <>
                <div className="video-viewport">
                  <video src={selectedVideoUrl} controls preload="metadata" id="selected-video" />
                </div>
                <div className="player-info">
                  <span>{selectedMedia?.name}</span>
                  {selectedMedia?.size && <span>{(selectedMedia.size / (1024 * 1024)).toFixed(1)} MB</span>}
                  <span>Source preview</span>
                  <button className="inline-link-btn" type="button" onClick={() => selectMedia(null)}>
                    Timeline Preview
                  </button>
                </div>
              </>
            ) : renderSummary ? (
              <>
                <div className="video-viewport">
                  <video src={renderSummary.url} controls preload="metadata" id="final-video" />
                </div>
                <div className="player-info">
                  <span>{renderSummary.duration.toFixed(1)}s</span>
                  <span>{(renderSummary.bytes / (1024 * 1024)).toFixed(1)} MB</span>
                  <span>1920x1080</span>
                </div>
              </>
            ) : (
              <div className="video-viewport video-placeholder">
                <Layers size={48} />
                <p>Run the pipeline to generate a preview</p>
              </div>
            )}
          </div>
        )}

        {tab === 'scenes' && sceneIndex && (
          <div className="artifact-scroll">
            <div className="section-header"><Map size={12} /> Scenes ({sceneIndex.scenes.length})</div>
            {sceneIndex.scenes.map((scene) => <SceneCard key={scene.scene_id} scene={scene} projectId={projectId} />)}
          </div>
        )}

        {tab === 'plan' && plan && (
          <div className="artifact-scroll">
            <div className="section-header"><FileText size={12} /> {plan.title}</div>
            <div className="story-arc">
              {plan.story_arc.map((step, index) => (
                <div key={step} className="arc-step"><span className="arc-number">{index + 1}</span>{step}</div>
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
                    <div style={{ marginTop: 4, color: 'var(--violet)' }}>Text: "{beat.onscreen_text}"</div>
                  )}
                </div>
                <div className="card-meta">
                  <span className="card-meta-item">{beat.duration.toFixed(1)}s</span>
                  {beat.scene_id && <span className="card-meta-item">- {beat.scene_id}</span>}
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === 'manifest' && manifest && (
          <div className="artifact-scroll">
            <div className="section-header"><Boxes size={12} /> Block Manifest v{manifest.version}</div>
            <div className="card-meta" style={{ marginBottom: 8, padding: '0 4px' }}>
              <span className="card-meta-item">{manifest.render_settings.width}x{manifest.render_settings.height}</span>
              <span className="card-meta-item">{manifest.render_settings.fps}fps</span>
            </div>
            {manifest.blocks.map((block) => <BlockCard key={block.block_id} block={block} />)}
          </div>
        )}

        {!projectId && tab !== 'player' && (
          <div className="empty-state">
            <Layers size={36} />
            <h3>No Data</h3>
            <p>Open a project and run pipeline stages</p>
          </div>
        )}
      </div>

      <Timeline />
    </div>
  )
}

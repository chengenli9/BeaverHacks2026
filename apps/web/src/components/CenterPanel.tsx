import { useMemo, useState } from 'react'
import { Boxes, FileText, Layers, Map, Play, Plus, Send, Trash2 } from 'lucide-react'
import { getProjectFileUrl } from '../api/scenerioApi'
import { usePipeline, usePipelineActions, useVideoRef } from '../state/pipelineStore'
import { BeatFormModal } from './BeatFormModal'
import { BlockCard } from './BlockCard'
import { SceneCard } from './SceneCard'
import { Timeline } from './Timeline'

type CenterTab = 'player' | 'scenes' | 'plan' | 'manifest'

export function CenterPanel() {
  const { activeJobs, sceneIndex, plan, manifest, renderSummary, projectId, selectedMedia } = usePipeline()
  const { createBeat, deleteBeat, editPlanPrompt, reorderPlanBeats, selectMedia } = usePipelineActions()
  const videoRef = useVideoRef()
  const [tab, setTab] = useState<CenterTab>('player')
  const [draggingBeatId, setDraggingBeatId] = useState<string | null>(null)
  const [dragOverBeatIndex, setDragOverBeatIndex] = useState<number | null>(null)
  const [planPrompt, setPlanPrompt] = useState('')
  const [insertAfterBeatId, setInsertAfterBeatId] = useState<string | null>(null)
  const selectedVideoUrl = projectId && selectedMedia?.type === 'video'
    ? getProjectFileUrl(projectId, selectedMedia.path)
    : null
  const renderVideoUrl = renderSummary
    ? (renderSummary.cache_key
      ? `${renderSummary.url}?v=${encodeURIComponent(renderSummary.cache_key)}`
      : renderSummary.url)
    : null
  const isPlanMutationRunning = useMemo(
    () => Object.values(activeJobs).some(
      (job) =>
        (job.status === 'queued' || job.status === 'running') &&
        ['reorder-plan', 'delete-beat', 'edit-plan', 'create-beat'].includes(String(job.stage)),
    ),
    [activeJobs],
  )

  const handleBeatDrop = async (dropIndex: number) => {
    if (!plan || !draggingBeatId) return
    const fromIndex = plan.beats.findIndex((beat) => beat.beat_id === draggingBeatId)
    if (fromIndex < 0 || fromIndex === dropIndex) {
      setDraggingBeatId(null)
      setDragOverBeatIndex(null)
      return
    }
    const next = [...plan.beats]
    const [moved] = next.splice(fromIndex, 1)
    next.splice(dropIndex, 0, moved)
    setDraggingBeatId(null)
    setDragOverBeatIndex(null)
    await reorderPlanBeats(next.map((beat) => beat.beat_id))
  }

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
                  <video
                    key={renderVideoUrl ?? renderSummary.url}
                    ref={videoRef}
                    src={renderVideoUrl ?? renderSummary.url}
                    controls
                    preload="metadata"
                    id="final-video"
                  />
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
            <div className="section-header" style={{ justifyContent: 'space-between' }}>
              <span><FileText size={12} /> {plan.title}</span>
              <button className="tl-tool-btn" type="button" onClick={() => setInsertAfterBeatId(plan.beats.at(-1)?.beat_id ?? null)}>
                <Plus size={14} />
              </button>
            </div>
            <div className="story-arc">
              {plan.story_arc.map((step, index) => (
                <div key={step} className="arc-step"><span className="arc-number">{index + 1}</span>{step}</div>
              ))}
            </div>
            {plan.beats.map((beat, index) => (
              <div key={beat.beat_id}>
              <div
                className={`card ${draggingBeatId === beat.beat_id ? 'dragging' : ''} ${dragOverBeatIndex === index ? 'drag-over' : ''}`}
                draggable
                onDragStart={() => setDraggingBeatId(beat.beat_id)}
                onDragOver={(event) => { event.preventDefault(); setDragOverBeatIndex(index) }}
                onDrop={(event) => { event.preventDefault(); void handleBeatDrop(index) }}
                onDragEnd={() => { setDraggingBeatId(null); setDragOverBeatIndex(null) }}
              >
                <div className="card-header">
                  <span className="card-title">{beat.beat_id}</span>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <span className={`type-badge ${beat.type}`}>{beat.type.replace('_', ' ')}</span>
                    <button className="tl-tool-btn" type="button" onClick={() => void deleteBeat(beat.beat_id)} title="Delete beat">
                      <Trash2 size={12} />
                    </button>
                  </div>
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
                  {beat.image_prompt && (
                    <div style={{ marginTop: 4, color: 'var(--text-muted)' }}>Image prompt: {beat.image_prompt}</div>
                  )}
                </div>
                <div className="card-meta">
                  <span className="card-meta-item">{beat.duration.toFixed(1)}s</span>
                  {beat.scene_id && <span className="card-meta-item">- {beat.scene_id}</span>}
                </div>
              </div>
              <button
                type="button"
                className="inline-link-btn"
                style={{ margin: '4px 0 12px 6px' }}
                onClick={() => setInsertAfterBeatId(beat.beat_id)}
              >
                <Plus size={12} /> Insert After
              </button>
              </div>
            ))}
            <form
              className="card"
              onSubmit={(event) => {
                event.preventDefault()
                if (!planPrompt.trim()) return
                void editPlanPrompt(planPrompt)
                setPlanPrompt('')
              }}
            >
              <div className="card-header">
                <span className="card-title">Plan Edit Prompt</span>
              </div>
              <div className="card-body" style={{ display: 'grid', gap: 8 }}>
                <input
                  className="modal-input"
                  type="text"
                  value={planPrompt}
                  onChange={(event) => setPlanPrompt(event.target.value)}
                  placeholder="Make the intro shorter and add a scene card about results"
                  disabled={isPlanMutationRunning}
                />
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <button type="submit" className="modal-btn modal-btn-primary" disabled={!planPrompt.trim() || isPlanMutationRunning}>
                    <Send size={12} />
                    {isPlanMutationRunning ? 'Working...' : 'Apply Prompt'}
                  </button>
                </div>
              </div>
            </form>
            {insertAfterBeatId !== undefined && insertAfterBeatId !== null && (
              <BeatFormModal
                insertAfter={insertAfterBeatId}
                submitting={isPlanMutationRunning}
                onClose={() => setInsertAfterBeatId(null)}
                onSubmit={async (payload) => {
                  await createBeat(payload)
                  setInsertAfterBeatId(null)
                }}
              />
            )}
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

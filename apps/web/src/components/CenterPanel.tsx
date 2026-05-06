import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Boxes, FileText, GripVertical, Layers, Map as MapIcon, Pencil, Play, Plus, Send, Trash2, Copy
} from 'lucide-react'
import { getProjectFileUrl } from '../api/scenerioApi'
import { usePipeline, usePipelineActions, useVideoRef } from '../state/pipelineStore'
import { BeatFormModal } from './BeatFormModal'
import { BlockCard } from './BlockCard'
import { ContextMenu, type ContextMenuItem } from './ContextMenu'
import { DiffReviewBar } from './DiffReviewBar'
import { SceneCard } from './SceneCard'
import { Timeline } from './Timeline'
import { computePlanDiff, mergedView } from '../utils/planDiff'
import type { Beat } from '../types/api'

type CenterTab = 'player' | 'scenes' | 'plan' | 'manifest'

interface DragState {
  beatId: string
  startY: number
  currentY: number
  startIndex: number
  cardHeight: number
}

const DRAG_THRESHOLD = 5

export function CenterPanel() {
  const { activeJobs, sceneIndex, plan, manifest, renderSummary, projectId, selectedMedia, proposedPlan } = usePipeline()
  const { createBeat, deleteBeat, editPlanPreview, acceptProposedPlan, rejectProposedPlan, reorderPlanBeats, selectMedia, updateBeat } = usePipelineActions()
  const videoRef = useVideoRef()
  const [tab, setTab] = useState<CenterTab>('player')
  const [editingBeatId, setEditingBeatId] = useState<string | null>(null)
  const [editText, setEditText] = useState('')
  const [planPrompt, setPlanPrompt] = useState('')
  const [insertAfterBeatId, setInsertAfterBeatId] = useState<string | null>(null)
  const [ctxMenu, setCtxMenu] = useState<{ x: number; y: number; beat: Beat; index: number } | null>(null)

  // Pointer-event drag state
  const [drag, setDrag] = useState<DragState | null>(null)
  const [dropIndex, setDropIndex] = useState<number | null>(null)
  const cardRefs = useRef<Map<string, HTMLDivElement>>(new Map())
  const scrollRef = useRef<HTMLDivElement>(null)
  const pointerStartRef = useRef<{ x: number; y: number; beatId: string; index: number } | null>(null)

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

  // Listen for insert-beat events from timeline context menu
  useEffect(() => {
    const handler = (e: Event) => {
      const beatId = (e as CustomEvent).detail as string
      setInsertAfterBeatId(beatId)
      setTab('plan')
    }
    window.addEventListener('dl:insert-beat', handler)
    return () => window.removeEventListener('dl:insert-beat', handler)
  }, [])

  // Pointer-event drag system
  const handleGripPointerDown = useCallback((e: React.PointerEvent, beatId: string, index: number) => {
    if (editingBeatId) return
    e.preventDefault()
    pointerStartRef.current = { x: e.clientX, y: e.clientY, beatId, index }
    ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  }, [editingBeatId])

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    const start = pointerStartRef.current
    if (!start || !plan) return

    const dy = e.clientY - start.y
    if (!drag && Math.abs(dy) < DRAG_THRESHOLD) return

    const cardEl = cardRefs.current.get(start.beatId)
    const cardHeight = cardEl?.offsetHeight ?? 50

    if (!drag) {
      setDrag({ beatId: start.beatId, startY: start.y, currentY: e.clientY, startIndex: start.index, cardHeight })
    } else {
      setDrag(prev => prev ? { ...prev, currentY: e.clientY } : null)
    }

    // Compute drop index from offset
    const offset = e.clientY - start.y
    const indexOffset = Math.round(offset / (cardHeight + 8))
    const newIdx = Math.max(0, Math.min(plan.beats.length - 1, start.index + indexOffset))
    setDropIndex(newIdx)
  }, [drag, plan])

  const handlePointerUp = useCallback(async () => {
    const start = pointerStartRef.current
    pointerStartRef.current = null
    if (!drag || !plan || dropIndex === null || !start) {
      setDrag(null)
      setDropIndex(null)
      return
    }
    if (start.index !== dropIndex) {
      const next = [...plan.beats]
      const [moved] = next.splice(start.index, 1)
      next.splice(dropIndex, 0, moved)
      await reorderPlanBeats(next.map(b => b.beat_id))
    }
    setDrag(null)
    setDropIndex(null)
  }, [drag, plan, dropIndex, reorderPlanBeats])

  // Context menu for plan cards
  const handleCardContext = useCallback((e: React.MouseEvent, beat: Beat, index: number) => {
    e.preventDefault()
    setCtxMenu({ x: e.clientX, y: e.clientY, beat, index })
  }, [])

  const getCardCtxItems = useCallback((): ContextMenuItem[] => {
    if (!ctxMenu || !plan) return []
    const { beat, index } = ctxMenu
    const prevBeatId = index > 0 ? plan.beats[index - 1].beat_id : null
    return [
      {
        label: 'Edit text',
        icon: <Pencil size={12} />,
        onClick: () => { setEditText(beat.onscreen_text ?? beat.goal); setEditingBeatId(beat.beat_id) },
      },
      {
        label: 'Insert scene card after',
        icon: <Plus size={12} />,
        onClick: () => setInsertAfterBeatId(beat.beat_id),
      },
      {
        label: 'Insert scene card before',
        icon: <Plus size={12} />,
        onClick: () => setInsertAfterBeatId(prevBeatId),
        disabled: index === 0,
      },
      {
        label: 'Duplicate',
        icon: <Copy size={12} />,
        disabled: true,
        onClick: () => {},
      },
      {
        label: 'Delete',
        icon: <Trash2 size={12} />,
        danger: true,
        onClick: () => void deleteBeat(beat.beat_id),
      },
    ]
  }, [ctxMenu, plan, deleteBeat])

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
              <MapIcon size={11} /> Scenes
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
            <div className="section-header"><MapIcon size={12} /> Scenes ({sceneIndex.scenes.length})</div>
            {sceneIndex.scenes.map((scene) => <SceneCard key={scene.scene_id} scene={scene} projectId={projectId} />)}
          </div>
        )}

        {tab === 'plan' && plan && (() => {
          const diff = proposedPlan ? computePlanDiff(plan, proposedPlan) : null
          const displayBeats = diff && proposedPlan ? mergedView(diff, proposedPlan.beats) : plan.beats.map(beat => ({ beat, status: 'unchanged' as const, changes: [] as import('../utils/planDiff').BeatChange[] }))
          const currentDuration = plan.beats.reduce((s, b) => s + b.duration, 0)
          const proposedDuration = proposedPlan ? proposedPlan.beats.reduce((s, b) => s + b.duration, 0) : currentDuration

          return (
          <div
            className="artifact-scroll"
            ref={scrollRef}
            onPointerMove={drag ? handlePointerMove : undefined}
            onPointerUp={drag ? () => { void handlePointerUp() } : undefined}
          >
            <div className="section-header" style={{ justifyContent: 'space-between' }}>
              <span><FileText size={12} /> {plan.title}</span>
              <button className="tl-tool-btn" type="button" onClick={() => setInsertAfterBeatId(plan.beats.at(-1)?.beat_id ?? null)} disabled={!!proposedPlan}>
                <Plus size={14} />
              </button>
            </div>

            {diff && (
              <DiffReviewBar
                diff={diff}
                currentDuration={currentDuration}
                proposedDuration={proposedDuration}
                onAccept={() => void acceptProposedPlan()}
                onReject={rejectProposedPlan}
                onEditPrompt={() => {
                  rejectProposedPlan()
                  document.querySelector<HTMLInputElement>('.plan-prompt-input')?.focus()
                }}
              />
            )}

            {!proposedPlan && (
              <div className="story-arc">
                {plan.story_arc.map((step, index) => (
                  <div key={step} className="arc-step"><span className="arc-number">{index + 1}</span>{step}</div>
                ))}
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {displayBeats.map(({ beat, status, changes }, index) => {
                const isEditing = editingBeatId === beat.beat_id
                const isDragging = drag?.beatId === beat.beat_id
                const showDropLine = dropIndex === index && drag && drag.startIndex !== index
                const diffClass = status !== 'unchanged' ? `diff-${status}` : ''

                return (
                  <div key={`${beat.beat_id}-${status}-${index}`} style={{ position: 'relative' }}>
                    {showDropLine && drag && drag.startIndex > index && (
                      <div className="plan-drop-indicator" />
                    )}
                    <div
                      ref={(el) => { if (el) cardRefs.current.set(beat.beat_id, el); else cardRefs.current.delete(beat.beat_id) }}
                      className={`plan-card-compact ${isDragging ? 'dragging' : ''} ${diffClass}`}
                      style={{ opacity: isDragging ? 0.3 : 1, transition: isDragging ? 'none' : 'transform 150ms ease' }}
                      onContextMenu={(e) => !proposedPlan && handleCardContext(e, beat, index)}
                    >
                      <div className="plan-card-header">
                        {!proposedPlan && (
                          <div
                            className="plan-card-grip"
                            onPointerDown={(e) => handleGripPointerDown(e, beat.beat_id, index)}
                            onPointerMove={handlePointerMove}
                            onPointerUp={() => { void handlePointerUp() }}
                          >
                            <GripVertical size={14} />
                          </div>
                        )}
                        <span className="plan-card-id">{beat.beat_id}</span>
                        <span className={`type-badge ${beat.type}`}>{beat.type.replace('_', ' ')}</span>
                        <span className="plan-card-goal">
                          {isEditing ? (
                            <input
                              className="modal-input"
                              type="text"
                              value={editText}
                              onChange={(e) => setEditText(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                  void updateBeat(beat.beat_id, { onscreen_text: editText.trim() || null })
                                  setEditingBeatId(null)
                                } else if (e.key === 'Escape') {
                                  setEditingBeatId(null)
                                }
                              }}
                              autoFocus
                              style={{ width: '100%' }}
                            />
                          ) : beat.goal}
                        </span>
                        <div className="plan-card-actions">
                          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{beat.duration.toFixed(1)}s</span>
                          {!proposedPlan && (
                            <>
                              <button className="tl-tool-btn" type="button" onClick={() => {
                                if (isEditing) {
                                  void updateBeat(beat.beat_id, { onscreen_text: editText.trim() || null, goal: beat.goal })
                                  setEditingBeatId(null)
                                } else {
                                  setEditText(beat.onscreen_text ?? beat.goal)
                                  setEditingBeatId(beat.beat_id)
                                }
                              }} title={isEditing ? 'Save' : 'Edit text'}>
                                <Pencil size={11} />
                              </button>
                              <button className="tl-tool-btn" type="button" onClick={() => void deleteBeat(beat.beat_id)} title="Delete beat">
                                <Trash2 size={11} />
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                      {!isEditing && (beat.onscreen_text || beat.narration) && (
                        <div className="plan-card-secondary">
                          {beat.onscreen_text && <span style={{ color: 'var(--violet)' }}>"{beat.onscreen_text}" </span>}
                          {beat.narration && <em>"{beat.narration}"</em>}
                        </div>
                      )}
                      {changes && changes.length > 0 && (
                        <div className="diff-field-change">
                          {changes.map((c, ci) => (
                            <span key={ci}>
                              {c.field}: <span className="diff-old">{String(c.oldValue ?? '(empty)')}</span> → <span className="diff-new">{String(c.newValue ?? '(empty)')}</span>
                              {ci < changes.length - 1 && ' · '}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                    {showDropLine && drag && drag.startIndex < index && (
                      <div className="plan-drop-indicator" />
                    )}
                  </div>
                )
              })}
            </div>

            {/* Floating drag ghost */}
            {drag && plan && (() => {
              const beat = plan.beats.find(b => b.beat_id === drag.beatId)
              if (!beat) return null
              const scrollEl = scrollRef.current
              const width = scrollEl ? scrollEl.clientWidth - 24 : 400
              return (
                <div
                  className="plan-card-dragging"
                  style={{ top: drag.currentY - 20, left: scrollEl ? scrollEl.getBoundingClientRect().left + 12 : 100, '--drag-width': `${width}px` } as React.CSSProperties}
                >
                  <div className="plan-card-header" style={{ padding: '8px 10px' }}>
                    <GripVertical size={14} style={{ color: 'var(--text-muted)' }} />
                    <span className="plan-card-id">{beat.beat_id}</span>
                    <span className={`type-badge ${beat.type}`}>{beat.type.replace('_', ' ')}</span>
                    <span className="plan-card-goal">{beat.goal}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>{beat.duration.toFixed(1)}s</span>
                  </div>
                </div>
              )
            })()}

            <form
              className="card"
              style={{ marginTop: 12 }}
              onSubmit={(event) => {
                event.preventDefault()
                if (!planPrompt.trim()) return
                void editPlanPreview(planPrompt)
                setPlanPrompt('')
              }}
            >
              <div className="card-header">
                <span className="card-title">Plan Edit Prompt</span>
              </div>
              <div className="card-body" style={{ display: 'grid', gap: 8 }}>
                <input
                  className="modal-input plan-prompt-input"
                  type="text"
                  value={planPrompt}
                  onChange={(event) => setPlanPrompt(event.target.value)}
                  placeholder="Make the intro shorter and add a scene card about results"
                  disabled={isPlanMutationRunning || !!proposedPlan}
                />
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <button type="submit" className="modal-btn modal-btn-primary" disabled={!planPrompt.trim() || isPlanMutationRunning || !!proposedPlan}>
                    <Send size={12} />
                    {isPlanMutationRunning ? 'Working...' : 'Preview Changes'}
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
          )
        })()}

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

      {ctxMenu && (
        <ContextMenu
          x={ctxMenu.x}
          y={ctxMenu.y}
          items={getCardCtxItems()}
          onClose={() => setCtxMenu(null)}
        />
      )}

      <Timeline />
    </div>
  )
}

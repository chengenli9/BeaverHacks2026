import { useState, useRef, useCallback, useEffect } from 'react'
import {
  Scissors, Undo2, Redo2, Trash2, ZoomIn, ZoomOut,
  Play, Pause, SkipBack, SkipForward, Mic, Film, Type
} from 'lucide-react'
import { usePipeline } from '../state/pipelineStore'
import type { Block } from '../types/api'

const TRACK_COLORS: Record<string, string> = {
  title: '#8b5cf6',
  source_clip: '#3b82f6',
  end_card: '#2dd4bf',
}

const TRACK_ICONS: Record<string, typeof Film> = {
  title: Type, source_clip: Film, end_card: Type,
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  const ms = Math.floor((seconds % 1) * 100)
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}:${String(ms).padStart(2, '0')}`
}

function getBlockDuration(b: Block): number {
  return b.type === 'source_clip' ? b.video_duration : b.duration
}

export function Timeline() {
  const { manifest } = usePipeline()
  const [zoom, setZoom] = useState(1)
  const [playheadPos, setPlayheadPos] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [draggingBlock, setDraggingBlock] = useState<string | null>(null)
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null)
  const timelineRef = useRef<HTMLDivElement>(null)
  const playTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  const blocks = manifest?.blocks ?? []
  const totalDuration = blocks.reduce((sum, b) => sum + getBlockDuration(b), 0)
  const pixelsPerSecond = 60 * zoom

  // Playback simulation
  useEffect(() => {
    if (playing && totalDuration > 0) {
      playTimer.current = setInterval(() => {
        setPlayheadPos(prev => {
          if (prev >= totalDuration) { setPlaying(false); return 0 }
          return prev + 0.05
        })
      }, 50)
    } else if (playTimer.current) {
      clearInterval(playTimer.current)
    }
    return () => { if (playTimer.current) clearInterval(playTimer.current) }
  }, [playing, totalDuration])

  const handleTimelineClick = useCallback((e: React.MouseEvent) => {
    if (!timelineRef.current || totalDuration === 0) return
    const rect = timelineRef.current.getBoundingClientRect()
    const scrollLeft = timelineRef.current.scrollLeft
    const x = e.clientX - rect.left + scrollLeft - 40 // account for track label
    const time = Math.max(0, Math.min(x / pixelsPerSecond, totalDuration))
    setPlayheadPos(time)
  }, [pixelsPerSecond, totalDuration])

  // Drag handlers
  const handleDragStart = (blockId: string) => { setDraggingBlock(blockId) }
  const handleDragOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault(); setDragOverIndex(idx)
  }
  const handleDragEnd = () => { setDraggingBlock(null); setDragOverIndex(null) }

  // Time ruler marks
  const rulerMarks: number[] = []
  const step = zoom >= 2 ? 0.5 : zoom >= 1 ? 1 : 2
  for (let t = 0; t <= totalDuration + step; t += step) rulerMarks.push(t)

  return (
    <div className="timeline-container" id="timeline" data-testid="timeline">
      {/* Toolbar */}
      <div className="timeline-toolbar">
        <div className="timeline-tools">
          <button className="tl-tool-btn" title="Undo"><Undo2 size={14} /></button>
          <button className="tl-tool-btn" title="Redo"><Redo2 size={14} /></button>
          <div className="tl-divider" />
          <button className="tl-tool-btn" title="Cut"><Scissors size={14} /></button>
          <button className="tl-tool-btn" title="Delete"><Trash2 size={14} /></button>
        </div>

        <div className="timeline-transport">
          <button className="tl-tool-btn" onClick={() => setPlayheadPos(0)}><SkipBack size={14} /></button>
          <button className="tl-play-btn" onClick={() => setPlaying(!playing)} id="timeline-play-btn">
            {playing ? <Pause size={16} /> : <Play size={16} />}
          </button>
          <button className="tl-tool-btn" onClick={() => setPlayheadPos(totalDuration)}><SkipForward size={14} /></button>
          <span className="tl-time">{formatTime(playheadPos)}</span>
          <span className="tl-time-sep">/</span>
          <span className="tl-time tl-time-total">{formatTime(totalDuration)}</span>
        </div>

        <div className="timeline-zoom">
          <button className="tl-tool-btn" onClick={() => setZoom(z => Math.max(0.25, z / 1.5))}><ZoomOut size={14} /></button>
          <span className="tl-zoom-label">{Math.round(zoom * 100)}%</span>
          <button className="tl-tool-btn" onClick={() => setZoom(z => Math.min(4, z * 1.5))}><ZoomIn size={14} /></button>
        </div>
      </div>

      {/* Timeline tracks */}
      <div className="timeline-tracks" ref={timelineRef} onClick={handleTimelineClick}>
        {blocks.length === 0 ? (
          <div className="timeline-empty">
            <Film size={20} />
            <span>Build a manifest to populate the timeline</span>
          </div>
        ) : (
          <>
            {/* Time ruler */}
            <div className="time-ruler" style={{ width: totalDuration * pixelsPerSecond + 40 }}>
              <div className="ruler-label-col" />
              {rulerMarks.map(t => (
                <div key={t} className="ruler-mark" style={{ left: t * pixelsPerSecond + 40 }}>
                  <span className="ruler-text">{formatTime(t)}</span>
                </div>
              ))}
            </div>

            {/* Video track */}
            <div className="tl-track">
              <div className="tl-track-label"><Film size={11} /> Video</div>
              <div className="tl-track-clips" style={{ width: totalDuration * pixelsPerSecond }}>
                {blocks.map((block, idx) => {
                  const dur = getBlockDuration(block)
                  const w = dur * pixelsPerSecond
                  const color = TRACK_COLORS[block.type] ?? '#6b7280'
                  const Icon = TRACK_ICONS[block.type] ?? Film
                  const isDragging = draggingBlock === block.block_id
                  const isOver = dragOverIndex === idx

                  return (
                    <div
                      key={block.block_id}
                      className={`tl-clip ${isDragging ? 'dragging' : ''} ${isOver ? 'drag-over' : ''}`}
                      style={{ width: w, '--clip-color': color } as React.CSSProperties}
                      draggable
                      onDragStart={() => handleDragStart(block.block_id)}
                      onDragOver={(e) => handleDragOver(e, idx)}
                      onDragEnd={handleDragEnd}
                      title={`${block.block_id} (${dur.toFixed(1)}s)`}
                      id={`tl-clip-${block.block_id}`}
                    >
                      <Icon size={10} />
                      <span className="tl-clip-label">{block.block_id}</span>
                      <span className="tl-clip-dur">{dur.toFixed(1)}s</span>
                      {/* Resize handles */}
                      <div className="tl-clip-handle tl-clip-handle-l" />
                      <div className="tl-clip-handle tl-clip-handle-r" />
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Audio track */}
            <div className="tl-track">
              <div className="tl-track-label"><Mic size={11} /> Audio</div>
              <div className="tl-track-clips" style={{ width: totalDuration * pixelsPerSecond }}>
                {blocks.filter(b => b.type === 'source_clip').map((block) => {
                  if (block.type !== 'source_clip') return null
                  const offset = blocks.slice(0, blocks.indexOf(block)).reduce((s, b) => s + getBlockDuration(b), 0)
                  const w = block.tts_duration * pixelsPerSecond
                  return (
                    <div
                      key={`audio-${block.block_id}`}
                      className="tl-clip tl-clip-audio"
                      style={{ width: w, marginLeft: offset * pixelsPerSecond - (blocks.slice(0, blocks.indexOf(block)).filter(b => b.type === 'source_clip').reduce((s, b) => s + (b.type === 'source_clip' ? b.tts_duration : 0), 0)) * pixelsPerSecond + offset * pixelsPerSecond * 0 }}
                      title={`TTS: ${block.tts_duration.toFixed(1)}s`}
                    >
                      <Mic size={10} />
                      <span className="tl-clip-label">TTS {block.block_id.split('_')[0]}</span>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Playhead */}
            {totalDuration > 0 && (
              <div
                className="tl-playhead"
                style={{ left: playheadPos * pixelsPerSecond + 40 }}
              >
                <div className="tl-playhead-head" />
                <div className="tl-playhead-line" />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

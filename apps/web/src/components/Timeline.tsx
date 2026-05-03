import { useState, useRef, useCallback, useEffect } from 'react'
import {
  Scissors, Undo2, Redo2, Trash2, ZoomIn, ZoomOut,
  Play, Pause, SkipBack, SkipForward, Mic, Film, Type
} from 'lucide-react'
import { usePipeline, useVideoRef } from '../state/pipelineStore'
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
  if (b.type === 'source_clip') return b.video_duration
  return b.duration
}

function getTtsDuration(block: Block): number {
  if (block.type !== 'source_clip') return 0
  return typeof block.tts_duration === 'number' && Number.isFinite(block.tts_duration) ? block.tts_duration : 0
}

export function Timeline() {
  const { manifest } = usePipeline()
  const videoRef = useVideoRef()
  const [zoom, setZoom] = useState(1)
  const [playheadPos, setPlayheadPos] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [draggingBlock, setDraggingBlock] = useState<string | null>(null)
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null)
  const timelineRef = useRef<HTMLDivElement>(null)

  const blocks = manifest?.blocks ?? []
  const totalDuration = blocks.reduce((sum, b) => sum + getBlockDuration(b), 0)
  const pixelsPerSecond = 60 * zoom

  // Sync playhead from the render video element at 60fps via rAF
  // Uses getElementById so it naturally returns null when render video is unmounted
  // (e.g. user is watching a source preview)
  useEffect(() => {
    let rafId: number

    const tick = () => {
      const video = videoRef.current
      if (video) {
        setPlayheadPos(video.currentTime)
        setPlaying(!video.paused && !video.ended)
      } else {
        setPlaying(false)
      }
      rafId = requestAnimationFrame(tick)
    }
    rafId = requestAnimationFrame(tick)

    return () => cancelAnimationFrame(rafId)
  }, [videoRef])

  const playVideo = useCallback((video: HTMLVideoElement) => {
    const playback = video.play()
    if (playback && typeof playback.catch === 'function') {
      playback.catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') {
          return
        }
        throw error
      })
    }
  }, [])

  // Playback: controls the actual <video> element
  const togglePlay = useCallback(() => {
    const video = videoRef.current
    if (!video) return
    if (video.paused) {
      playVideo(video)
    } else {
      video.pause()
    }
  }, [playVideo, videoRef])

  const seekTo = useCallback((time: number) => {
    const video = videoRef.current
    if (!video) return
    video.currentTime = Math.max(0, Math.min(time, video.duration || totalDuration))
    setPlayheadPos(video.currentTime)
  }, [totalDuration, videoRef])

  const handleTimelineClick = useCallback((e: React.MouseEvent) => {
    if (!timelineRef.current || totalDuration === 0) return
    const rect = timelineRef.current.getBoundingClientRect()
    const scrollLeft = timelineRef.current.scrollLeft
    const x = e.clientX - rect.left + scrollLeft - 40 // account for track label
    const time = Math.max(0, Math.min(x / pixelsPerSecond, totalDuration))
    seekTo(time)
  }, [pixelsPerSecond, totalDuration, seekTo])

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
          <button className="tl-tool-btn" onClick={() => seekTo(0)}><SkipBack size={14} /></button>
          <button className="tl-play-btn" onClick={togglePlay} id="timeline-play-btn">
            {playing ? <Pause size={16} /> : <Play size={16} />}
          </button>
          <button className="tl-tool-btn" onClick={() => seekTo(totalDuration)}><SkipForward size={14} /></button>
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
                  const ttsDuration = getTtsDuration(block)
                  if (ttsDuration <= 0) return null
                  const w = ttsDuration * pixelsPerSecond
                  return (
                    <div
                      key={`audio-${block.block_id}`}
                      className="tl-clip tl-clip-audio"
                      style={{ width: w, marginLeft: offset * pixelsPerSecond - (blocks.slice(0, blocks.indexOf(block)).filter(b => b.type === 'source_clip').reduce((s, b) => s + getTtsDuration(b), 0)) * pixelsPerSecond + offset * pixelsPerSecond * 0 }}
                      title={`TTS: ${ttsDuration.toFixed(1)}s`}
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

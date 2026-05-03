import type { Block } from '../types/api'
import { Clock, Film, Type, Mic, AlertTriangle } from 'lucide-react'

interface Props {
  block: Block
}

export function BlockCard({ block }: Props) {
  const isClip = block.type === 'source_clip'
  const ttsDuration = isClip && Number.isFinite(block.tts_duration) ? block.tts_duration : null
  const textBlock = block.type === 'title' || block.type === 'end_card' || block.type === 'scene_card' ? block : null

  return (
    <div className="card" id={`block-${block.block_id}`}>
      <div className="card-header">
        <span className="card-title">
          {block.type === 'title' && <Type size={12} />}
          {block.type === 'source_clip' && <Film size={12} />}
          {block.type === 'scene_card' && <Type size={12} />}
          {block.type === 'end_card' && <Type size={12} />}
          {block.block_id}
        </span>
        <span className={`type-badge ${block.type}`}>{block.type.replace('_', ' ')}</span>
      </div>

      {textBlock && (
        <div className="card-body">
          <strong style={{ color: 'var(--text-primary)' }}>"{textBlock.text}"</strong>
        </div>
      )}

      <div className="card-meta">
        <span className="card-meta-item">
          <Clock size={10} />
          {isClip ? `${block.video_duration.toFixed(1)}s` : `${block.duration.toFixed(1)}s`}
        </span>
        {isClip && (
          <>
            <span className="card-meta-item">
              <Film size={10} />
              {block.source_start.toFixed(1)}s - {block.source_end.toFixed(1)}s
            </span>
            {ttsDuration != null && (
              <span className="card-meta-item">
                <Mic size={10} />
                TTS {ttsDuration.toFixed(1)}s
              </span>
            )}
          </>
        )}
        {textBlock?.layout_preset && <span className="card-meta-item">{textBlock.layout_preset}</span>}
        {textBlock?.font_family && <span className="card-meta-item">{textBlock.font_family}</span>}
        {textBlock?.background_mode && <span className="card-meta-item">{textBlock.background_mode}</span>}
        {textBlock?.motion_asset && <span className="card-meta-item">remotion</span>}
        {textBlock?.motion_asset?.runtime_template && (
          <span className="card-meta-item">{textBlock.motion_asset.runtime_template}</span>
        )}
      </div>

      {isClip && ttsDuration != null && ttsDuration > block.video_duration && (
        <div className="timing-warning">
          <AlertTriangle size={12} />
          TTS ({ttsDuration.toFixed(1)}s) exceeds video ({block.video_duration.toFixed(1)}s)
        </div>
      )}
    </div>
  )
}

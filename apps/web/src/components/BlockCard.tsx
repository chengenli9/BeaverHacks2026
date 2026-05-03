import type { Block } from '../types/api'
import { getProjectFileUrl } from '../api/scenerioApi'
import { usePipeline } from '../state/pipelineStore'
import { Clock, Film, Type, Mic, AlertTriangle } from 'lucide-react'

interface Props {
  block: Block
}

export function BlockCard({ block }: Props) {
  const { highlightedBlockId, projectId } = usePipeline()
  const isHighlighted = highlightedBlockId === block.block_id
  const isClip = block.type === 'source_clip'
  const ttsDuration = isClip && Number.isFinite(block.tts_duration) ? block.tts_duration : null
  const textBlock = block.type === 'title' || block.type === 'end_card' || block.type === 'scene_card' ? block : null
  const imageBlock = block.type === 'image_card' ? block : null
  const imageUrl = projectId && imageBlock ? getProjectFileUrl(projectId, imageBlock.image_asset) : null

  return (
    <div className={`card${isHighlighted ? ' block-highlight' : ''}`} id={`block-${block.block_id}`}>
      <div className="card-header">
        <span className="card-title">
          {block.type === 'title' && <Type size={12} />}
          {block.type === 'source_clip' && <Film size={12} />}
          {block.type === 'scene_card' && <Type size={12} />}
          {block.type === 'end_card' && <Type size={12} />}
          {block.type === 'image_card' && <Film size={12} />}
          {block.block_id}
        </span>
        <span className={`type-badge ${block.type}`}>{block.type.replace('_', ' ')}</span>
      </div>

      {textBlock && (
        <div className="card-body">
          <strong style={{ color: 'var(--text-primary)' }}>"{textBlock.text}"</strong>
        </div>
      )}

      {imageBlock && (
        <div className="card-body" style={{ display: 'grid', gap: 8 }}>
          {imageUrl && (
            <img
              src={imageUrl}
              alt={imageBlock.image_prompt}
              style={{ width: '100%', maxHeight: 140, objectFit: 'cover', borderRadius: 6 }}
              loading="lazy"
            />
          )}
          <strong style={{ color: 'var(--text-primary)' }}>{imageBlock.image_prompt}</strong>
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
        {imageBlock?.ken_burns && <span className="card-meta-item">ken burns</span>}
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

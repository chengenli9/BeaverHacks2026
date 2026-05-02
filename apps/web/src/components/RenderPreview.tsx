import { Play, HardDrive, Clock } from 'lucide-react'
import { usePipeline } from '../state/pipelineStore'

export function RenderPreview() {
  const { renderSummary } = usePipeline()

  if (!renderSummary) return null

  const sizeMB = (renderSummary.bytes / (1024 * 1024)).toFixed(1)

  return (
    <div id="render-preview-section">
      <div className="section-header">
        <Play size={12} /> Final Render
      </div>
      <div className="video-preview">
        <video
          src={renderSummary.url}
          controls
          preload="metadata"
          id="final-video"
        />
      </div>
      <div className="video-meta">
        <span className="card-meta-item">
          <Clock size={10} /> {renderSummary.duration.toFixed(1)}s
        </span>
        <span className="card-meta-item">
          <HardDrive size={10} /> {sizeMB} MB
        </span>
      </div>
    </div>
  )
}

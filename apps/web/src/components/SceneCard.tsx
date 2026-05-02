import type { Scene } from '../types/api'
import { Clock, MapPin } from 'lucide-react'

interface Props {
  scene: Scene
}

export function SceneCard({ scene }: Props) {
  const dur = (scene.end - scene.start).toFixed(1)
  const rel = scene.demo_relevance
  const relClass = rel >= 0.8 ? 'high' : rel >= 0.5 ? 'medium' : 'low'

  return (
    <div className="card" id={`scene-${scene.scene_id}`}>
      <div className="card-header">
        <span className="card-title">
          <MapPin size={12} />
          {scene.scene_id}
        </span>
        <span className="card-id">{dur}s</span>
      </div>
      <div className="card-body">{scene.summary}</div>
      <div className="card-meta">
        <span className="card-meta-item">
          <Clock size={10} />
          {scene.start.toFixed(1)}s — {scene.end.toFixed(1)}s
        </span>
      </div>
      <div className="tags">
        {scene.visual_tags.map((tag) => (
          <span key={tag} className="tag">{tag}</span>
        ))}
      </div>
      <div className="relevance-bar" style={{ marginTop: 8 }}>
        <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>Relevance</span>
        <div className="relevance-track">
          <div className={`relevance-fill ${relClass}`} style={{ width: `${rel * 100}%` }} />
        </div>
        <span className="relevance-label">{(rel * 100).toFixed(0)}%</span>
      </div>
    </div>
  )
}

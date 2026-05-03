import { useState } from 'react'
import type { Scene } from '../types/api'
import { getProjectFileUrl } from '../api/scenerioApi'
import { Clock, MapPin } from 'lucide-react'

interface Props {
  scene: Scene
  projectId: string | null
}

export function SceneCard({ scene, projectId }: Props) {
  const dur = (scene.end - scene.start).toFixed(1)
  const rel = scene.demo_relevance
  const relClass = rel >= 0.8 ? 'high' : rel >= 0.5 ? 'medium' : 'low'
  const [imgError, setImgError] = useState(false)

  const thumbUrl = projectId && !imgError
    ? getProjectFileUrl(projectId, `cache/frames/${scene.scene_id}_mid.jpg`)
    : null
  const sourceLabel = scene.source.split('/').pop() ?? scene.source

  return (
    <div className="card scene-card" id={`scene-${scene.scene_id}`}>
      <div className="scene-card-body">
        <div className="scene-card-text">
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
              {scene.start.toFixed(1)}s - {scene.end.toFixed(1)}s
            </span>
            <span className="card-meta-item">{sourceLabel}</span>
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
        {thumbUrl && (
          <img
            className="scene-thumb"
            src={thumbUrl}
            alt={`${scene.scene_id} thumbnail`}
            loading="lazy"
            onError={() => setImgError(true)}
          />
        )}
      </div>
    </div>
  )
}

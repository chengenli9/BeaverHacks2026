import { useState, useRef, useEffect } from 'react'
import { Star, Play, AlertCircle, Circle, MoreVertical, Pencil, Trash2 } from 'lucide-react'
import type { ProjectListItem } from '../types/api'
import { navigate } from '../router'

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  if (days < 1) return 'Today'
  if (days === 1) return '1 day ago'
  if (days < 30) return `${days} days ago`
  const months = Math.floor(days / 30)
  if (months === 1) return '1 month ago'
  return `${months} months ago`
}

function statusLabel(project: ProjectListItem): string {
  if (project.status === 'empty') return 'Empty'
  if (project.status === 'draft') return 'Draft'
  if ((project.progress ?? 0) > 0 && (project.progress ?? 0) < 100) return `${project.progress}% complete`
  if (project.status === 'active') return 'In progress'
  return 'Draft'
}

function statusBadgeClass(project: ProjectListItem): string {
  if (project.status === 'active' && !project.starred) return 'project-badge-active'
  if (project.starred) return 'project-badge-starred'
  return 'project-badge-draft'
}

function statusBadgeLabel(project: ProjectListItem): string {
  if (project.starred) return 'Starred'
  if (project.status === 'active') return 'Active'
  return 'Draft'
}

/** Abstract thumbnail SVGs matching the reference image */
function Thumbnail({ type }: { type?: string }) {
  switch (type) {
    case 'timeline':
      return (
        <div className="project-thumb project-thumb-timeline">
          <div className="thumb-label">TIMELINE EDIT</div>
          <svg viewBox="0 0 200 80" className="thumb-svg">
            <rect x="8" y="8" width="70" height="10" rx="2" fill="var(--teal)" opacity="0.7" />
            <rect x="8" y="22" width="120" height="10" rx="2" fill="var(--blue)" opacity="0.6" />
            <rect x="8" y="36" width="90" height="10" rx="2" fill="var(--blue)" opacity="0.5" />
            <rect x="8" y="50" width="140" height="10" rx="2" fill="var(--rose)" opacity="0.5" />
            <rect x="8" y="64" width="60" height="10" rx="2" fill="var(--rose)" opacity="0.4" />
            <rect x="82" y="8" width="50" height="10" rx="2" fill="var(--teal)" opacity="0.5" />
            <rect x="140" y="22" width="50" height="10" rx="2" fill="var(--emerald)" opacity="0.4" />
          </svg>
        </div>
      )
    case 'mobile':
      return (
        <div className="project-thumb project-thumb-mobile">
          <div className="thumb-label">MOBILE UI</div>
          <svg viewBox="0 0 200 80" className="thumb-svg">
            <rect x="20" y="5" width="50" height="70" rx="4" fill="var(--bg-card-hover)" stroke="var(--border)" strokeWidth="1" />
            <rect x="75" y="5" width="50" height="70" rx="4" fill="var(--bg-card-hover)" stroke="var(--border)" strokeWidth="1" />
            <rect x="130" y="5" width="50" height="70" rx="4" fill="var(--bg-card-hover)" stroke="var(--border)" strokeWidth="1" />
            <rect x="25" y="25" width="40" height="20" rx="2" fill="var(--text-muted)" opacity="0.3" />
            <rect x="80" y="15" width="40" height="15" rx="2" fill="var(--text-muted)" opacity="0.3" />
            <rect x="80" y="35" width="40" height="25" rx="2" fill="var(--blue)" opacity="0.2" />
            <rect x="135" y="20" width="40" height="30" rx="2" fill="var(--text-muted)" opacity="0.2" />
          </svg>
        </div>
      )
    case 'analytics':
      return (
        <div className="project-thumb project-thumb-analytics">
          <div className="thumb-label">ANALYTICS</div>
          <svg viewBox="0 0 200 80" className="thumb-svg">
            <rect x="15" y="55" width="18" height="20" rx="2" fill="var(--lime)" opacity="0.8" />
            <rect x="38" y="40" width="18" height="35" rx="2" fill="var(--lime)" opacity="0.7" />
            <rect x="61" y="25" width="18" height="50" rx="2" fill="var(--lime)" opacity="0.9" />
            <rect x="84" y="10" width="18" height="65" rx="2" fill="var(--teal)" opacity="0.7" />
            <rect x="107" y="30" width="18" height="45" rx="2" fill="var(--teal)" opacity="0.6" />
            <rect x="130" y="20" width="18" height="55" rx="2" fill="var(--blue)" opacity="0.5" />
            <rect x="153" y="35" width="18" height="40" rx="2" fill="var(--blue)" opacity="0.6" />
            <rect x="176" y="45" width="18" height="30" rx="2" fill="var(--teal)" opacity="0.5" />
          </svg>
        </div>
      )
    case 'gameloop':
      return (
        <div className="project-thumb project-thumb-game">
          <div className="thumb-label">GAME LOOP</div>
          <svg viewBox="0 0 200 80" className="thumb-svg">
            <circle cx="50" cy="45" r="18" fill="none" stroke="var(--lime)" strokeWidth="3" opacity="0.7" />
            <circle cx="100" cy="45" r="14" fill="none" stroke="var(--lime)" strokeWidth="3" opacity="0.9" />
            <circle cx="100" cy="45" r="6" fill="var(--lime)" opacity="0.8" />
            <circle cx="140" cy="45" r="18" fill="none" stroke="var(--lime)" strokeWidth="3" opacity="0.6" />
            <circle cx="140" cy="45" r="8" fill="none" stroke="var(--lime)" strokeWidth="2" opacity="0.4" />
          </svg>
        </div>
      )
    case 'empty':
      return (
        <div className="project-thumb project-thumb-empty">
          <div className="thumb-label">UNTITLED</div>
          <svg viewBox="0 0 200 80" className="thumb-svg">
            <rect x="30" y="20" width="140" height="8" rx="2" fill="var(--text-muted)" opacity="0.15" />
            <rect x="30" y="35" width="100" height="8" rx="2" fill="var(--text-muted)" opacity="0.12" />
            <rect x="30" y="50" width="120" height="8" rx="2" fill="var(--text-muted)" opacity="0.1" />
          </svg>
        </div>
      )
    default:
      return (
        <div className="project-thumb project-thumb-default">
          <svg viewBox="0 0 200 80" className="thumb-svg">
            <rect x="20" y="15" width="160" height="50" rx="4" fill="var(--bg-card-hover)" />
          </svg>
        </div>
      )
  }
}

interface Props {
  project: ProjectListItem
  onEdit?: (project: ProjectListItem) => void
  onDelete?: (project: ProjectListItem) => void
}

export function ProjectCard({ project, onEdit, onDelete }: Props) {
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close context menu on outside click
  useEffect(() => {
    if (!menuOpen) return
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [menuOpen])

  const handleClick = () => {
    navigate(`/project/${project.project_id}`)
  }

  const handleMenuToggle = (e: React.MouseEvent) => {
    e.stopPropagation()
    setMenuOpen((prev) => !prev)
  }

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation()
    setMenuOpen(false)
    onEdit?.(project)
  }

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation()
    setMenuOpen(false)
    onDelete?.(project)
  }

  return (
    <div className="project-card-wrapper">
      <button
        className="project-card"
        onClick={handleClick}
        id={`project-card-${project.project_id}`}
      >
        {/* Thumbnail */}
        <div className="project-card-thumb">
          <Thumbnail type={project.thumbnail_type} />
          <span className={`project-status-badge ${statusBadgeClass(project)}`}>
            {statusBadgeLabel(project)}
          </span>
        </div>

        {/* Info */}
        <div className="project-card-info">
          <div className="project-card-title-row">
            <h3 className="project-card-name">{project.display_name ?? project.name}</h3>
            <span className="project-card-status-icon">
              {project.starred && <Star size={14} fill="var(--amber)" color="var(--amber)" />}
              {project.status === 'active' && !project.starred && <Play size={14} fill="var(--lime)" color="var(--lime)" />}
              {project.status === 'empty' && <Circle size={14} color="var(--blue)" />}
              {project.status === 'draft' && !project.starred && project.thumbnail_type !== 'empty' && (
                <AlertCircle size={14} color="var(--teal)" />
              )}
            </span>
          </div>
          <p className="project-card-desc">{project.description}</p>
          <div className="project-card-footer">
            <span>Edited {timeAgo(project.updated_at)}</span>
            <span className="project-card-footer-sep">•</span>
            <span>{statusLabel(project)}</span>
          </div>
        </div>
      </button>

      {/* Context menu button */}
      <div className="project-card-menu-area" ref={menuRef}>
        <button
          className="project-card-menu-btn"
          onClick={handleMenuToggle}
          aria-label={`Options for ${project.name}`}
          id={`project-menu-${project.project_id}`}
        >
          <MoreVertical size={16} />
        </button>
        {menuOpen && (
          <div className="project-card-dropdown" id={`project-dropdown-${project.project_id}`}>
            <button className="dropdown-item" onClick={handleEdit} id={`edit-${project.project_id}`}>
              <Pencil size={13} />
              Rename / Edit
            </button>
            <button className="dropdown-item dropdown-item-danger" onClick={handleDelete} id={`delete-${project.project_id}`}>
              <Trash2 size={13} />
              Delete
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

interface NewProjectCardProps {
  onClick: () => void
}

export function NewProjectCard({ onClick }: NewProjectCardProps) {
  return (
    <button
      className="project-card project-card-new"
      onClick={onClick}
      id="new-project-card"
    >
      <div className="project-card-new-content">
        <div className="project-card-new-icon">+</div>
        <div className="project-card-new-label">New Project</div>
        <div className="project-card-new-hint">Upload footage to start</div>
      </div>
    </button>
  )
}

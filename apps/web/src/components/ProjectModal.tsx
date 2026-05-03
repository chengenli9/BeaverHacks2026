import { useState, useEffect, useRef } from 'react'
import { X, Trash2, AlertTriangle } from 'lucide-react'
import type { ProjectListItem } from '../types/api'

export type ModalMode = 'create' | 'edit' | 'delete'

interface Props {
  mode: ModalMode
  project?: ProjectListItem | null
  onClose: () => void
  onCreate: (name: string, description: string) => void
  onEdit: (projectId: string, name: string, description: string) => void
  onDelete: (projectId: string) => void
}

export function ProjectModal({ mode, project, onClose, onCreate, onEdit, onDelete }: Props) {
  const [name, setName] = useState(mode === 'edit' ? (project?.name ?? '') : '')
  const [description, setDescription] = useState(mode === 'edit' ? (project?.description ?? '') : '')
  const [confirmDelete, setConfirmDelete] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const overlayRef = useRef<HTMLDivElement>(null)

  // Focus input on open
  useEffect(() => {
    const timer = setTimeout(() => inputRef.current?.focus(), 50)
    return () => clearTimeout(timer)
  }, [])

  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  // Close on overlay click
  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) onClose()
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (mode === 'create') {
      if (!name.trim()) return
      onCreate(name.trim(), description.trim())
    } else if (mode === 'edit' && project) {
      if (!name.trim()) return
      onEdit(project.project_id, name.trim(), description.trim())
    } else if (mode === 'delete' && project) {
      onDelete(project.project_id)
    }
  }

  const deleteNameMatch = project ? confirmDelete === project.name : false

  return (
    <div className="modal-overlay" ref={overlayRef} onClick={handleOverlayClick} id="project-modal-overlay">
      <div className="modal" role="dialog" aria-modal="true" id="project-modal">
        {/* Header */}
        <div className="modal-header">
          <h2 className="modal-title">
            {mode === 'create' && 'New Project'}
            {mode === 'edit' && 'Edit Project'}
            {mode === 'delete' && 'Delete Project'}
          </h2>
          <button className="modal-close" onClick={onClose} aria-label="Close modal" id="modal-close">
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        <form className="modal-body" onSubmit={handleSubmit}>
          {mode === 'delete' ? (
            <div className="modal-delete-body">
              <div className="modal-delete-icon">
                <AlertTriangle size={32} />
              </div>
              <p className="modal-delete-text">
                Are you sure you want to delete <strong>{project?.name}</strong>? This action cannot be undone.
              </p>
              <label className="modal-label" htmlFor="delete-confirm">
                Type <strong>{project?.name}</strong> to confirm
              </label>
              <input
                ref={inputRef}
                id="delete-confirm"
                className="modal-input"
                type="text"
                value={confirmDelete}
                onChange={(e) => setConfirmDelete(e.target.value)}
                placeholder={project?.name}
                autoComplete="off"
              />
            </div>
          ) : (
            <>
              <label className="modal-label" htmlFor="project-name">Project Name</label>
              <input
                ref={inputRef}
                id="project-name"
                className="modal-input"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Enter project name..."
                maxLength={80}
                autoComplete="off"
              />

              <label className="modal-label" htmlFor="project-desc">Description <span className="modal-label-optional">(optional)</span></label>
              <textarea
                id="project-desc"
                className="modal-textarea"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Brief description of your project..."
                maxLength={300}
                rows={3}
              />

              {mode === 'edit' && project && (
                <div className="modal-meta">
                  <span className="modal-meta-item">ID: {project.project_id}</span>
                  <span className="modal-meta-item">Status: {project.status}</span>
                </div>
              )}
            </>
          )}

          {/* Footer */}
          <div className="modal-footer">
            <button type="button" className="modal-btn modal-btn-cancel" onClick={onClose} id="modal-cancel">
              Cancel
            </button>
            {mode === 'delete' ? (
              <button
                type="submit"
                className="modal-btn modal-btn-danger"
                disabled={!deleteNameMatch}
                id="modal-delete"
              >
                <Trash2 size={14} />
                Delete Project
              </button>
            ) : (
              <button
                type="submit"
                className="modal-btn modal-btn-primary"
                disabled={!name.trim()}
                id="modal-submit"
              >
                {mode === 'create' ? 'Create Project' : 'Save Changes'}
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}

import { useState, useEffect, useCallback } from 'react'
import { Search, LayoutGrid, List, Plus } from 'lucide-react'
import type { ProjectListItem } from '../types/api'
import { listProjects, updateProject, deleteProject } from '../api/scenerioApi'
import { navigate } from '../router'
import { HomeHeader } from './HomeHeader'
import { HomeSidebar } from './HomeSidebar'
import { ProjectCard, NewProjectCard } from './ProjectCard'
import { ProjectModal, type ModalMode } from './ProjectModal'
import { usePipelineActions } from '../state/pipelineStore'

const FILTER_CHIPS = ['All', 'Starred', 'In Progress', 'Exported'] as const

export function HomePage() {
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeChip, setActiveChip] = useState<string>('All')
  const [sidebarFilter, setSidebarFilter] = useState('all')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const { createNewProject } = usePipelineActions()

  // Modal state
  const [modalMode, setModalMode] = useState<ModalMode | null>(null)
  const [modalProject, setModalProject] = useState<ProjectListItem | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    listProjects()
      .then((data) => {
        if (!cancelled) setProjects(data)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  // ── Modal handlers ──────────────────────────────

  const openCreateModal = useCallback(() => {
    setModalProject(null)
    setModalMode('create')
  }, [])

  const openEditModal = useCallback((project: ProjectListItem) => {
    setModalProject(project)
    setModalMode('edit')
  }, [])

  const openDeleteModal = useCallback((project: ProjectListItem) => {
    setModalProject(project)
    setModalMode('delete')
  }, [])

  const closeModal = useCallback(() => {
    setModalMode(null)
    setModalProject(null)
  }, [])

  const handleCreate = useCallback(async (name: string) => {
    closeModal()
    try {
      const project = await createNewProject(name)
      // We can rely on the real project object from the backend now
      if (project) {
        setProjects((prev) => [project, ...prev])
        navigate(`/project/${project.project_id}`)
      }
    } catch (err) {
      console.error('Failed to create project', err)
    }
  }, [closeModal, createNewProject])

  const handleEdit = useCallback(async (projectId: string, name: string, description: string) => {
    closeModal()
    try {
      const updatedProject = await updateProject(projectId, name, description)
      setProjects((prev) =>
        prev.map((p) =>
          p.project_id === projectId
            ? { ...p, ...updatedProject }
            : p
        )
      )
    } catch (err) {
      console.error('Failed to update project', err)
    }
  }, [closeModal])

  const handleDelete = useCallback(async (projectId: string) => {
    closeModal()
    try {
      await deleteProject(projectId)
      setProjects((prev) => prev.filter((p) => p.project_id !== projectId))
    } catch (err) {
      console.error('Failed to delete project', err)
    }
  }, [closeModal])

  const handleToggleStar = useCallback(async (project: ProjectListItem) => {
    try {
      const newStarred = !project.starred
      // Optimistic update
      setProjects((prev) =>
        prev.map((p) =>
          p.project_id === project.project_id
            ? { ...p, starred: newStarred }
            : p
        )
      )
      await updateProject(project.project_id, project.name, project.description ?? '', newStarred)
    } catch (err) {
      console.error('Failed to toggle star', err)
      // Revert on error
      setProjects((prev) =>
        prev.map((p) =>
          p.project_id === project.project_id
            ? { ...p, starred: project.starred }
            : p
        )
      )
    }
  }, [])

  // ── Filtering ───────────────────────────────────

  const filtered = projects.filter((p) => {
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      const match =
        p.name.toLowerCase().includes(q) ||
        (p.description ?? '').toLowerCase().includes(q) ||
        p.project_id.toLowerCase().includes(q)
      if (!match) return false
    }

    if (activeChip === 'In Progress' && p.status !== 'in_progress' && p.status !== 'active') return false
    if (activeChip === 'Exported' && p.progress !== 100) return false
    if (activeChip === 'Starred' && !p.starred) return false

    if (sidebarFilter === 'starred' && !p.starred) return false

    return true
  })

  return (
    <div className="home-page">
      <HomeHeader />
      <div className="home-body">
        <HomeSidebar activeFilter={sidebarFilter} onFilterChange={setSidebarFilter} />

        <main className="home-main">
          {/* Title row */}
          <div className="home-title-row">
            <div>
              <h1 className="home-title">All Projects</h1>
              <p className="home-subtitle">
                {projects.length} project{projects.length !== 1 ? 's' : ''} · Last modified
              </p>
            </div>

            <div className="home-title-actions">
              <button
                className={`home-view-btn${viewMode === 'grid' ? ' active' : ''}`}
                onClick={() => setViewMode('grid')}
                aria-label="Grid view"
                id="view-grid"
              >
                <LayoutGrid size={16} />
              </button>
              <button
                className={`home-view-btn${viewMode === 'list' ? ' active' : ''}`}
                onClick={() => setViewMode('list')}
                aria-label="List view"
                id="view-list"
              >
                <List size={16} />
              </button>
              <button
                className="home-new-project-btn"
                onClick={openCreateModal}
                id="home-new-project-btn"
              >
                <Plus size={16} />
                New Project
              </button>
            </div>
          </div>

          {/* Search + Filter chips */}
          <div className="home-toolbar">
            <div className="home-search">
              <Search size={15} className="home-search-icon" />
              <input
                type="text"
                className="home-search-input"
                placeholder="Search projects..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                id="search-projects"
              />
            </div>
            <div className="home-chips">
              {FILTER_CHIPS.map((chip) => (
                <button
                  key={chip}
                  className={`home-chip${activeChip === chip ? ' active' : ''}`}
                  onClick={() => setActiveChip(chip)}
                  id={`chip-${chip.toLowerCase()}`}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>

          {/* Project grid */}
          {loading ? (
            <div className="home-loading">
              <div className="home-loading-spinner" />
              <p>Loading projects...</p>
            </div>
          ) : filtered.length === 0 && !searchQuery ? (
            <div className="home-empty">
              <h3>No projects yet</h3>
              <p>Create your first project to get started with Scenerio.</p>
              <button className="home-new-project-btn" onClick={openCreateModal}>
                <Plus size={16} /> New Project
              </button>
            </div>
          ) : (
            <div className={`project-grid${viewMode === 'list' ? ' project-grid-list' : ''}`}>
              {filtered.map((project) => (
                <ProjectCard
                  key={project.project_id}
                  project={project}
                  onEdit={openEditModal}
                  onDelete={openDeleteModal}
                  onToggleStar={handleToggleStar}
                />
              ))}
              <NewProjectCard onClick={openCreateModal} />
            </div>
          )}

          {searchQuery && filtered.length === 0 && (
            <div className="home-empty">
              <h3>No results</h3>
              <p>No projects match "{searchQuery}". Try a different search term.</p>
            </div>
          )}
        </main>
      </div>

      {/* Project Modal */}
      {modalMode && (
        <ProjectModal
          mode={modalMode}
          project={modalProject}
          onClose={closeModal}
          onCreate={handleCreate}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />
      )}
    </div>
  )
}

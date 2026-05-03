import { useState, useEffect, useCallback } from 'react'
import { Search, LayoutGrid, List, Plus } from 'lucide-react'
import type { ProjectListItem } from '../types/api'
import { listProjects } from '../api/directorloopApi'
import { navigate } from '../router'
import { HomeHeader } from './HomeHeader'
import { HomeSidebar } from './HomeSidebar'
import { ProjectCard, NewProjectCard } from './ProjectCard'
import { usePipelineActions } from '../state/pipelineStore'

const FILTER_CHIPS = ['All', 'Video', 'Draft', 'Active', 'Shared'] as const

export function HomePage() {
  const [projects, setProjects] = useState<ProjectListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeChip, setActiveChip] = useState<string>('All')
  const [sidebarFilter, setSidebarFilter] = useState('all')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const { createNewProject } = usePipelineActions()

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

  const handleNewProject = useCallback(async () => {
    await createNewProject('New Project')
    navigate('/project/new-project')
  }, [createNewProject])

  // Filter projects
  const filtered = projects.filter((p) => {
    // Search
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      const match =
        p.name.toLowerCase().includes(q) ||
        (p.description ?? '').toLowerCase().includes(q) ||
        p.project_id.toLowerCase().includes(q)
      if (!match) return false
    }

    // Chip filter
    if (activeChip === 'Draft' && p.status !== 'draft') return false
    if (activeChip === 'Active' && p.status !== 'active') return false

    // Sidebar filter
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
                onClick={handleNewProject}
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
              <p>Create your first project to get started with DirectorLoop.</p>
              <button className="home-new-project-btn" onClick={handleNewProject}>
                <Plus size={16} /> New Project
              </button>
            </div>
          ) : (
            <div className={`project-grid${viewMode === 'list' ? ' project-grid-list' : ''}`}>
              {filtered.map((project) => (
                <ProjectCard key={project.project_id} project={project} />
              ))}
              <NewProjectCard onClick={handleNewProject} />
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
    </div>
  )
}

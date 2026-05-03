import { useState } from 'react'
import {
  Clapperboard, Plus, Search, LayoutGrid, List, Star,
  Clock, FolderOpen, Archive, Users, Share2,
  Film, BarChart3, Smartphone, Gamepad2, FileText
} from 'lucide-react'

interface ProjectItem {
  id: string
  name: string
  description: string
  status: 'active' | 'draft' | 'starred' | 'shared'
  editedAgo: string
  progress?: number
  progressLabel?: string
  thumbnailType: 'timeline' | 'mobile' | 'analytics' | 'gameloop' | 'empty'
  starred?: boolean
}

const DEMO_PROJECTS: ProjectItem[] = [
  {
    id: 'demo_project',
    name: 'DirectorLoop — Demo Reel',
    description: 'AI rough cut with self-healing critic loop. Gemini indexed 47 scenes.',
    status: 'active',
    editedAgo: 'Edited 11 days ago',
    progress: 72,
    progressLabel: '72% complete',
    thumbnailType: 'timeline',
    starred: true,
  },
  {
    id: 'scout_ios',
    name: 'Scout — iOS',
    description: 'Mobile app walkthrough video. 12 screen recordings imported.',
    status: 'starred',
    editedAgo: 'Edited 11 days ago',
    progressLabel: 'Draft',
    thumbnailType: 'mobile',
  },
  {
    id: 'fitsync',
    name: 'FitSync',
    description: 'Product demo for FitSync dashboard. Narration pending TTS generation.',
    status: 'draft',
    editedAgo: 'Edited 10 months ago',
    progress: 30,
    progressLabel: '30% complete',
    thumbnailType: 'analytics',
  },
  {
    id: 'gameify',
    name: 'Gameify',
    description: 'Explainer video for gamification SDK. B-roll generation queued.',
    status: 'active',
    editedAgo: 'Edited 10 months ago',
    progressLabel: 'In progress',
    thumbnailType: 'gameloop',
  },
  {
    id: 'untitled',
    name: 'Untitled Project',
    description: 'Empty project. No footage imported yet.',
    status: 'draft',
    editedAgo: 'Edited 2 months ago',
    progressLabel: 'Empty',
    thumbnailType: 'empty',
  },
]

const NAV_WORKSPACE = [
  { label: 'All Projects', icon: FolderOpen, id: 'all' },
  { label: 'Recent', icon: Clock, id: 'recent' },
  { label: 'Starred', icon: Star, id: 'starred' },
  { label: 'Shared with me', icon: Share2, id: 'shared' },
]

const NAV_LIBRARY = [
  { label: 'Templates', icon: FileText, id: 'templates' },
  { label: 'Assets', icon: Film, id: 'assets' },
  { label: 'Archive', icon: Archive, id: 'archive' },
]

const FILTER_PILLS = ['All', 'Video', 'Draft', 'Active', 'Shared']

const STATUS_MAP: Record<string, { bg: string; color: string }> = {
  active: { bg: 'var(--teal)', color: 'var(--text-inverse)' },
  starred: { bg: 'var(--amber)', color: 'var(--text-inverse)' },
  draft: { bg: 'var(--bg-card-hover)', color: 'var(--text-secondary)' },
  shared: { bg: 'var(--blue)', color: 'var(--text-inverse)' },
}

/* Mini thumbnails rendered inline */
function ProjectThumbnail({ type }: { type: ProjectItem['thumbnailType'] }) {
  if (type === 'timeline') {
    return (
      <div className="hp-thumb hp-thumb-timeline">
        <div className="hp-tl-row">
          <div className="hp-tl-block" style={{ width: '30%', background: 'var(--teal)' }} />
          <div className="hp-tl-block" style={{ width: '20%', background: 'var(--blue)' }} />
          <div className="hp-tl-block" style={{ width: '25%', background: 'var(--teal)' }} />
        </div>
        <div className="hp-tl-row">
          <div className="hp-tl-block" style={{ width: '40%', background: 'var(--rose)' }} />
          <div className="hp-tl-block" style={{ width: '35%', background: 'var(--rose)', opacity: 0.5 }} />
        </div>
        <div className="hp-tl-row">
          <div className="hp-tl-block" style={{ width: '25%', background: 'var(--blue)', opacity: 0.6 }} />
          <div className="hp-tl-block" style={{ width: '45%', background: 'var(--emerald)' }} />
          <div className="hp-tl-block" style={{ width: '15%', background: 'var(--violet)' }} />
        </div>
      </div>
    )
  }
  if (type === 'mobile') {
    return (
      <div className="hp-thumb hp-thumb-mobile">
        <div className="hp-mobile-screen" />
        <div className="hp-mobile-screen" />
        <div className="hp-mobile-screen" style={{ height: '70%' }} />
      </div>
    )
  }
  if (type === 'analytics') {
    return (
      <div className="hp-thumb hp-thumb-analytics">
        {[65, 80, 45, 90, 55, 70, 85].map((h, i) => (
          <div key={i} className="hp-bar" style={{ height: `${h}%`, background: i % 2 === 0 ? 'var(--teal)' : 'var(--blue)' }} />
        ))}
      </div>
    )
  }
  if (type === 'gameloop') {
    return (
      <div className="hp-thumb hp-thumb-game">
        <div className="hp-circle" style={{ width: 28, height: 28, borderColor: 'var(--teal)' }} />
        <div className="hp-circle" style={{ width: 20, height: 20, borderColor: 'var(--teal)', opacity: .5 }} />
        <div className="hp-circle" style={{ width: 28, height: 28, borderColor: 'var(--teal)' }} />
      </div>
    )
  }
  return (
    <div className="hp-thumb hp-thumb-empty">
      <div className="hp-line" style={{ width: '60%' }} />
      <div className="hp-line" style={{ width: '80%' }} />
      <div className="hp-line" style={{ width: '45%' }} />
    </div>
  )
}

interface Props {
  onOpenProject: (projectId: string) => void
}

export function HomePage({ onOpenProject }: Props) {
  const [activeNav, setActiveNav] = useState('all')
  const [activeFilter, setActiveFilter] = useState('All')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [searchQuery, setSearchQuery] = useState('')

  const filtered = DEMO_PROJECTS.filter((p) => {
    if (searchQuery && !p.name.toLowerCase().includes(searchQuery.toLowerCase())) return false
    if (activeFilter === 'All') return true
    if (activeFilter === 'Draft') return p.status === 'draft'
    if (activeFilter === 'Active') return p.status === 'active'
    if (activeFilter === 'Shared') return p.status === 'shared'
    if (activeFilter === 'Video') return true
    return true
  })

  return (
    <div className="hp-layout">
      {/* ── LEFT SIDEBAR ── */}
      <aside className="hp-sidebar">
        <div className="hp-sidebar-logo">
          <Clapperboard size={22} />
          <div>
            <div className="hp-sidebar-brand">DirectorLoop</div>
            <div className="hp-sidebar-sub">AI VIDEO EDITOR</div>
          </div>
        </div>

        <div className="hp-nav-section">
          <div className="hp-nav-label">WORKSPACE</div>
          {NAV_WORKSPACE.map(({ label, icon: Icon, id }) => (
            <button
              key={id}
              className={`hp-nav-item ${activeNav === id ? 'active' : ''}`}
              onClick={() => setActiveNav(id)}
            >
              <Icon size={15} /> {label}
            </button>
          ))}
        </div>

        <div className="hp-nav-section">
          <div className="hp-nav-label">LIBRARY</div>
          {NAV_LIBRARY.map(({ label, icon: Icon, id }) => (
            <button
              key={id}
              className={`hp-nav-item ${activeNav === id ? 'active' : ''}`}
              onClick={() => setActiveNav(id)}
            >
              <Icon size={15} /> {label}
            </button>
          ))}
        </div>

        <div className="hp-nav-section">
          <div className="hp-nav-label">TEAM</div>
          <button className="hp-nav-item" onClick={() => {}}>
            <Users size={15} /> Kenneth's team
          </button>
        </div>

        <div className="hp-sidebar-user">
          <div className="hp-avatar">K</div>
          <div>
            <div className="hp-user-name">Kenneth</div>
            <div className="hp-user-plan">Free plan</div>
          </div>
        </div>
      </aside>

      {/* ── MAIN CONTENT ── */}
      <main className="hp-main">
        {/* Top bar */}
        <div className="hp-topbar">
          <span className="hp-breadcrumb">Drafts</span>
          <div className="hp-topbar-tabs">
            {['Design', 'Projects', 'Timeline', 'Export'].map((tab) => (
              <button
                key={tab}
                className={`hp-topbar-tab ${tab === 'Projects' ? 'active' : ''}`}
              >
                {tab}
              </button>
            ))}
          </div>
        </div>

        {/* Header */}
        <div className="hp-content-header">
          <div>
            <h1 className="hp-title">All Projects</h1>
            <p className="hp-subtitle">{filtered.length} projects · Last modified</p>
          </div>
          <div className="hp-header-actions">
            <button
              className={`hp-view-toggle ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
            >
              <LayoutGrid size={16} />
            </button>
            <button
              className={`hp-view-toggle ${viewMode === 'list' ? 'active' : ''}`}
              onClick={() => setViewMode('list')}
            >
              <List size={16} />
            </button>
            <button className="hp-new-project-btn" onClick={() => onOpenProject('demo_project')}>
              <Plus size={14} /> New Project
            </button>
          </div>
        </div>

        {/* Search + filters */}
        <div className="hp-filters">
          <div className="hp-search">
            <Search size={14} />
            <input
              type="text"
              placeholder="Search projects..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="hp-search-input"
            />
          </div>
          <div className="hp-pills">
            {FILTER_PILLS.map((pill) => (
              <button
                key={pill}
                className={`hp-pill ${activeFilter === pill ? 'active' : ''}`}
                onClick={() => setActiveFilter(pill)}
              >
                {pill}
              </button>
            ))}
          </div>
        </div>

        {/* Project grid */}
        <div className={`hp-projects ${viewMode === 'list' ? 'hp-projects-list' : ''}`}>
          {filtered.map((project) => {
            const statusStyle = STATUS_MAP[project.status]
            return (
              <div
                key={project.id}
                className="hp-project-card"
                onClick={() => onOpenProject(project.id)}
                id={`project-${project.id}`}
              >
                <div className="hp-card-preview">
                  <span className="hp-card-type">{project.thumbnailType.replace('_', ' ').toUpperCase()}</span>
                  <span
                    className="hp-card-status"
                    style={{ background: statusStyle.bg, color: statusStyle.color }}
                  >
                    {project.status.charAt(0).toUpperCase() + project.status.slice(1)}
                  </span>
                  <ProjectThumbnail type={project.thumbnailType} />
                  {project.starred && (
                    <Star size={16} className="hp-star" fill="var(--amber)" color="var(--amber)" />
                  )}
                </div>
                <div className="hp-card-info">
                  <div className="hp-card-name">
                    {project.name}
                    <span className="hp-card-dot" style={{ background: statusStyle.bg }} />
                  </div>
                  <p className="hp-card-desc">{project.description}</p>
                  <div className="hp-card-footer">
                    <span>{project.editedAgo}</span>
                    {project.progressLabel && (
                      <>
                        <span className="hp-card-sep">·</span>
                        <span>{project.progressLabel}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )
          })}

          {/* New project card */}
          <div className="hp-project-card hp-new-card" onClick={() => onOpenProject('new_project')}>
            <div className="hp-new-card-inner">
              <div className="hp-new-card-icon">
                <Plus size={24} />
              </div>
              <span className="hp-new-card-label">New Project</span>
              <span className="hp-new-card-hint">Upload footage to start</span>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

import {
  FolderKanban, Clock, Star, Users,
  LayoutTemplate, Package, Archive,
  UsersRound, Mail,
} from 'lucide-react'

interface SidebarItem {
  icon: React.ReactNode
  label: string
  id: string
}

interface SidebarSection {
  title: string
  items: SidebarItem[]
}

const SECTIONS: SidebarSection[] = [
  {
    title: 'Workspace',
    items: [
      { icon: <FolderKanban size={15} />, label: 'All Projects', id: 'all' },
      { icon: <Clock size={15} />, label: 'Recent', id: 'recent' },
      { icon: <Star size={15} />, label: 'Starred', id: 'starred' },
      { icon: <Users size={15} />, label: 'Shared with me', id: 'shared' },
    ],
  },
  {
    title: 'Library',
    items: [
      { icon: <LayoutTemplate size={15} />, label: 'Templates', id: 'templates' },
      { icon: <Package size={15} />, label: 'Assets', id: 'assets' },
      { icon: <Archive size={15} />, label: 'Archive', id: 'archive' },
    ],
  },
  {
    title: 'Team',
    items: [
      { icon: <UsersRound size={15} />, label: "Kenneth's team", id: 'team' },
      { icon: <Mail size={15} />, label: 'Invitations', id: 'invitations' },
    ],
  },
]

interface Props {
  activeFilter: string
  onFilterChange: (id: string) => void
}

export function HomeSidebar({ activeFilter, onFilterChange }: Props) {
  return (
    <aside className="home-sidebar">
      {SECTIONS.map((section) => (
        <div key={section.title} className="sidebar-section">
          <div className="sidebar-section-title">{section.title}</div>
          {section.items.map((item) => (
            <button
              key={item.id}
              className={`sidebar-item${activeFilter === item.id ? ' active' : ''}`}
              onClick={() => onFilterChange(item.id)}
              id={`sidebar-${item.id}`}
            >
              <span className="sidebar-item-icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </div>
      ))}

      {/* User badge at bottom */}
      <div className="sidebar-user">
        <div className="sidebar-user-avatar">K</div>
        <div className="sidebar-user-info">
          <div className="sidebar-user-name">Kenneth</div>
          <div className="sidebar-user-plan">Free plan</div>
        </div>
      </div>
    </aside>
  )
}

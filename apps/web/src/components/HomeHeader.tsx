import { Clapperboard } from 'lucide-react'

const TABS = ['Design', 'Projects', 'Timeline', 'Export'] as const

interface Props {
  activeTab?: string
}

export function HomeHeader({ activeTab = 'Projects' }: Props) {
  return (
    <header className="home-header">
      <div className="app-logo">
        <Clapperboard size={20} />
        DirectorLoop
      </div>
      <span className="home-header-subtitle">AI VIDEO EDITOR</span>

      <nav className="home-header-tabs">
        {TABS.map((tab) => (
          <button
            key={tab}
            className={`home-header-tab${activeTab === tab ? ' active' : ''}`}
            id={`header-tab-${tab.toLowerCase()}`}
          >
            {tab}
          </button>
        ))}
      </nav>
    </header>
  )
}

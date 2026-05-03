import { Clapperboard } from 'lucide-react'

export function HomeHeader() {
  return (
    <header className="home-header">
      <div className="app-logo">
        <Clapperboard size={20} />
        DirectorLoop
      </div>
      <span className="home-header-subtitle">AI VIDEO EDITOR</span>

    </header>
  )
}

import { useState } from 'react'
import { PipelineProvider } from './state/pipelineStore'
import { AppShell } from './components/AppShell'
import { HomePage } from './components/HomePage'

function App() {
  const [currentView, setCurrentView] = useState<'home' | 'editor'>('home')
  const [selectedProject, setSelectedProject] = useState<string | null>(null)

  const handleOpenProject = (projectId: string) => {
    setSelectedProject(projectId)
    setCurrentView('editor')
  }

  const handleBackToHome = () => {
    setCurrentView('home')
    setSelectedProject(null)
  }

  if (currentView === 'home') {
    return <HomePage onOpenProject={handleOpenProject} />
  }

  return (
    <PipelineProvider>
      <AppShell onBack={handleBackToHome} />
    </PipelineProvider>
  )
}

export default App

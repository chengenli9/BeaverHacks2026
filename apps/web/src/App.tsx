import { PipelineProvider } from './state/PipelineProvider'
import { useRoute } from './router'
import { AppShell } from './components/AppShell'
import { HomePage } from './components/HomePage'

function AppRouter() {
  const route = useRoute()

  if (route.page === 'project') {
    return <AppShell projectId={route.projectId} />
  }

  return <HomePage />
}

function App() {
  return (
    <PipelineProvider>
      <AppRouter />
    </PipelineProvider>
  )
}

export default App

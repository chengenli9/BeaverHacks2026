import { PipelineProvider } from './state/pipelineStore'
import { AppShell } from './components/AppShell'

function App() {
  return (
    <PipelineProvider>
      <AppShell />
    </PipelineProvider>
  )
}

export default App

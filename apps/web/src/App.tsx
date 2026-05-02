import { PipelineProvider } from './state/PipelineProvider'
import { AppShell } from './components/AppShell'

function App() {
  return (
    <PipelineProvider>
      <AppShell />
    </PipelineProvider>
  )
}

export default App

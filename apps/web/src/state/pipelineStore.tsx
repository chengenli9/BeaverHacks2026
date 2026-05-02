import {
  createContext,
  useContext,
  useReducer,
  useCallback,
  useRef,
  useEffect,
  type ReactNode,
  type Dispatch,
} from 'react'
import type {
  JobStatus,
  JobKind,
  SceneIndex,
  Plan,
  BlockManifest,
  CriticSuggestions,
  RenderSummary,
  EventLogEntry,
  ProjectSummary,
} from '../types/api'
import * as api from '../api/directorloopApi'

export interface PipelineState {
  projectId: string | null
  projectName: string | null
  activeJobs: Record<string, JobStatus>
  sceneIndex: SceneIndex | null
  plan: Plan | null
  manifest: BlockManifest | null
  criticSuggestions: CriticSuggestions | null
  renderSummary: RenderSummary | null
  eventLog: EventLogEntry[]
  approvalState: Record<string, 'approved' | 'rejected' | 'pending'>
  pipelineStages: Record<string, 'idle' | 'running' | 'succeeded' | 'failed'>
}

const initialState: PipelineState = {
  projectId: null,
  projectName: null,
  activeJobs: {},
  sceneIndex: null,
  plan: null,
  manifest: null,
  criticSuggestions: null,
  renderSummary: null,
  eventLog: [],
  approvalState: {},
  pipelineStages: {
    'analyze-scenes': 'idle',
    'generate-plan': 'idle',
    'generate-tts': 'idle',
    'generate-assets': 'idle',
    'build-manifest': 'idle',
    'precritique': 'idle',
    'render': 'idle',
  },
}

type Action =
  | { type: 'SET_PROJECT'; payload: ProjectSummary }
  | { type: 'SET_JOB'; payload: JobStatus }
  | { type: 'REMOVE_JOB'; payload: string }
  | { type: 'SET_SCENE_INDEX'; payload: SceneIndex }
  | { type: 'SET_PLAN'; payload: Plan }
  | { type: 'SET_MANIFEST'; payload: BlockManifest }
  | { type: 'SET_CRITIC_SUGGESTIONS'; payload: CriticSuggestions }
  | { type: 'SET_RENDER_SUMMARY'; payload: RenderSummary }
  | { type: 'ADD_EVENT'; payload: EventLogEntry }
  | { type: 'SET_APPROVAL'; payload: { id: string; value: 'approved' | 'rejected' | 'pending' } }
  | { type: 'SET_STAGE'; payload: { stage: string; status: 'idle' | 'running' | 'succeeded' | 'failed' } }
  | { type: 'RESET' }

function reducer(state: PipelineState, action: Action): PipelineState {
  switch (action.type) {
    case 'SET_PROJECT':
      return { ...state, projectId: action.payload.project_id, projectName: action.payload.name ?? action.payload.project_id }
    case 'SET_JOB':
      return { ...state, activeJobs: { ...state.activeJobs, [action.payload.job_id]: action.payload } }
    case 'REMOVE_JOB': {
      const { [action.payload]: _, ...rest } = state.activeJobs
      void _
      return { ...state, activeJobs: rest }
    }
    case 'SET_SCENE_INDEX':
      return { ...state, sceneIndex: action.payload }
    case 'SET_PLAN':
      return { ...state, plan: action.payload }
    case 'SET_MANIFEST':
      return { ...state, manifest: action.payload }
    case 'SET_CRITIC_SUGGESTIONS': {
      const approvalState: Record<string, 'pending'> = {}
      for (const s of action.payload.suggestions) approvalState[s.suggestion_id] = 'pending'
      return { ...state, criticSuggestions: action.payload, approvalState }
    }
    case 'SET_RENDER_SUMMARY':
      return { ...state, renderSummary: action.payload }
    case 'ADD_EVENT':
      return { ...state, eventLog: [...state.eventLog, action.payload] }
    case 'SET_APPROVAL':
      return { ...state, approvalState: { ...state.approvalState, [action.payload.id]: action.payload.value } }
    case 'SET_STAGE':
      return { ...state, pipelineStages: { ...state.pipelineStages, [action.payload.stage]: action.payload.status } }
    case 'RESET':
      return initialState
    default:
      return state
  }
}

const PipelineContext = createContext<PipelineState>(initialState)
const DispatchContext = createContext<Dispatch<Action>>(() => {})

export function PipelineProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState)
  return (
    <PipelineContext.Provider value={state}>
      <DispatchContext.Provider value={dispatch}>{children}</DispatchContext.Provider>
    </PipelineContext.Provider>
  )
}

export function usePipeline() { return useContext(PipelineContext) }
export function useDispatch() { return useContext(DispatchContext) }

let eventCounter = 0
export function makeEvent(type: EventLogEntry['type'], message: string, extra?: Partial<EventLogEntry>): EventLogEntry {
  return { id: `evt_${++eventCounter}_${Date.now()}`, timestamp: new Date().toISOString(), type, message, ...extra }
}

async function fetchArtifact(dispatch: Dispatch<Action>, stage: string, projectId: string) {
  try {
    if (stage === 'analyze-scenes') {
      const d = await api.getSceneIndex(projectId); dispatch({ type: 'SET_SCENE_INDEX', payload: d })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Scene index: ${d.scenes.length} scenes`) })
    } else if (stage === 'generate-plan') {
      const d = await api.getPlan(projectId); dispatch({ type: 'SET_PLAN', payload: d })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Plan: "${d.title}" — ${d.beats.length} beats`) })
    } else if (stage === 'build-manifest') {
      const d = await api.getManifest(projectId); dispatch({ type: 'SET_MANIFEST', payload: d })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Manifest: ${d.blocks.length} blocks`) })
    } else if (stage === 'precritique') {
      const d = await api.getCriticSuggestions(projectId); dispatch({ type: 'SET_CRITIC_SUGGESTIONS', payload: d })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Critic: ${d.suggestions.length} suggestions`) })
    } else if (stage === 'render') {
      const d = await api.getRender(projectId); dispatch({ type: 'SET_RENDER_SUMMARY', payload: d })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Render: ${d.duration.toFixed(1)}s`) })
    } else if (stage === 'apply-approved-patches') {
      const d = await api.getManifest(projectId); dispatch({ type: 'SET_MANIFEST', payload: d })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', 'Manifest updated') })
    }
  } catch { /* artifact not ready */ }
}

export function useJobPoller() {
  const dispatch = useDispatch()
  const state = usePipeline()
  const pollTimers = useRef<Record<string, ReturnType<typeof setInterval>>>({})
  const projectRef = useRef(state.projectId)
  projectRef.current = state.projectId

  const stopPolling = useCallback((jobId: string) => {
    if (pollTimers.current[jobId]) { clearInterval(pollTimers.current[jobId]); delete pollTimers.current[jobId] }
  }, [])

  const startPolling = useCallback((jobId: string, stage: string) => {
    stopPolling(jobId)
    dispatch({ type: 'SET_STAGE', payload: { stage, status: 'running' } })
    dispatch({ type: 'ADD_EVENT', payload: makeEvent('info', `Job started: ${stage}`, { jobId, stage }) })
    pollTimers.current[jobId] = setInterval(async () => {
      try {
        const job = await api.getJob(jobId)
        dispatch({ type: 'SET_JOB', payload: job })
        if (job.status === 'succeeded') {
          stopPolling(jobId)
          dispatch({ type: 'SET_STAGE', payload: { stage, status: 'succeeded' } })
          dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Completed: ${stage}`, { jobId }) })
          if (projectRef.current) await fetchArtifact(dispatch, stage, projectRef.current)
        } else if (job.status === 'failed') {
          stopPolling(jobId)
          dispatch({ type: 'SET_STAGE', payload: { stage, status: 'failed' } })
          dispatch({ type: 'ADD_EVENT', payload: makeEvent('error', `Failed: ${stage} — ${job.error ?? 'Unknown'}`, { jobId }) })
        }
      } catch (err) {
        dispatch({ type: 'ADD_EVENT', payload: makeEvent('warning', `Poll error: ${err instanceof Error ? err.message : 'Unknown'}`) })
      }
    }, 1000)
  }, [dispatch, stopPolling])

  useEffect(() => { return () => { Object.values(pollTimers.current).forEach(clearInterval) } }, [])
  return { startPolling, stopPolling }
}

export function usePipelineActions() {
  const dispatch = useDispatch()
  const state = usePipeline()
  const { startPolling } = useJobPoller()

  const openDemo = useCallback(async () => {
    try {
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('info', 'Opening demo project…') })
      const project = await api.openDemoProject()
      dispatch({ type: 'SET_PROJECT', payload: project })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Project: ${project.project_id}`) })
      // Load existing artifacts
      const pid = project.project_id
      try { const d = await api.getSceneIndex(pid); dispatch({ type: 'SET_SCENE_INDEX', payload: d }); dispatch({ type: 'SET_STAGE', payload: { stage: 'analyze-scenes', status: 'succeeded' } }) } catch {}
      try { const d = await api.getPlan(pid); dispatch({ type: 'SET_PLAN', payload: d }); dispatch({ type: 'SET_STAGE', payload: { stage: 'generate-plan', status: 'succeeded' } }) } catch {}
      try { const d = await api.getManifest(pid); dispatch({ type: 'SET_MANIFEST', payload: d }); dispatch({ type: 'SET_STAGE', payload: { stage: 'build-manifest', status: 'succeeded' } }) } catch {}
      try { const d = await api.getCriticSuggestions(pid); dispatch({ type: 'SET_CRITIC_SUGGESTIONS', payload: d }); dispatch({ type: 'SET_STAGE', payload: { stage: 'precritique', status: 'succeeded' } }) } catch {}
      try { const d = await api.getRender(pid); dispatch({ type: 'SET_RENDER_SUMMARY', payload: d }); dispatch({ type: 'SET_STAGE', payload: { stage: 'render', status: 'succeeded' } }) } catch {}
    } catch (err) {
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('error', `Failed: ${err instanceof Error ? err.message : 'Unknown'}`) })
    }
  }, [dispatch])

  const runStage = useCallback(async (kind: JobKind, body?: unknown) => {
    if (!state.projectId) return
    try {
      const { job_id } = await api.startJob(kind, body ?? { project_id: state.projectId })
      dispatch({ type: 'SET_JOB', payload: { job_id, project_id: state.projectId, status: 'queued', stage: kind, progress: 0, message: null, error: null, created_at: new Date().toISOString(), updated_at: new Date().toISOString() } })
      startPolling(job_id, kind)
    } catch (err) {
      dispatch({ type: 'SET_STAGE', payload: { stage: kind, status: 'failed' } })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('error', `Failed to start ${kind}: ${err instanceof Error ? err.message : 'Unknown'}`) })
    }
  }, [dispatch, state.projectId, startPolling])

  const submitApprovals = useCallback(async () => {
    if (!state.projectId) return
    const approved: string[] = [], rejected: string[] = []
    for (const [id, val] of Object.entries(state.approvalState)) {
      if (val === 'approved') approved.push(id)
      if (val === 'rejected') rejected.push(id)
    }
    try {
      const { job_id } = await api.applyApprovedPatches({ project_id: state.projectId, approved_suggestion_ids: approved, rejected_suggestion_ids: rejected })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('info', `Applying ${approved.length} approved, ${rejected.length} rejected`) })
      startPolling(job_id, 'apply-approved-patches')
    } catch (err) {
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('error', `Patch error: ${err instanceof Error ? err.message : 'Unknown'}`) })
    }
  }, [dispatch, state.projectId, state.approvalState, startPolling])

  const setApproval = useCallback((id: string, value: 'approved' | 'rejected' | 'pending') => {
    dispatch({ type: 'SET_APPROVAL', payload: { id, value } })
  }, [dispatch])

  return { openDemo, runStage, submitApprovals, setApproval }
}

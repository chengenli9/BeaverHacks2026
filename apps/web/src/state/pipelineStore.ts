import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  type Dispatch,
} from 'react'
import * as api from '../api/directorloopApi'
import type {
  BlockManifest,
  CriticSuggestions,
  EventLogEntry,
  JobKind,
  JobStatus,
  PipelineJobKind,
  PipelineStageKey,
  Plan,
  ProjectSummary,
  RenderSummary,
  SceneIndex,
} from '../types/api'

type StageRunStatus = 'idle' | 'running' | 'succeeded' | 'failed'
type ApprovalValue = 'approved' | 'rejected' | 'pending'

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
  approvalState: Record<string, ApprovalValue>
  pipelineStages: Record<PipelineStageKey, StageRunStatus>
}

export type PipelineAction =
  | { type: 'SET_PROJECT'; payload: ProjectSummary }
  | { type: 'SET_JOB'; payload: JobStatus }
  | { type: 'REMOVE_JOB'; payload: string }
  | { type: 'SET_SCENE_INDEX'; payload: SceneIndex }
  | { type: 'SET_PLAN'; payload: Plan }
  | { type: 'SET_MANIFEST'; payload: BlockManifest }
  | { type: 'SET_CRITIC_SUGGESTIONS'; payload: CriticSuggestions }
  | { type: 'SET_RENDER_SUMMARY'; payload: RenderSummary }
  | { type: 'ADD_EVENT'; payload: EventLogEntry }
  | { type: 'SET_APPROVAL'; payload: { id: string; value: ApprovalValue } }
  | { type: 'SET_STAGE'; payload: { stage: PipelineStageKey; status: StageRunStatus } }
  | { type: 'RESET' }

export const initialState: PipelineState = {
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
    precritique: 'idle',
    render: 'idle',
    'apply-approved-patches': 'idle',
  },
}

export const PipelineContext = createContext<PipelineState>(initialState)
export const DispatchContext = createContext<Dispatch<PipelineAction>>(() => undefined)

export function reducer(state: PipelineState, action: PipelineAction): PipelineState {
  switch (action.type) {
    case 'SET_PROJECT':
      return {
        ...state,
        projectId: action.payload.project_id,
        projectName: action.payload.name ?? action.payload.project_id,
      }
    case 'SET_JOB':
      return { ...state, activeJobs: { ...state.activeJobs, [action.payload.job_id]: action.payload } }
    case 'REMOVE_JOB': {
      const { [action.payload]: removed, ...rest } = state.activeJobs
      void removed
      return { ...state, activeJobs: rest }
    }
    case 'SET_SCENE_INDEX':
      return { ...state, sceneIndex: action.payload }
    case 'SET_PLAN':
      return { ...state, plan: action.payload }
    case 'SET_MANIFEST':
      return { ...state, manifest: action.payload }
    case 'SET_CRITIC_SUGGESTIONS': {
      const approvalState: Record<string, ApprovalValue> = {}
      for (const suggestion of action.payload.suggestions) {
        approvalState[suggestion.suggestion_id] = 'pending'
      }
      return { ...state, criticSuggestions: action.payload, approvalState }
    }
    case 'SET_RENDER_SUMMARY':
      return { ...state, renderSummary: action.payload }
    case 'ADD_EVENT':
      return { ...state, eventLog: [...state.eventLog, action.payload] }
    case 'SET_APPROVAL':
      return {
        ...state,
        approvalState: { ...state.approvalState, [action.payload.id]: action.payload.value },
      }
    case 'SET_STAGE':
      return {
        ...state,
        pipelineStages: { ...state.pipelineStages, [action.payload.stage]: action.payload.status },
      }
    case 'RESET':
      return initialState
    default:
      return state
  }
}

export function usePipeline() {
  return useContext(PipelineContext)
}

export function useDispatch() {
  return useContext(DispatchContext)
}

let eventCounter = 0

export function makeEvent(
  type: EventLogEntry['type'],
  message: string,
  extra?: Partial<EventLogEntry>,
): EventLogEntry {
  return {
    id: `evt_${++eventCounter}_${Date.now()}`,
    timestamp: new Date().toISOString(),
    type,
    message,
    ...extra,
  }
}

const BACKEND_STAGE_TO_FRONTEND: Record<string, PipelineStageKey> = {
  analyzing_scenes: 'analyze-scenes',
  generating_plan: 'generate-plan',
  generating_tts: 'generate-tts',
  generating_assets: 'generate-assets',
  building_manifest: 'build-manifest',
  precritique: 'precritique',
  rendering: 'render',
  apply_patches: 'apply-approved-patches',
}

function normalizeStage(stage: string | null, fallback: PipelineStageKey): PipelineStageKey {
  return stage ? BACKEND_STAGE_TO_FRONTEND[stage] ?? (stage as PipelineStageKey) : fallback
}

function makeQueuedJob(jobId: string, projectId: string, stage: PipelineStageKey): JobStatus {
  const now = new Date().toISOString()
  return {
    job_id: jobId,
    project_id: projectId,
    status: 'queued',
    stage,
    progress: 0,
    message: null,
    error: null,
    created_at: now,
    updated_at: now,
  }
}

async function fetchArtifact(
  dispatch: Dispatch<PipelineAction>,
  stage: PipelineStageKey,
  projectId: string,
) {
  try {
    if (stage === 'analyze-scenes') {
      const data = await api.getSceneIndex(projectId)
      dispatch({ type: 'SET_SCENE_INDEX', payload: data })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Scene index: ${data.scenes.length} scenes`) })
    } else if (stage === 'generate-plan') {
      const data = await api.getPlan(projectId)
      dispatch({ type: 'SET_PLAN', payload: data })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Plan: "${data.title}" - ${data.beats.length} beats`) })
    } else if (stage === 'build-manifest') {
      const data = await api.getManifest(projectId)
      dispatch({ type: 'SET_MANIFEST', payload: data })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Manifest: ${data.blocks.length} blocks`) })
    } else if (stage === 'precritique') {
      const data = await api.getCriticSuggestions(projectId)
      dispatch({ type: 'SET_CRITIC_SUGGESTIONS', payload: data })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Critic: ${data.suggestions.length} suggestions`) })
    } else if (stage === 'render') {
      const data = await api.getRender(projectId)
      dispatch({ type: 'SET_RENDER_SUMMARY', payload: data })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Render: ${data.duration.toFixed(1)}s`) })
    } else if (stage === 'apply-approved-patches') {
      const data = await api.getManifest(projectId)
      dispatch({ type: 'SET_MANIFEST', payload: data })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', 'Manifest updated') })
    }
  } catch (error) {
    dispatch({
      type: 'ADD_EVENT',
      payload: makeEvent('warning', `Artifact not ready for ${stage}: ${error instanceof Error ? error.message : 'Unknown'}`),
    })
  }
}

async function loadIfAvailable(load: () => Promise<void>) {
  try {
    await load()
  } catch {
    return
  }
}

export function useJobPoller() {
  const dispatch = useDispatch()
  const pollTimers = useRef<Record<string, ReturnType<typeof setInterval>>>({})

  const stopPolling = useCallback((jobId: string) => {
    if (pollTimers.current[jobId]) {
      clearInterval(pollTimers.current[jobId])
      delete pollTimers.current[jobId]
    }
  }, [])

  const startPolling = useCallback((jobId: string, stage: PipelineStageKey, projectId: string) => {
    stopPolling(jobId)
    dispatch({ type: 'SET_STAGE', payload: { stage, status: 'running' } })
    dispatch({ type: 'ADD_EVENT', payload: makeEvent('info', `Job started: ${stage}`, { jobId, stage }) })

    pollTimers.current[jobId] = setInterval(async () => {
      try {
        const job = await api.getJob(jobId)
        const frontendStage = normalizeStage(job.stage, stage)
        const normalizedJob = { ...job, stage: frontendStage }
        dispatch({ type: 'SET_JOB', payload: normalizedJob })

        if (job.status === 'succeeded') {
          stopPolling(jobId)
          dispatch({ type: 'SET_STAGE', payload: { stage: frontendStage, status: 'succeeded' } })
          dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Completed: ${frontendStage}`, { jobId }) })
          await fetchArtifact(dispatch, frontendStage, projectId)
        } else if (job.status === 'failed') {
          stopPolling(jobId)
          dispatch({ type: 'SET_STAGE', payload: { stage: frontendStage, status: 'failed' } })
          dispatch({
            type: 'ADD_EVENT',
            payload: makeEvent('error', `Failed: ${frontendStage} - ${job.error ?? 'Unknown'}`, { jobId }),
          })
        }
      } catch (error) {
        dispatch({
          type: 'ADD_EVENT',
          payload: makeEvent('warning', `Poll error: ${error instanceof Error ? error.message : 'Unknown'}`),
        })
      }
    }, 1000)
  }, [dispatch, stopPolling])

  useEffect(() => {
    const timers = pollTimers.current
    return () => {
      Object.values(timers).forEach(clearInterval)
    }
  }, [])

  return { startPolling, stopPolling }
}

export function usePipelineActions() {
  const dispatch = useDispatch()
  const state = usePipeline()
  const { startPolling } = useJobPoller()

  const openDemo = useCallback(async () => {
    try {
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('info', 'Opening demo project...') })
      const project = await api.openDemoProject()
      const projectId = project.project_id
      dispatch({ type: 'SET_PROJECT', payload: project })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Project: ${projectId}`) })

      await loadIfAvailable(async () => {
        const data = await api.getSceneIndex(projectId)
        dispatch({ type: 'SET_SCENE_INDEX', payload: data })
        dispatch({ type: 'SET_STAGE', payload: { stage: 'analyze-scenes', status: 'succeeded' } })
      })
      await loadIfAvailable(async () => {
        const data = await api.getPlan(projectId)
        dispatch({ type: 'SET_PLAN', payload: data })
        dispatch({ type: 'SET_STAGE', payload: { stage: 'generate-plan', status: 'succeeded' } })
      })
      await loadIfAvailable(async () => {
        const data = await api.getManifest(projectId)
        dispatch({ type: 'SET_MANIFEST', payload: data })
        dispatch({ type: 'SET_STAGE', payload: { stage: 'build-manifest', status: 'succeeded' } })
      })
      await loadIfAvailable(async () => {
        const data = await api.getCriticSuggestions(projectId)
        dispatch({ type: 'SET_CRITIC_SUGGESTIONS', payload: data })
        dispatch({ type: 'SET_STAGE', payload: { stage: 'precritique', status: 'succeeded' } })
      })
      await loadIfAvailable(async () => {
        const data = await api.getRender(projectId)
        dispatch({ type: 'SET_RENDER_SUMMARY', payload: data })
        dispatch({ type: 'SET_STAGE', payload: { stage: 'render', status: 'succeeded' } })
      })
    } catch (error) {
      dispatch({
        type: 'ADD_EVENT',
        payload: makeEvent('error', `Failed: ${error instanceof Error ? error.message : 'Unknown'}`),
      })
    }
  }, [dispatch])

  const runStage = useCallback(async (kind: PipelineJobKind) => {
    if (!state.projectId) return

    try {
      const { job_id } = await api.startJob(kind, state.projectId)
      dispatch({ type: 'SET_JOB', payload: makeQueuedJob(job_id, state.projectId, kind) })
      startPolling(job_id, kind, state.projectId)
    } catch (error) {
      dispatch({ type: 'SET_STAGE', payload: { stage: kind, status: 'failed' } })
      dispatch({
        type: 'ADD_EVENT',
        payload: makeEvent('error', `Failed to start ${kind}: ${error instanceof Error ? error.message : 'Unknown'}`),
      })
    }
  }, [dispatch, startPolling, state.projectId])

  const submitApprovals = useCallback(async () => {
    if (!state.projectId) return

    const approved: string[] = []
    const rejected: string[] = []
    for (const [id, value] of Object.entries(state.approvalState)) {
      if (value === 'approved') approved.push(id)
      if (value === 'rejected') rejected.push(id)
    }

    try {
      const { job_id } = await api.applyApprovedPatches({
        project_id: state.projectId,
        approved_suggestion_ids: approved,
        rejected_suggestion_ids: rejected,
      })
      dispatch({ type: 'SET_JOB', payload: makeQueuedJob(job_id, state.projectId, 'apply-approved-patches') })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('info', `Applying ${approved.length} approved, ${rejected.length} rejected`) })
      startPolling(job_id, 'apply-approved-patches', state.projectId)
    } catch (error) {
      dispatch({
        type: 'ADD_EVENT',
        payload: makeEvent('error', `Patch error: ${error instanceof Error ? error.message : 'Unknown'}`),
      })
    }
  }, [dispatch, startPolling, state.approvalState, state.projectId])

  const setApproval = useCallback((id: string, value: ApprovalValue) => {
    dispatch({ type: 'SET_APPROVAL', payload: { id, value } })
  }, [dispatch])

  return { openDemo, runStage, submitApprovals, setApproval }
}

export type { ApprovalValue, JobKind, PipelineJobKind, PipelineStageKey, StageRunStatus }

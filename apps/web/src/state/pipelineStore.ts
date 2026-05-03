import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  type Dispatch,
} from 'react'
import * as api from '../api/scenerioApi'
import type {
  BlockManifest,
  CriticSuggestions,
  CreateBeatRequest,
  EventLogEntry,
  JobKind,
  JobStatus,
  MediaProbe,
  MediaNode,
  MediaTree,
  MusicTrackRef,
  PipelineJobKind,
  PipelineStageKey,
  Plan,
  ProjectSummary,
  RenderQa,
  RenderSummary,
  SceneIndex,
  ShotIndex,
} from '../types/api'

type StageRunStatus = 'idle' | 'running' | 'succeeded' | 'failed'
type ApprovalValue = 'approved' | 'rejected' | 'pending' | 'dismissed'

interface UndoSnapshot {
  plan: Plan | null
  manifest: BlockManifest | null
}

const MAX_UNDO = 30

export interface PipelineState {
  projectId: string | null
  projectName: string | null
  activeJobs: Record<string, JobStatus>
  sceneIndex: SceneIndex | null
  mediaProbe: MediaProbe | null
  shotIndex: ShotIndex | null
  plan: Plan | null
  manifest: BlockManifest | null
  criticSuggestions: CriticSuggestions | null
  renderSummary: RenderSummary | null
  renderQa: RenderQa | null
  mediaTree: MediaTree | null
  selectedMedia: MediaNode | null
  eventLog: EventLogEntry[]
  approvalState: Record<string, ApprovalValue>
  pipelineStages: Record<PipelineStageKey, StageRunStatus>
  highlightedBlockId: string | null
  selectedBlockId: string | null
  musicLibrary: MusicTrackRef[]
  undoStack: UndoSnapshot[]
  redoStack: UndoSnapshot[]
}

export type PipelineAction =
  | { type: 'SET_PROJECT'; payload: ProjectSummary }
  | { type: 'SET_JOB'; payload: JobStatus }
  | { type: 'REMOVE_JOB'; payload: string }
  | { type: 'SET_SCENE_INDEX'; payload: SceneIndex }
  | { type: 'SET_MEDIA_PROBE'; payload: MediaProbe }
  | { type: 'SET_SHOT_INDEX'; payload: ShotIndex }
  | { type: 'SET_PLAN'; payload: Plan }
  | { type: 'SET_MANIFEST'; payload: BlockManifest }
  | { type: 'SET_CRITIC_SUGGESTIONS'; payload: CriticSuggestions }
  | { type: 'SET_RENDER_SUMMARY'; payload: RenderSummary }
  | { type: 'SET_RENDER_QA'; payload: RenderQa }
  | { type: 'SET_MEDIA_TREE'; payload: MediaTree }
  | { type: 'SET_SELECTED_MEDIA'; payload: MediaNode | null }
  | { type: 'ADD_EVENT'; payload: EventLogEntry }
  | { type: 'SET_APPROVAL'; payload: { id: string; value: ApprovalValue } }
  | { type: 'SET_STAGE'; payload: { stage: PipelineStageKey; status: StageRunStatus } }
  | { type: 'SET_HIGHLIGHTED_BLOCK'; payload: string | null }
  | { type: 'SET_SELECTED_BLOCK'; payload: string | null }
  | { type: 'SET_MUSIC_LIBRARY'; payload: MusicTrackRef[] }
  | { type: 'CLEAR_REVIEW_ARTIFACTS' }
  | { type: 'SNAPSHOT_UNDO' }
  | { type: 'UNDO' }
  | { type: 'REDO' }
  | { type: 'RESET' }

export const initialState: PipelineState = {
  projectId: null,
  projectName: null,
  activeJobs: {},
  sceneIndex: null,
  mediaProbe: null,
  shotIndex: null,
  plan: null,
  manifest: null,
  criticSuggestions: null,
  renderSummary: null,
  renderQa: null,
  mediaTree: null,
  selectedMedia: null,
  eventLog: [],
  approvalState: {},
  pipelineStages: {
    'analyze-scenes': 'idle',
    'generate-plan': 'idle',
    'generate-tts': 'idle',
    'generate-assets': 'idle',
    'build-manifest': 'idle',
    render: 'idle',
    'review-render': 'idle',
    'apply-approved-patches': 'idle',
    'reorder-plan': 'idle',
    'delete-beat': 'idle',
    'edit-plan': 'idle',
    'create-beat': 'idle',
  },
  highlightedBlockId: null,
  selectedBlockId: null,
  musicLibrary: [],
  undoStack: [],
  redoStack: [],
}

export const PipelineContext = createContext<PipelineState>(initialState)
export const DispatchContext = createContext<Dispatch<PipelineAction>>(() => undefined)
export const VideoRefContext = createContext<React.RefObject<HTMLVideoElement | null>>({ current: null })

function pushUndo(state: PipelineState): Pick<PipelineState, 'undoStack' | 'redoStack'> {
  const snapshot: UndoSnapshot = { plan: state.plan, manifest: state.manifest }
  return {
    undoStack: [...state.undoStack.slice(-(MAX_UNDO - 1)), snapshot],
    redoStack: [],
  }
}

export function reducer(state: PipelineState, action: PipelineAction): PipelineState {
  switch (action.type) {
    case 'SET_PROJECT':
      return {
        ...initialState,
        projectId: action.payload.project_id,
        projectName: action.payload.display_name ?? action.payload.name ?? action.payload.project_id,
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
    case 'SET_MEDIA_PROBE':
      return { ...state, mediaProbe: action.payload }
    case 'SET_SHOT_INDEX':
      return { ...state, shotIndex: action.payload }
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
    case 'SET_RENDER_QA':
      return { ...state, renderQa: action.payload }
    case 'SET_MEDIA_TREE':
      return { ...state, mediaTree: action.payload }
    case 'SET_SELECTED_MEDIA':
      return { ...state, selectedMedia: action.payload }
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
    case 'SET_HIGHLIGHTED_BLOCK':
      return { ...state, highlightedBlockId: action.payload }
    case 'SET_SELECTED_BLOCK':
      return { ...state, selectedBlockId: action.payload }
    case 'SET_MUSIC_LIBRARY':
      return { ...state, musicLibrary: action.payload }
    case 'CLEAR_REVIEW_ARTIFACTS':
      return {
        ...state,
        criticSuggestions: null,
        renderQa: null,
        renderSummary: null,
        approvalState: {},
        pipelineStages: {
          ...state.pipelineStages,
          render: 'idle',
          'review-render': 'idle',
        },
      }
    case 'SNAPSHOT_UNDO':
      return { ...state, ...pushUndo(state) }
    case 'UNDO': {
      if (state.undoStack.length === 0) return state
      const prev = state.undoStack[state.undoStack.length - 1]
      const current: UndoSnapshot = { plan: state.plan, manifest: state.manifest }
      return {
        ...state,
        plan: prev.plan,
        manifest: prev.manifest,
        undoStack: state.undoStack.slice(0, -1),
        redoStack: [...state.redoStack, current],
        renderSummary: null,
        renderQa: null,
        criticSuggestions: null,
        approvalState: {},
        pipelineStages: {
          ...state.pipelineStages,
          render: 'idle',
          'review-render': 'idle',
        },
      }
    }
    case 'REDO': {
      if (state.redoStack.length === 0) return state
      const next = state.redoStack[state.redoStack.length - 1]
      const current: UndoSnapshot = { plan: state.plan, manifest: state.manifest }
      return {
        ...state,
        plan: next.plan,
        manifest: next.manifest,
        undoStack: [...state.undoStack, current],
        redoStack: state.redoStack.slice(0, -1),
        renderSummary: null,
        renderQa: null,
        criticSuggestions: null,
        approvalState: {},
        pipelineStages: {
          ...state.pipelineStages,
          render: 'idle',
          'review-render': 'idle',
        },
      }
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

export function useVideoRef() {
  return useContext(VideoRefContext)
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
  rendering: 'render',
  review_render: 'review-render',
  apply_patches: 'apply-approved-patches',
  reordering_plan: 'reorder-plan',
  deleting_plan_beat: 'delete-beat',
  editing_plan: 'edit-plan',
  creating_plan_beat: 'create-beat',
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

function optimisticManifestReorder(plan: Plan | null, manifest: BlockManifest | null, beatOrder: string[]): BlockManifest | null {
  if (!plan || !manifest || plan.beats.length !== manifest.blocks.length) return manifest
  const blockByBeatId = new Map(plan.beats.map((beat, index) => [beat.beat_id, manifest.blocks[index]]))
  const reorderedBlocks = beatOrder.map((beatId) => blockByBeatId.get(beatId)).filter(Boolean) as BlockManifest['blocks']
  if (reorderedBlocks.length !== manifest.blocks.length) return manifest
  return { ...manifest, blocks: reorderedBlocks }
}

function optimisticManifestDelete(plan: Plan | null, manifest: BlockManifest | null, beatId: string): BlockManifest | null {
  if (!plan || !manifest || plan.beats.length !== manifest.blocks.length) return manifest
  const index = plan.beats.findIndex((beat) => beat.beat_id === beatId)
  if (index < 0) return manifest
  return { ...manifest, blocks: manifest.blocks.filter((_, blockIndex) => blockIndex !== index) }
}

async function fetchArtifact(
  dispatch: Dispatch<PipelineAction>,
  stage: PipelineStageKey,
  projectId: string,
) {
  try {
    if (stage === 'analyze-scenes') {
      const [sceneIndex, mediaProbe, shotIndex] = await Promise.all([
        api.getSceneIndex(projectId),
        api.getMediaProbe(projectId).catch(() => null),
        api.getShotIndex(projectId).catch(() => null),
      ])
      dispatch({ type: 'SET_SCENE_INDEX', payload: sceneIndex })
      if (mediaProbe) {
        dispatch({ type: 'SET_MEDIA_PROBE', payload: mediaProbe })
      }
      if (shotIndex) {
        dispatch({ type: 'SET_SHOT_INDEX', payload: shotIndex })
      }
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Scene index: ${sceneIndex.scenes.length} scenes`) })
    } else if (stage === 'generate-plan') {
      const data = await api.getPlan(projectId)
      dispatch({ type: 'SET_PLAN', payload: data })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Plan: "${data.title}" - ${data.beats.length} beats`) })
    } else if (stage === 'build-manifest') {
      const data = await api.getManifest(projectId)
      dispatch({ type: 'SET_MANIFEST', payload: data })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Manifest: ${data.blocks.length} blocks`) })
    } else if (stage === 'render') {
      const data = await api.getRender(projectId)
      dispatch({ type: 'SET_RENDER_SUMMARY', payload: data })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Render: ${data.duration.toFixed(1)}s`) })
    } else if (stage === 'review-render') {
      const [critic, renderQa] = await Promise.all([
        api.getCriticSuggestions(projectId),
        api.getRenderQa(projectId).catch(() => null),
      ])
      dispatch({ type: 'SET_CRITIC_SUGGESTIONS', payload: critic })
      if (renderQa) {
        dispatch({ type: 'SET_RENDER_QA', payload: renderQa })
      }
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Review: ${critic.suggestions.length} suggestions`) })
    } else if (stage === 'apply-approved-patches') {
      dispatch({ type: 'CLEAR_REVIEW_ARTIFACTS' })
      const data = await api.getManifest(projectId)
      dispatch({ type: 'SET_MANIFEST', payload: data })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', 'Manifest updated') })
    } else if (stage === 'reorder-plan' || stage === 'delete-beat' || stage === 'edit-plan' || stage === 'create-beat') {
      const [plan, manifest, render] = await Promise.all([
        api.getPlan(projectId),
        api.getManifest(projectId),
        api.getRender(projectId),
      ])
      dispatch({ type: 'SET_PLAN', payload: plan })
      dispatch({ type: 'SET_MANIFEST', payload: manifest })
      dispatch({ type: 'SET_RENDER_SUMMARY', payload: render })
      dispatch({ type: 'CLEAR_REVIEW_ARTIFACTS' })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Plan updated: ${plan.beats.length} beats`) })
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
    // Missing artifacts are expected for new or partially run projects.
    return
  }
}

async function hydrateProject(dispatch: Dispatch<PipelineAction>, project: ProjectSummary) {
  const projectId = project.project_id
  const artifacts = project.artifacts ?? {}
  dispatch({ type: 'SET_PROJECT', payload: project })
  dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Project: ${project.display_name ?? project.name ?? projectId}`) })

  await loadIfAvailable(async () => {
    const data = await api.getProjectMedia(projectId)
    dispatch({ type: 'SET_MEDIA_TREE', payload: data })
  })
  if (artifacts.scene_index) {
    await loadIfAvailable(async () => {
      const data = await api.getSceneIndex(projectId)
      dispatch({ type: 'SET_SCENE_INDEX', payload: data })
      dispatch({ type: 'SET_STAGE', payload: { stage: 'analyze-scenes', status: 'succeeded' } })
    })
  }
  if (artifacts.media_probe) {
    await loadIfAvailable(async () => {
      const data = await api.getMediaProbe(projectId)
      dispatch({ type: 'SET_MEDIA_PROBE', payload: data })
    })
  }
  if (artifacts.shot_index) {
    await loadIfAvailable(async () => {
      const data = await api.getShotIndex(projectId)
      dispatch({ type: 'SET_SHOT_INDEX', payload: data })
    })
  }
  if (artifacts.plan) {
    await loadIfAvailable(async () => {
      const data = await api.getPlan(projectId)
      dispatch({ type: 'SET_PLAN', payload: data })
      dispatch({ type: 'SET_STAGE', payload: { stage: 'generate-plan', status: 'succeeded' } })
    })
  }
  if (artifacts.manifest) {
    await loadIfAvailable(async () => {
      const data = await api.getManifest(projectId)
      dispatch({ type: 'SET_MANIFEST', payload: data })
      dispatch({ type: 'SET_STAGE', payload: { stage: 'build-manifest', status: 'succeeded' } })
    })
  }
  if (artifacts.render) {
    await loadIfAvailable(async () => {
      const data = await api.getRender(projectId)
      dispatch({ type: 'SET_RENDER_SUMMARY', payload: data })
      dispatch({ type: 'SET_STAGE', payload: { stage: 'render', status: 'succeeded' } })
    })
  }
  if (artifacts.render_qa) {
    await loadIfAvailable(async () => {
      const data = await api.getRenderQa(projectId)
      dispatch({ type: 'SET_RENDER_QA', payload: data })
      dispatch({ type: 'SET_STAGE', payload: { stage: 'review-render', status: 'succeeded' } })
    })
  }
  if (artifacts.critic) {
    await loadIfAvailable(async () => {
      const data = await api.getCriticSuggestions(projectId)
      dispatch({ type: 'SET_CRITIC_SUGGESTIONS', payload: data })
      dispatch({ type: 'SET_STAGE', payload: { stage: 'review-render', status: 'succeeded' } })
    })
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

    const pollJob = async () => {
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

          // Auto-render preview after manifest is built OR patches applied
          if (frontendStage === 'build-manifest' || frontendStage === 'apply-approved-patches') {
            try {
              const { job_id: renderJobId } = await api.startJob('render', projectId)
              dispatch({ type: 'SET_JOB', payload: makeQueuedJob(renderJobId, projectId, 'render') })
              startPolling(renderJobId, 'render', projectId)
              dispatch({ type: 'ADD_EVENT', payload: makeEvent('info', 'Auto-rendering preview...') })
            } catch {
              // Render can still be triggered manually
            }
          } else if (frontendStage === 'render') {
            try {
              const { job_id: reviewJobId } = await api.startJob('review-render', projectId)
              dispatch({ type: 'SET_JOB', payload: makeQueuedJob(reviewJobId, projectId, 'review-render') })
              startPolling(reviewJobId, 'review-render', projectId)
              dispatch({ type: 'ADD_EVENT', payload: makeEvent('info', 'Reviewing final render...') })
            } catch {
              // Review can still be triggered manually
            }
          }
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
    }

    void pollJob()
    pollTimers.current[jobId] = setInterval(pollJob, 1000)
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
      await hydrateProject(dispatch, project)
    } catch (error) {
      dispatch({
        type: 'ADD_EVENT',
        payload: makeEvent('error', `Failed: ${error instanceof Error ? error.message : 'Unknown'}`),
      })
    }
  }, [dispatch])

  const createNewProject = useCallback(async (name = 'New Project') => {
    try {
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('info', `Creating ${name}...`) })
      const project = await api.createProject(name)
      await hydrateProject(dispatch, project)
      return project
    } catch (error) {
      dispatch({
        type: 'ADD_EVENT',
        payload: makeEvent('error', `Create project failed: ${error instanceof Error ? error.message : 'Unknown'}`),
      })
      throw error
    }
  }, [dispatch])

  const selectMedia = useCallback((media: MediaNode | null) => {
    dispatch({ type: 'SET_SELECTED_MEDIA', payload: media })
  }, [dispatch])

  const importMedia = useCallback(async (files: File[]) => {
    if (!state.projectId || files.length === 0) return

    try {
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('info', `Importing ${files.length} file${files.length === 1 ? '' : 's'}...`) })
      await api.importProjectMedia(state.projectId, files)
      const mediaTree = await api.getProjectMedia(state.projectId)
      dispatch({ type: 'SET_MEDIA_TREE', payload: mediaTree })
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('success', `Imported ${files.length} file${files.length === 1 ? '' : 's'}`) })
    } catch (error) {
      dispatch({
        type: 'ADD_EVENT',
        payload: makeEvent('error', `Import failed: ${error instanceof Error ? error.message : 'Unknown'}`),
      })
    }
  }, [dispatch, state.projectId])

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
      else if (value === 'rejected') rejected.push(id)
    }

    if (approved.length === 0 && rejected.length === 0) return

    if (approved.length === 0) {
      // Only rejections — just mark them dismissed, don't clear the whole panel
      for (const id of rejected) {
        dispatch({ type: 'SET_APPROVAL', payload: { id, value: 'dismissed' } })
      }
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('info', `Dismissed ${rejected.length} suggestion${rejected.length === 1 ? '' : 's'}`) })
      return
    }

    try {
      const { job_id } = await api.applyApprovedPatches({
        project_id: state.projectId,
        approved_suggestion_ids: approved,
        rejected_suggestion_ids: rejected,
      })
      // Dismiss the handled suggestions
      for (const id of approved) dispatch({ type: 'SET_APPROVAL', payload: { id, value: 'dismissed' } })
      for (const id of rejected) dispatch({ type: 'SET_APPROVAL', payload: { id, value: 'dismissed' } })
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

  const dismissSuggestion = useCallback((id: string) => {
    dispatch({ type: 'SET_APPROVAL', payload: { id, value: 'dismissed' } })
  }, [dispatch])

  const highlightBlock = useCallback((blockId: string | null) => {
    dispatch({ type: 'SET_HIGHLIGHTED_BLOCK', payload: blockId })
  }, [dispatch])

  const selectBlock = useCallback((blockId: string | null) => {
    dispatch({ type: 'SET_SELECTED_BLOCK', payload: blockId })
  }, [dispatch])

  const undo = useCallback(() => { dispatch({ type: 'UNDO' }) }, [dispatch])
  const redo = useCallback(() => { dispatch({ type: 'REDO' }) }, [dispatch])

  const reorderPlanBeats = useCallback(async (beatOrder: string[]) => {
    if (!state.projectId || !state.plan) return

    const reorderedBeats = beatOrder
      .map((beatId) => state.plan?.beats.find((beat) => beat.beat_id === beatId))
      .filter(Boolean) as Plan['beats']
    if (reorderedBeats.length === state.plan.beats.length) {
      dispatch({ type: 'SNAPSHOT_UNDO' })
      dispatch({ type: 'SET_PLAN', payload: { ...state.plan, beats: reorderedBeats } })
      const optimisticManifest = optimisticManifestReorder(state.plan, state.manifest, beatOrder)
      if (optimisticManifest) {
        dispatch({ type: 'SET_MANIFEST', payload: optimisticManifest })
      }
      dispatch({ type: 'CLEAR_REVIEW_ARTIFACTS' })
    }

    try {
      const { job_id } = await api.reorderPlanBeats(state.projectId, beatOrder)
      dispatch({ type: 'SET_JOB', payload: makeQueuedJob(job_id, state.projectId, 'reorder-plan') })
      startPolling(job_id, 'reorder-plan', state.projectId)
    } catch (error) {
      dispatch({
        type: 'ADD_EVENT',
        payload: makeEvent('error', `Reorder failed: ${error instanceof Error ? error.message : 'Unknown'}`),
      })
    }
  }, [dispatch, startPolling, state.manifest, state.plan, state.projectId])

  const deleteBeat = useCallback(async (beatId: string) => {
    if (!state.projectId || !state.plan) return

    dispatch({ type: 'SNAPSHOT_UNDO' })
    dispatch({ type: 'SET_PLAN', payload: { ...state.plan, beats: state.plan.beats.filter((beat) => beat.beat_id !== beatId) } })
    const optimisticManifest = optimisticManifestDelete(state.plan, state.manifest, beatId)
    if (optimisticManifest) {
      dispatch({ type: 'SET_MANIFEST', payload: optimisticManifest })
    }
    dispatch({ type: 'CLEAR_REVIEW_ARTIFACTS' })

    try {
      const { job_id } = await api.deletePlanBeat(state.projectId, beatId)
      dispatch({ type: 'SET_JOB', payload: makeQueuedJob(job_id, state.projectId, 'delete-beat') })
      startPolling(job_id, 'delete-beat', state.projectId)
    } catch (error) {
      dispatch({
        type: 'ADD_EVENT',
        payload: makeEvent('error', `Delete beat failed: ${error instanceof Error ? error.message : 'Unknown'}`),
      })
    }
  }, [dispatch, startPolling, state.manifest, state.plan, state.projectId])

  const editPlanPrompt = useCallback(async (prompt: string, history?: { role: 'user' | 'assistant'; content: string }[]) => {
    if (!state.projectId || !prompt.trim()) return
    dispatch({ type: 'CLEAR_REVIEW_ARTIFACTS' })
    try {
      const { job_id } = await api.editPlanWithPrompt(state.projectId, prompt.trim(), history)
      dispatch({ type: 'SET_JOB', payload: makeQueuedJob(job_id, state.projectId, 'edit-plan') })
      startPolling(job_id, 'edit-plan', state.projectId)
    } catch (error) {
      dispatch({
        type: 'ADD_EVENT',
        payload: makeEvent('error', `Plan edit failed: ${error instanceof Error ? error.message : 'Unknown'}`),
      })
    }
  }, [dispatch, startPolling, state.projectId])

  const createBeat = useCallback(async (payload: CreateBeatRequest) => {
    if (!state.projectId) return
    dispatch({ type: 'CLEAR_REVIEW_ARTIFACTS' })
    try {
      const { job_id } = await api.createPlanBeat(state.projectId, payload)
      dispatch({ type: 'SET_JOB', payload: makeQueuedJob(job_id, state.projectId, 'create-beat') })
      startPolling(job_id, 'create-beat', state.projectId)
    } catch (error) {
      dispatch({
        type: 'ADD_EVENT',
        payload: makeEvent('error', `Create beat failed: ${error instanceof Error ? error.message : 'Unknown'}`),
      })
      throw error
    }
  }, [dispatch, startPolling, state.projectId])

  const updateBeat = useCallback(async (beatId: string, updates: Record<string, unknown>) => {
    if (!state.projectId) return
    dispatch({ type: 'SNAPSHOT_UNDO' })
    try {
      const { job_id } = await api.updatePlanBeat(state.projectId, beatId, updates)
      dispatch({ type: 'SET_JOB', payload: makeQueuedJob(job_id, state.projectId, 'edit-plan') })
      startPolling(job_id, 'edit-plan', state.projectId)
    } catch (error) {
      dispatch({
        type: 'ADD_EVENT',
        payload: makeEvent('error', `Update beat failed: ${error instanceof Error ? error.message : 'Unknown'}`),
      })
    }
  }, [dispatch, startPolling, state.projectId])

  const loadProject = useCallback(async (projectId: string) => {
    try {
      dispatch({ type: 'ADD_EVENT', payload: makeEvent('info', `Loading project ${projectId}...`) })
      const projects = await api.listProjects().catch(() => [])
      const project = projects.find((entry) => entry.project_id === projectId) ?? {
        project_id: projectId,
        name: projectId,
        display_name: projectId.replace(/[-_]/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
        status: 'empty' as const,
        updated_at: new Date().toISOString(),
        artifacts: {},
      }
      await hydrateProject(dispatch, project)
    } catch (error) {
      dispatch({
        type: 'ADD_EVENT',
        payload: makeEvent('error', `Load failed: ${error instanceof Error ? error.message : 'Unknown'}`),
      })
    }
  }, [dispatch])

  return {
    openDemo,
    createNewProject,
    loadProject,
    runStage,
    submitApprovals,
    setApproval,
    dismissSuggestion,
    selectMedia,
    importMedia,
    highlightBlock,
    selectBlock,
    undo,
    redo,
    reorderPlanBeats,
    deleteBeat,
    editPlanPrompt,
    createBeat,
    updateBeat,
  }
}

export type { ApprovalValue, JobKind, PipelineJobKind, PipelineStageKey, StageRunStatus }

import type {
  ApplyPatchesRequest,
  BlockManifest,
  CriticSuggestions,
  JobStartResponse,
  JobStatus,
  PipelineJobKind,
  Plan,
  ProjectSummary,
  RenderSummary,
  SceneIndex,
} from '../types/api'

const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${text}`)
  }

  return res.json() as Promise<T>
}

export function openDemoProject(): Promise<ProjectSummary> {
  return request<ProjectSummary>('/projects/open-demo', { method: 'POST' })
}

export function startJob(kind: PipelineJobKind, projectId: string): Promise<JobStartResponse> {
  const query = new URLSearchParams({ project_id: projectId })
  return request<JobStartResponse>(`/jobs/${kind}?${query.toString()}`, {
    method: 'POST',
    body: undefined,
  })
}

export function getJob(jobId: string): Promise<JobStatus> {
  return request<JobStatus>(`/jobs/${jobId}`)
}

export function getSceneIndex(projectId: string): Promise<SceneIndex> {
  return request<SceneIndex>(`/projects/${projectId}/scene-index`)
}

export function getPlan(projectId: string): Promise<Plan> {
  return request<Plan>(`/projects/${projectId}/plan`)
}

export function getManifest(projectId: string): Promise<BlockManifest> {
  return request<BlockManifest>(`/projects/${projectId}/manifest`)
}

export function getCriticSuggestions(projectId: string): Promise<CriticSuggestions> {
  return request<CriticSuggestions>(`/projects/${projectId}/critic-suggestions`)
}

export function getRender(projectId: string): Promise<RenderSummary> {
  return request<RenderSummary>(`/projects/${projectId}/render`)
}

export function applyApprovedPatches(body: ApplyPatchesRequest): Promise<JobStartResponse> {
  return request<JobStartResponse>('/jobs/apply-approved-patches', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

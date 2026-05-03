import type {
  ApplyPatchesRequest,
  BlockManifest,
  CriticSuggestions,
  ImportMediaResponse,
  JobStartResponse,
  JobStatus,
  MediaProbe,
  MediaTree,
  PipelineJobKind,
  Plan,
  ProjectSummary,
  RenderQa,
  RenderSummary,
  SceneIndex,
  ShotIndex,
} from '../types/api'


const BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = init?.body instanceof FormData ? undefined : { 'Content-Type': 'application/json' }
  const res = await fetch(`${BASE}${path}`, {
    headers,
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

export function createProject(name: string): Promise<ProjectSummary> {
  return request<ProjectSummary>('/projects', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}

export function getProjectMedia(projectId: string): Promise<MediaTree> {
  return request<MediaTree>(`/projects/${projectId}/media`)
}

export function importProjectMedia(projectId: string, files: File[]): Promise<ImportMediaResponse> {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }
  return request<ImportMediaResponse>(`/projects/${projectId}/media/import`, {
    method: 'POST',
    body: formData,
  })
}

export function getProjectFileUrl(projectId: string, path: string): string {
  const query = new URLSearchParams({ path })
  return `${BASE}/projects/${projectId}/media/file?${query.toString()}`
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

export function getMediaProbe(projectId: string): Promise<MediaProbe> {
  return request<MediaProbe>(`/projects/${projectId}/media-probe`)
}

export function getShotIndex(projectId: string): Promise<ShotIndex> {
  return request<ShotIndex>(`/projects/${projectId}/shot-index`)
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

export function getRenderQa(projectId: string): Promise<RenderQa> {
  return request<RenderQa>(`/projects/${projectId}/render-qa`)
}

export function applyApprovedPatches(body: ApplyPatchesRequest): Promise<JobStartResponse> {
  return request<JobStartResponse>('/jobs/apply-approved-patches', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export async function listProjects(): Promise<ProjectSummary[]> {
  return request<ProjectSummary[]>('/projects')
}

export function updateProject(projectId: string, name: string, description: string, starred?: boolean): Promise<ProjectSummary> {
  return request<ProjectSummary>(`/projects/${projectId}`, {
    method: 'PUT',
    body: JSON.stringify({ name, description, starred }),
  })
}

export function deleteProject(projectId: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/projects/${projectId}`, {
    method: 'DELETE',
  })
}

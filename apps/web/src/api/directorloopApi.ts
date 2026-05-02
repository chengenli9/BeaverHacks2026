/* ──────────────────────────────────────────────
   DirectorLoop — API Client
   All calls target the FastAPI backend
   ────────────────────────────────────────────── */

import type {
  ProjectSummary,
  JobStartResponse,
  JobStatus,
  JobKind,
  SceneIndex,
  Plan,
  BlockManifest,
  CriticSuggestions,
  RenderSummary,
  ApplyPatchesRequest,
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

// ── Project ──────────────────────────────────

export function openDemoProject(): Promise<ProjectSummary> {
  return request<ProjectSummary>('/projects/open-demo', { method: 'POST' })
}

// ── Jobs ─────────────────────────────────────

export function startJob(kind: JobKind, body?: unknown): Promise<JobStartResponse> {
  return request<JobStartResponse>(`/jobs/${kind}`, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  })
}

export function getJob(jobId: string): Promise<JobStatus> {
  return request<JobStatus>(`/jobs/${jobId}`)
}

// ── Artifacts ────────────────────────────────

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

// ── Approval ─────────────────────────────────

export function applyApprovedPatches(body: ApplyPatchesRequest): Promise<JobStartResponse> {
  return request<JobStartResponse>('/jobs/apply-approved-patches', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

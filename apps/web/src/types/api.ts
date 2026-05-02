/* ──────────────────────────────────────────────
   DirectorLoop — Frontend API Types
   Mirrors docs/API_AND_DATA_CONTRACTS.md
   ────────────────────────────────────────────── */

// ── Job ──────────────────────────────────────

export type JobStatusValue = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'

export interface JobStatus {
  job_id: string
  project_id: string
  status: JobStatusValue
  stage: string | null
  progress: number
  message: string | null
  error: string | null
  created_at: string
  updated_at: string
}

export interface JobStartResponse {
  job_id: string
  status: 'queued'
}

export type JobKind =
  | 'analyze-scenes'
  | 'generate-plan'
  | 'generate-tts'
  | 'generate-assets'
  | 'build-manifest'
  | 'precritique'
  | 'apply-approved-patches'
  | 'render'

// ── Project ──────────────────────────────────

export interface ProjectSummary {
  project_id: string
  name: string
  source_path: string
}

// ── Scene Index ──────────────────────────────

export interface Scene {
  scene_id: string
  start: number
  end: number
  summary: string
  visual_tags: string[]
  audio_notes: string
  demo_relevance: number
}

export interface SceneIndex {
  project_id: string
  source: string
  source_duration: number
  scenes: Scene[]
}

// ── Plan ─────────────────────────────────────

export interface Beat {
  beat_id: string
  type: 'title' | 'source_clip' | 'end_card'
  goal: string
  scene_id: string | null
  duration: number
  narration: string | null
  onscreen_text: string | null
}

export interface Plan {
  project_id: string
  title: string
  target_duration: number
  story_arc: string[]
  beats: Beat[]
}

// ── Block Manifest ───────────────────────────

export interface RenderSettings {
  width: number
  height: number
  fps: number
  video_codec: string
  audio_codec: string
  sample_rate: number
  pixel_format: string
}

export interface TitleBlock {
  block_id: string
  type: 'title'
  background_asset: string
  text: string
  duration: number
  fontfile: string
  rendered_path: string
}

export interface SourceClipBlock {
  block_id: string
  type: 'source_clip'
  source: string
  source_start: number
  source_end: number
  video_duration: number
  tts_asset: string
  tts_duration: number
  source_audio_volume: number
  tts_fade_seconds: number
  rendered_path: string
}

export interface EndCardBlock {
  block_id: string
  type: 'end_card'
  background_asset: string
  text: string
  duration: number
  fontfile: string
  rendered_path: string
}

export type Block = TitleBlock | SourceClipBlock | EndCardBlock

export interface BlockManifest {
  project_id: string
  version: number
  render_settings: RenderSettings
  blocks: Block[]
}

// ── Critic Suggestions ──────────────────────

export type CriticAction =
  | 'trim_end'
  | 'extend_end'
  | 'reorder_after'
  | 'replace_text'
  | 'lower_source_audio'

export interface Suggestion {
  suggestion_id: string
  block_id: string
  action: CriticAction
  amount_seconds: number
  max_allowed_trim_seconds: number
  reason: string
  requires_approval: boolean
  replacement_text?: string
}

export interface CriticSuggestions {
  project_id: string
  critic_scope: string
  suggestions: Suggestion[]
}

// ── Apply Patches ────────────────────────────

export interface ApplyPatchesRequest {
  project_id: string
  approved_suggestion_ids: string[]
  rejected_suggestion_ids: string[]
}

// ── Render ───────────────────────────────────

export interface RenderSummary {
  project_id: string
  render_path: string
  url: string
  duration: number
  bytes: number
}

// ── Event Log ────────────────────────────────

export interface EventLogEntry {
  id: string
  timestamp: string
  type: 'info' | 'success' | 'error' | 'warning' | 'progress'
  message: string
  jobId?: string
  stage?: string
}

// DirectorLoop frontend API types. Mirrors docs/API_AND_DATA_CONTRACTS.md.

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

export type PipelineJobKind =
  | 'analyze-scenes'
  | 'generate-plan'
  | 'generate-tts'
  | 'generate-assets'
  | 'build-manifest'
  | 'render'
  | 'review-render'

export type PatchJobKind = 'apply-approved-patches'
export type JobKind = PipelineJobKind | PatchJobKind
export type PipelineStageKey = JobKind

export interface ProjectSummary extends ProjectListItem {
  source_path?: string
  artifacts?: Record<string, boolean>
}

export interface ProjectListItem {
  project_id: string
  name: string
  display_name?: string
  description?: string
  status: 'active' | 'in_progress' | 'empty'
  progress?: number
  updated_at: string
  thumbnail_type?: string
  starred?: boolean
}

export type MediaFileType = 'folder' | 'video' | 'image' | 'audio' | 'json' | 'file'

export interface MediaNode {
  name: string
  path: string
  type: MediaFileType
  children?: MediaNode[]
  size?: number
  duration?: number
}

export interface MediaTree {
  project_id: string
  files: MediaNode[]
}

export interface ImportMediaResponse {
  project_id: string
  files: MediaNode[]
}

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

export interface Beat {
  beat_id: string
  type: 'title' | 'source_clip' | 'end_card'
  goal: string
  scene_id: string | null
  duration: number
  narration: string | null
  onscreen_text: string | null
  style?: BeatStyle | null
}

export interface BeatStyle {
  font_family?: string | null
  font_variant?: string | null
  text_color?: string | null
  accent_color?: string | null
  background_mode?: 'image' | 'color' | 'gradient' | 'image_tint' | null
  background_color?: string | null
  text_alignment?: 'left' | 'center' | 'right' | null
  layout_preset?: 'centered' | 'hero-left' | 'hero-right' | 'stacked' | null
}

export interface Plan {
  project_id: string
  title: string
  target_duration: number
  story_arc: string[]
  beats: Beat[]
}

export interface RenderSettings {
  width: number
  height: number
  fps: number
  video_codec: string
  audio_codec: string
  sample_rate: number
  pixel_format: string
}

export interface MotionAssetRef {
  kind: 'remotion_scene'
  runtime_template: 'hero-reveal' | 'split-panel' | 'stacked-pulse'
  scene_spec_path: string
  decorator_module_path?: string | null
  preview_frame_path?: string | null
}

export interface TitleBlock {
  block_id: string
  type: 'title'
  background_asset?: string | null
  text: string
  duration: number
  fontfile: string
  font_family?: string | null
  font_variant?: string | null
  text_color?: string | null
  accent_color?: string | null
  background_mode?: 'image' | 'color' | 'gradient' | 'image_tint'
  background_color?: string | null
  text_alignment?: 'left' | 'center' | 'right'
  layout_preset?: 'centered' | 'hero-left' | 'hero-right' | 'stacked'
  motion_asset?: MotionAssetRef | null
  rendered_path: string
}

export interface SourceClipBlock {
  block_id: string
  type: 'source_clip'
  source: string
  source_start: number
  source_end: number
  video_duration: number
  tts_asset: string | null
  tts_duration: number | null
  source_audio_volume: number
  tts_fade_seconds: number
  motion_asset?: MotionAssetRef | null
  rendered_path: string
}

export interface EndCardBlock {
  block_id: string
  type: 'end_card'
  background_asset?: string | null
  text: string
  duration: number
  fontfile: string
  font_family?: string | null
  font_variant?: string | null
  text_color?: string | null
  accent_color?: string | null
  background_mode?: 'image' | 'color' | 'gradient' | 'image_tint'
  background_color?: string | null
  text_alignment?: 'left' | 'center' | 'right'
  layout_preset?: 'centered' | 'hero-left' | 'hero-right' | 'stacked'
  motion_asset?: MotionAssetRef | null
  rendered_path: string
}

export type Block = TitleBlock | SourceClipBlock | EndCardBlock

export interface BlockManifest {
  project_id: string
  version: number
  render_settings: RenderSettings
  blocks: Block[]
}

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
  target_block_id?: string | null
  source_audio_volume?: number | null
  category?: string | null
  severity?: 'low' | 'medium' | 'high' | null
  confidence?: number | null
  viewer_problem?: string | null
  evidence: string[]
  before_summary?: string | null
  after_summary?: string | null
}

export interface CriticSuggestions {
  project_id: string
  critic_scope: string
  suggestions: Suggestion[]
}

export interface VideoStreamInfo {
  codec: string
  width: number
  height: number
  fps: number
}

export interface AudioStreamInfo {
  codec: string
  sample_rate: number
  channels?: number | null
}

export interface MediaProbe {
  project_id: string
  source: string
  duration_seconds: number
  has_audio: boolean
  video_stream: VideoStreamInfo
  audio_stream?: AudioStreamInfo | null
}

export interface Shot {
  shot_id: string
  start: number
  end: number
  duration: number
  start_frame_path: string
  mid_frame_path: string
  end_frame_path: string
}

export interface ShotIndex {
  project_id: string
  source: string
  shots: Shot[]
}

export interface FrameCheck {
  frame_path: string
  timestamp_seconds: number
  average_brightness: number
  contrast: number
  is_near_black: boolean
  text_contrast_ratio?: number | null
}

export interface AudioCheck {
  check_type: 'silence' | 'loudness'
  details: string
  value?: number | null
}

export interface QaIssue {
  code: string
  severity: 'low' | 'medium' | 'high'
  message: string
  evidence: string[]
}

export interface RenderQaSummary {
  has_video: boolean
  has_audio: boolean
  duration_seconds: number
}

export interface RenderQa {
  project_id: string
  render_path: string
  summary: RenderQaSummary
  frame_checks: FrameCheck[]
  audio_checks: AudioCheck[]
  issues: QaIssue[]
}

export interface ApplyPatchesRequest {
  project_id: string
  approved_suggestion_ids: string[]
  rejected_suggestion_ids: string[]
}

export interface RenderSummary {
  project_id: string
  render_path: string
  url: string
  duration: number
  bytes: number
  cache_key?: string
}

export interface EventLogEntry {
  id: string
  timestamp: string
  type: 'info' | 'success' | 'error' | 'warning' | 'progress'
  message: string
  jobId?: string
  stage?: string
}

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'

vi.mock('../api/directorloopApi', () => ({
  createProject: vi.fn(),
  openDemoProject: vi.fn(),
  startJob: vi.fn(),
  getJob: vi.fn(),
  getProjectMedia: vi.fn(),
  getMediaProbe: vi.fn(),
  getShotIndex: vi.fn(),
  getRenderQa: vi.fn(),
  getProjectFileUrl: vi.fn((projectId: string, path: string) => `http://localhost:8000/projects/${projectId}/media/file?path=${encodeURIComponent(path)}`),
  importProjectMedia: vi.fn(),
  getSceneIndex: vi.fn(),
  getPlan: vi.fn(),
  getManifest: vi.fn(),
  getCriticSuggestions: vi.fn(),
  getRender: vi.fn(),
  applyApprovedPatches: vi.fn(),
  listProjects: vi.fn().mockResolvedValue([]),
}))

import * as api from '../api/directorloopApi'

const mockCritic = {
  project_id: 'demo_project',
  critic_scope: 'render_review',
  suggestions: [
    { suggestion_id: 's001', block_id: '001_title', action: 'trim_end' as const, amount_seconds: 1, max_allowed_trim_seconds: 2, reason: 'Tighten pacing.', requires_approval: true, category: 'pacing', severity: 'medium', confidence: 0.78, viewer_problem: 'The intro lingers after the hook lands.', evidence: ['render_qa: no technical issue', 'shot_index: repeated frames'], before_summary: '3.0s title', after_summary: '2.0s title' },
    { suggestion_id: 's002', block_id: '001_title', action: 'replace_text' as const, amount_seconds: 0, max_allowed_trim_seconds: 0.9, reason: 'Better text.', requires_approval: true, replacement_text: 'New Text', category: 'clarity', severity: 'low', confidence: 0.66, viewer_problem: 'The title undersells the product outcome.', evidence: ['manifest: generic title copy'], before_summary: 'DirectorLoop', after_summary: 'New Text' },
  ],
}

const mockRender = {
  project_id: 'demo_project',
  render_path: 'renders/final.mp4',
  url: 'http://localhost:8000/projects/demo_project/render/file',
  duration: 29.7,
  bytes: 1842042,
}

const mockSceneIndex = {
  project_id: 'demo_project',
  source: 'source/demo_footage.mp4',
  source_duration: 42,
  scenes: [
    {
      scene_id: 'scene_001',
      start: 0,
      end: 8,
      summary: 'Opening shot of the team explaining the project.',
      visual_tags: ['team', 'intro'],
      audio_notes: 'Clear speech',
      demo_relevance: 0.8,
    },
  ],
}

const mockPlan = {
  project_id: 'demo_project',
  title: 'DirectorLoop Demo Cut',
  target_duration: 30,
  story_arc: ['Name the problem', 'Show the pipeline'],
  beats: [
    {
      beat_id: 'beat_001',
      type: 'title' as const,
      goal: 'Brand the demo instantly',
      scene_id: null,
      duration: 3,
      narration: null,
      onscreen_text: 'DirectorLoop',
    },
  ],
}

const mockManifest = {
  project_id: 'demo_project',
  version: 1,
  render_settings: {
    width: 1920,
    height: 1080,
    fps: 30,
    video_codec: 'libx264',
    audio_codec: 'aac',
    sample_rate: 48000,
    pixel_format: 'yuv420p',
  },
  blocks: [
    {
      block_id: '001_title',
      type: 'title' as const,
      background_asset: 'assets/backgrounds/bg_001.png',
      text: 'DirectorLoop',
      duration: 3,
      fontfile: 'assets/fonts/Inter-Bold.ttf',
      rendered_path: 'blocks/001_title.mp4',
    },
    {
      block_id: '002_clip_without_tts',
      type: 'source_clip' as const,
      source: 'source/demo_footage.mp4',
      source_start: 0,
      source_end: 4,
      video_duration: 4,
      tts_asset: null,
      tts_duration: null,
      source_audio_volume: 0.15,
      tts_fade_seconds: 0.5,
      rendered_path: 'blocks/002_clip_without_tts.mp4',
    },
  ],
}

const mockMedia = {
  project_id: 'demo_project',
  files: [
    {
      name: 'source',
      path: 'source',
      type: 'folder' as const,
      children: [
        {
          name: 'demo_footage.mp4',
          path: 'source/demo_footage.mp4',
          type: 'video' as const,
          size: 1024,
          duration: 42,
        },
      ],
    },
  ],
}

const mockMediaProbe = {
  project_id: 'demo_project',
  source: 'source/demo_footage.mp4',
  duration_seconds: 42,
  has_audio: true,
  video_stream: { codec: 'h264', width: 1920, height: 1080, fps: 30 },
  audio_stream: { codec: 'aac', sample_rate: 48000 },
}

const mockRenderQa = {
  project_id: 'demo_project',
  render_path: 'renders/final.mp4',
  summary: { has_video: true, has_audio: true, duration_seconds: 29.7 },
  frame_checks: [],
  audio_checks: [],
  issues: [],
}

function mockApi() {
  const m = api as unknown as Record<string, ReturnType<typeof vi.fn>>
  return m
}

beforeEach(() => {
  vi.useRealTimers()
  vi.resetAllMocks()
  // Default: render the dashboard (not the home page) for existing tests
  window.location.hash = '#/project/demo_project'
  // Re-mock listProjects after resetAllMocks
  const m = mockApi()
  m.listProjects.mockResolvedValue([])
  m.getMediaProbe.mockRejectedValue(new Error('no'))
  m.getShotIndex.mockRejectedValue(new Error('no'))
  m.getRenderQa.mockRejectedValue(new Error('no'))
})

afterEach(() => {
  vi.useRealTimers()
  window.location.hash = ''
})

describe('Dashboard', () => {
  it('renders empty state with Open Demo Project button', () => {
    window.location.hash = '#/project'
    render(<App />)
    expect(screen.getByText('DirectorLoop')).toBeInTheDocument()
    expect(screen.getByText('Open Demo Project')).toBeInTheDocument()
    expect(screen.getByText('No Events')).toBeInTheDocument()
    expect(screen.getByText('No Project')).toBeInTheDocument()
  })

  it('opens demo project and populates artifact panels', async () => {
    const user = userEvent.setup()
    const m = mockApi()
    m.openDemoProject.mockResolvedValue({ project_id: 'demo_project', name: 'Demo Project', source_path: 'source/' })
    m.getProjectMedia.mockResolvedValue(mockMedia)
    m.getSceneIndex.mockResolvedValue(mockSceneIndex)
    m.getPlan.mockResolvedValue(mockPlan)
    m.getManifest.mockResolvedValue(mockManifest)
    m.getCriticSuggestions.mockRejectedValue(new Error('no'))
    m.getRender.mockRejectedValue(new Error('no'))

    render(<App />)
    await user.click(screen.getByText('Open Demo Project'))
    expect(await screen.findByText('Demo Project')).toBeInTheDocument()

    await user.click(await screen.findByRole('button', { name: /Scenes/i }))
    expect(screen.getByText('Opening shot of the team explaining the project.')).toBeInTheDocument()

    const centerPanel = document.querySelector('#center-panel') as HTMLElement
    await user.click(within(centerPanel).getByRole('button', { name: /Plan/i }))
    expect(screen.getByText('DirectorLoop Demo Cut')).toBeInTheDocument()

    await user.click(within(centerPanel).getByRole('button', { name: /Manifest/i }))
    expect(screen.getByText('Block Manifest v1')).toBeInTheDocument()
    expect(within(centerPanel).getAllByText('001_title').length).toBeGreaterThan(0)
  })

  it('polls a running job and updates progress', async () => {
    const user = userEvent.setup()
    const m = mockApi()
    m.openDemoProject.mockResolvedValue({ project_id: 'demo_project', name: 'Demo', source_path: '' })
    m.getProjectMedia.mockResolvedValue(mockMedia)
    m.getSceneIndex.mockRejectedValue(new Error('no'))
    m.getPlan.mockRejectedValue(new Error('no'))
    m.getManifest.mockRejectedValue(new Error('no'))
    m.getCriticSuggestions.mockRejectedValue(new Error('no'))
    m.getRender.mockRejectedValue(new Error('no'))
    m.startJob.mockResolvedValue({ job_id: 'job_analyze_1', status: 'queued' })
    m.getJob.mockResolvedValue({
      job_id: 'job_analyze_1',
      project_id: 'demo_project',
      status: 'running',
      stage: 'analyzing_scenes',
      progress: 0.42,
      message: 'Analyzing scene 2 of 5',
      error: null,
      created_at: '2026-05-02T20:00:00Z',
      updated_at: '2026-05-02T20:00:01Z',
    })

    render(<App />)
    await user.click(screen.getByText('Open Demo Project'))
    await screen.findByText('Demo')
    await user.click(screen.getByRole('button', { name: /Analyze/i }))

    expect(screen.getByRole('button', { name: /Analyze/i })).toHaveClass('running')
  }, 7000)

  it('renders failed job retry state', async () => {
    const user = userEvent.setup()
    const m = mockApi()
    m.openDemoProject.mockResolvedValue({ project_id: 'demo_project', name: 'Demo', source_path: '' })
    m.getSceneIndex.mockRejectedValue(new Error('no'))
    m.getPlan.mockRejectedValue(new Error('no'))
    m.getManifest.mockRejectedValue(new Error('no'))
    m.getCriticSuggestions.mockRejectedValue(new Error('no'))
    m.getRender.mockRejectedValue(new Error('no'))
    m.startJob.mockResolvedValue({ job_id: 'job_analyze_2', status: 'queued' })
    m.getJob.mockResolvedValue({
      job_id: 'job_analyze_2',
      project_id: 'demo_project',
      status: 'failed',
      stage: 'analyzing_scenes',
      progress: 0.18,
      message: null,
      error: 'Scene analyzer crashed',
      created_at: '2026-05-02T20:00:00Z',
      updated_at: '2026-05-02T20:00:01Z',
    })

    render(<App />)
    await user.click(screen.getByText('Open Demo Project'))
    await screen.findByText('Demo')
    await user.click(screen.getByRole('button', { name: /Analyze/i }))

    expect(await screen.findByText(/Scene analyzer crashed/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Retry Analyze/i })).toBeEnabled()
  }, 7000)

  it('renders critic suggestions with approve/reject controls', async () => {
    const user = userEvent.setup()
    const m = mockApi()
    m.openDemoProject.mockResolvedValue({ project_id: 'demo_project', name: 'Demo', source_path: '' })
    m.getMediaProbe.mockResolvedValue(mockMediaProbe)
    m.getRenderQa.mockResolvedValue(mockRenderQa)
    m.getSceneIndex.mockRejectedValue(new Error('no'))
    m.getPlan.mockRejectedValue(new Error('no'))
    m.getManifest.mockRejectedValue(new Error('no'))
    m.getCriticSuggestions.mockResolvedValue(mockCritic)
    m.getRender.mockRejectedValue(new Error('no'))

    render(<App />)
    await user.click(screen.getByText('Open Demo Project'))
    // Wait for project to load, then switch to Output tab
    await screen.findByText('Demo')
    await user.click(screen.getByText('Output'))
    expect(await screen.findByText('Tighten pacing.')).toBeInTheDocument()

    const approveButtons = screen.getAllByText('Approve')
    const rejectButtons = screen.getAllByText('Reject')
    expect(approveButtons.length).toBe(2)
    expect(rejectButtons.length).toBe(2)
    expect(screen.getByText('The intro lingers after the hook lands.')).toBeInTheDocument()
    expect(screen.getByText(/repeated frames/i)).toBeInTheDocument()
  })

  it('submits approved and rejected critic suggestion ids', async () => {
    const user = userEvent.setup()
    const m = mockApi()
    m.openDemoProject.mockResolvedValue({ project_id: 'demo_project', name: 'Demo', source_path: '' })
    m.getSceneIndex.mockRejectedValue(new Error('no'))
    m.getPlan.mockRejectedValue(new Error('no'))
    m.getManifest.mockRejectedValue(new Error('no'))
    m.getCriticSuggestions.mockResolvedValue(mockCritic)
    m.getRender.mockRejectedValue(new Error('no'))
    m.applyApprovedPatches.mockResolvedValue({ job_id: 'job_apply_1', status: 'queued' })

    render(<App />)
    await user.click(screen.getByText('Open Demo Project'))
    await screen.findByText('Demo')
    await user.click(screen.getByText('Output'))
    await user.click(await screen.findByRole('button', { name: /Approve s001/i }))
    await user.click(screen.getByRole('button', { name: /Reject s002/i }))
    await user.click(screen.getByRole('button', { name: /Apply Changes/i }))

    expect(m.applyApprovedPatches).toHaveBeenCalledWith({
      project_id: 'demo_project',
      approved_suggestion_ids: ['s001'],
      rejected_suggestion_ids: ['s002'],
    })
  })

  it('renders render preview when render summary exists', async () => {
    const user = userEvent.setup()
    const m = mockApi()
    m.openDemoProject.mockResolvedValue({ project_id: 'demo_project', name: 'Demo', source_path: '' })
    m.getSceneIndex.mockRejectedValue(new Error('no'))
    m.getPlan.mockRejectedValue(new Error('no'))
    m.getManifest.mockRejectedValue(new Error('no'))
    m.getCriticSuggestions.mockRejectedValue(new Error('no'))
    m.getRender.mockResolvedValue(mockRender)

    render(<App />)
    await user.click(screen.getByText('Open Demo Project'))
    // Render preview shows in the center player area
    expect(await screen.findByText('29.7s')).toBeInTheDocument()
  })

  it('shows failed state event in log on API error', async () => {
    const m = mockApi()
    m.openDemoProject.mockRejectedValue(new Error('Connection refused'))
    // The hash route triggers auto-load, which calls openDemo and fails
    render(<App />)
    expect(await screen.findByText(/Connection refused/)).toBeInTheDocument()
  })

  it('creates and loads a new empty project', async () => {
    const user = userEvent.setup()
    const m = mockApi()
    m.createProject.mockResolvedValue({ project_id: 'new-project', display_name: 'New Project', artifacts: {} })
    m.getProjectMedia.mockResolvedValue({ project_id: 'new-project', files: [] })
    m.getSceneIndex.mockRejectedValue(new Error('no'))
    m.getPlan.mockRejectedValue(new Error('no'))
    m.getManifest.mockRejectedValue(new Error('no'))
    m.getCriticSuggestions.mockRejectedValue(new Error('no'))
    m.getRender.mockRejectedValue(new Error('no'))

    render(<App />)
    await user.click(screen.getByText('New Project'))

    expect(await screen.findByText('New Project')).toBeInTheDocument()
    expect(m.createProject).toHaveBeenCalledWith('New Project')
  })

  it('renders backend media files and previews a selected video', async () => {
    const user = userEvent.setup()
    const m = mockApi()
    m.openDemoProject.mockResolvedValue({ project_id: 'demo_project', name: 'Demo', source_path: '' })
    m.getProjectMedia.mockResolvedValue(mockMedia)
    m.getSceneIndex.mockRejectedValue(new Error('no'))
    m.getPlan.mockRejectedValue(new Error('no'))
    m.getManifest.mockRejectedValue(new Error('no'))
    m.getCriticSuggestions.mockRejectedValue(new Error('no'))
    m.getRender.mockRejectedValue(new Error('no'))

    render(<App />)
    await user.click(screen.getByText('Open Demo Project'))
    await user.click(await screen.findByText('demo_footage.mp4'))

    const video = document.querySelector('#selected-video') as HTMLVideoElement
    expect(video).toBeInTheDocument()
    expect(video.src).toContain('/projects/demo_project/media/file')

    await user.click(screen.getByRole('button', { name: /Timeline Preview/i }))
    expect(document.querySelector('#selected-video')).not.toBeInTheDocument()
  })

  it('imports selected media and refreshes the media tree', async () => {
    const user = userEvent.setup()
    const m = mockApi()
    const file = new File(['fake'], 'dropped.mp4', { type: 'video/mp4' })
    m.openDemoProject.mockResolvedValue({ project_id: 'demo_project', name: 'Demo', source_path: '' })
    m.getProjectMedia
      .mockResolvedValueOnce({ project_id: 'demo_project', files: [] })
      .mockResolvedValueOnce({
        project_id: 'demo_project',
        files: [{ name: 'dropped.mp4', path: 'source/dropped.mp4', type: 'video', size: 4 }],
      })
    m.importProjectMedia.mockResolvedValue({
      project_id: 'demo_project',
      files: [{ name: 'dropped.mp4', path: 'source/dropped.mp4', type: 'video', size: 4 }],
    })
    m.getSceneIndex.mockRejectedValue(new Error('no'))
    m.getPlan.mockRejectedValue(new Error('no'))
    m.getManifest.mockRejectedValue(new Error('no'))
    m.getCriticSuggestions.mockRejectedValue(new Error('no'))
    m.getRender.mockRejectedValue(new Error('no'))

    render(<App />)
    await user.click(screen.getByText('Open Demo Project'))
    await screen.findByText('Demo')
    await user.click(screen.getByText('Import'))
    await user.upload(screen.getByLabelText('Add media files'), file)

    expect(m.importProjectMedia).toHaveBeenCalledWith('demo_project', [file])
    expect(await screen.findByText('Imported 1 file')).toBeInTheDocument()
  })

  it('renders the timeline inside the center panel', async () => {
    const user = userEvent.setup()
    const m = mockApi()
    m.openDemoProject.mockResolvedValue({ project_id: 'demo_project', name: 'Demo', source_path: '' })
    m.getProjectMedia.mockResolvedValue(mockMedia)
    m.getSceneIndex.mockRejectedValue(new Error('no'))
    m.getPlan.mockRejectedValue(new Error('no'))
    m.getManifest.mockResolvedValue(mockManifest)
    m.getCriticSuggestions.mockRejectedValue(new Error('no'))
    m.getRender.mockRejectedValue(new Error('no'))

    render(<App />)
    await user.click(screen.getByText('Open Demo Project'))

    const centerPanel = document.querySelector('#center-panel') as HTMLElement
    const timeline = await within(centerPanel).findByTestId('timeline')
    expect(timeline).toBeInTheDocument()
    expect(document.querySelector('.main-area > #timeline')).not.toBeInTheDocument()

    await user.click(within(centerPanel).getByRole('button', { name: /Manifest/i }))
    expect(within(centerPanel).getByTestId('timeline')).toBeInTheDocument()
  })

  it('renders the review stage after render', async () => {
    const user = userEvent.setup()
    const m = mockApi()
    m.openDemoProject.mockResolvedValue({ project_id: 'demo_project', name: 'Demo', source_path: '' })
    m.getProjectMedia.mockResolvedValue(mockMedia)
    m.getSceneIndex.mockRejectedValue(new Error('no'))
    m.getPlan.mockRejectedValue(new Error('no'))
    m.getManifest.mockRejectedValue(new Error('no'))
    m.getCriticSuggestions.mockRejectedValue(new Error('no'))
    m.getRender.mockRejectedValue(new Error('no'))

    render(<App />)
    await user.click(screen.getByText('Open Demo Project'))
    await screen.findByText('Demo')

    expect(screen.getByRole('button', { name: /^Review$/i })).toBeInTheDocument()
  })
})

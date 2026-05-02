import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'

vi.mock('../api/directorloopApi', () => ({
  openDemoProject: vi.fn(),
  startJob: vi.fn(),
  getJob: vi.fn(),
  getSceneIndex: vi.fn(),
  getPlan: vi.fn(),
  getManifest: vi.fn(),
  getCriticSuggestions: vi.fn(),
  getRender: vi.fn(),
  applyApprovedPatches: vi.fn(),
}))

import * as api from '../api/directorloopApi'

const mockCritic = {
  project_id: 'demo_project',
  critic_scope: 'blind_manifest_only',
  suggestions: [
    { suggestion_id: 's001', block_id: '001_title', action: 'trim_end' as const, amount_seconds: 1, max_allowed_trim_seconds: 2, reason: 'Tighten pacing.', requires_approval: true },
    { suggestion_id: 's002', block_id: '001_title', action: 'replace_text' as const, amount_seconds: 0, max_allowed_trim_seconds: 0.9, reason: 'Better text.', requires_approval: true, replacement_text: 'New Text' },
  ],
}

const mockRender = {
  project_id: 'demo_project',
  render_path: 'renders/final.mp4',
  url: 'http://localhost:8000/projects/demo_project/render/file',
  duration: 29.7,
  bytes: 1842042,
}

function mockApi() {
  const m = api as unknown as Record<string, ReturnType<typeof vi.fn>>
  return m
}

beforeEach(() => { vi.resetAllMocks() })

describe('Dashboard', () => {
  it('renders empty state with Open Demo Project button', () => {
    render(<App />)
    expect(screen.getByText('DirectorLoop')).toBeInTheDocument()
    expect(screen.getByText('Open Demo Project')).toBeInTheDocument()
    expect(screen.getByText('No Events')).toBeInTheDocument()
    expect(screen.getByText('No Project')).toBeInTheDocument()
  })

  it('opens demo project and populates panels', async () => {
    const user = userEvent.setup()
    const m = mockApi()
    m.openDemoProject.mockResolvedValue({ project_id: 'demo_project', name: 'Demo Project', source_path: 'source/' })
    m.getSceneIndex.mockRejectedValue(new Error('no'))
    m.getPlan.mockRejectedValue(new Error('no'))
    m.getManifest.mockRejectedValue(new Error('no'))
    m.getCriticSuggestions.mockRejectedValue(new Error('no'))
    m.getRender.mockRejectedValue(new Error('no'))

    render(<App />)
    await user.click(screen.getByText('Open Demo Project'))
    expect(await screen.findByText('Demo Project')).toBeInTheDocument()
  })

  it('renders critic suggestions with approve/reject controls', async () => {
    const user = userEvent.setup()
    const m = mockApi()
    m.openDemoProject.mockResolvedValue({ project_id: 'demo_project', name: 'Demo', source_path: '' })
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
    const user = userEvent.setup()
    const m = mockApi()
    m.openDemoProject.mockRejectedValue(new Error('Connection refused'))

    render(<App />)
    await user.click(screen.getByText('Open Demo Project'))
    expect(await screen.findByText(/Connection refused/)).toBeInTheDocument()
  })
})

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  applyApprovedPatches,
  createProject,
  getProjectFileUrl,
  getProjectMedia,
  importProjectMedia,
  startJob,
} from '../api/scenerioApi'

const okResponse = {
  ok: true,
  json: () => Promise.resolve({ job_id: 'job_001', status: 'queued' }),
} as Response

describe('scenerioApi', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(okResponse))
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('starts pipeline jobs with project_id as a query parameter', async () => {
    await startJob('analyze-scenes', 'demo_project')

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/jobs/analyze-scenes?project_id=demo_project',
      expect.objectContaining({
        method: 'POST',
        body: undefined,
      }),
    )
  })

  it('submits approved patches with the documented JSON body', async () => {
    await applyApprovedPatches({
      project_id: 'demo_project',
      approved_suggestion_ids: ['s001'],
      rejected_suggestion_ids: ['s002'],
    })

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/jobs/apply-approved-patches',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          project_id: 'demo_project',
          approved_suggestion_ids: ['s001'],
          rejected_suggestion_ids: ['s002'],
        }),
      }),
    )
  })

  it('creates projects with the documented JSON body', async () => {
    await createProject('My Project')

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/projects',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'My Project' }),
      }),
    )
  })

  it('loads project media and builds file URLs', async () => {
    await getProjectMedia('demo_project')

    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/projects/demo_project/media',
      expect.any(Object),
    )
    expect(getProjectFileUrl('demo_project', 'source/demo footage.mp4')).toBe(
      'http://localhost:8000/projects/demo_project/media/file?path=source%2Fdemo+footage.mp4',
    )
  })

  it('imports project media with multipart form data', async () => {
    const file = new File(['fake'], 'clip.mp4', { type: 'video/mp4' })

    await importProjectMedia('demo_project', [file])

    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect(fetch).toHaveBeenCalledWith(
      'http://localhost:8000/projects/demo_project/media/import',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(init?.body).toBeInstanceOf(FormData)
  })
})

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { applyApprovedPatches, startJob } from '../api/directorloopApi'

const okResponse = {
  ok: true,
  json: () => Promise.resolve({ job_id: 'job_001', status: 'queued' }),
} as Response

describe('directorloopApi', () => {
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
})

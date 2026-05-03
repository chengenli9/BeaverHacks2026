# Scenerio Implementation Plan

> For agentic workers: follow the owner boundaries in `docs/DEVELOPER_WORK_SPLIT.md` and your assigned handoff file. Do not edit another developer's owned folders without a short written handoff.

## Goal

Build a polished local hackathon demo of Scenerio: load a demo project, run async pipeline jobs, show structured artifacts, approve blind critic suggestions, render normalized FFmpeg blocks, and play the final MP4.

## Architecture

The backend owns validation, jobs, file access, manifests, and rendering. Gemini owns structured scene/plan/critic generation plus TTS/background assets, but only through isolated integration services. The frontend shows the pipeline dashboard and never implements media or AI logic.

## Milestones

### Milestone 0: Repo Foundation

Status: created by this documentation pass.

Deliverables:

- Architecture and implementation docs.
- Four dev handoff files.
- Sample project fixtures.
- Folder scaffolding for frontend, backend, assets, samples, and tests.

Acceptance:

- A new dev can pick one handoff file and know exactly which folders to touch.
- Frontend and backend can work against sample JSON before Gemini exists.

### Milestone 1: Static Demo Project and Contracts

Owner: Dev 3 with read-only support from all devs.

Files:

```text
backend/app/manifests/
tests/backend/manifests/
samples/demo_project/cache/scene_index.json
samples/demo_project/manifests/plan.json
samples/demo_project/manifests/block_manifest.json
samples/demo_project/manifests/critic_suggestions.json
```

Tasks:

- Define Pydantic models for `SceneIndex`, `Plan`, `BlockManifest`, `CriticSuggestions`, and `JobStatus`.
- Load sample fixture JSON and validate it in tests.
- Implement duration reconciliation.
- Implement critic patch validation rules.

Required tests:

```bash
pytest tests/backend/manifests -q
```

Acceptance:

- Invalid manifests fail before render.
- TTS longer than video expands `source_end`.
- Critic suggestions over 30 percent trim fail validation.

### Milestone 2: Backend Job API

Owner: Dev 2.

Files:

```text
backend/app/main.py
backend/app/api/
backend/app/jobs/
backend/app/projects/
tests/backend/jobs/
tests/backend/api/
```

Tasks:

- Create FastAPI app.
- Add CORS for local frontend.
- Implement in-memory `JobStore`.
- Implement `POST /projects/open-demo`.
- Implement all `POST /jobs/*` endpoints with fake service calls first.
- Implement all artifact `GET /projects/{project_id}/*` endpoints.
- Replace fake calls with service imports as Dev 3 and Dev 4 land their modules.

Required tests:

```bash
pytest tests/backend/jobs tests/backend/api -q
```

Acceptance:

- Every expensive endpoint returns a job id immediately.
- Job state progresses from `queued` to `running` to `succeeded` or `failed`.
- Failed jobs preserve actionable error text.
- Sample project JSON is served through the API.

### Milestone 3: Deterministic Renderer

Owner: Dev 3.

Files:

```text
backend/app/rendering/
backend/app/manifests/
tests/backend/rendering/
```

Tasks:

- Implement FFmpeg availability check.
- Implement one renderer per block type: title, source_clip, end_card.
- Normalize every block to the same codec, resolution, frame rate, sample rate, and pixel format.
- Write concat demuxer list.
- Run final concat.
- Run ffprobe smoke check on the final MP4.

Required tests:

```bash
pytest tests/backend/rendering -q
```

Acceptance:

- Renderer never builds one giant filtergraph.
- Missing font fails before FFmpeg starts.
- `blocks/*.mp4` are created before `renders/final_render.mp4`.
- Final render has nonzero duration and playable streams.

### Milestone 4: Gemini Integrations

Owner: Dev 4.

Files:

```text
backend/app/integrations/gemini/
backend/app/prompts/
backend/app/assets/
tests/backend/integrations/
tests/backend/prompts/
```

Tasks:

- Implement Gemini client wrapper with model names from environment variables.
- Default text model to `gemini-2.5-flash-lite`.
- Default TTS model to `gemini-2.5-flash-preview-tts`.
- Default image model to `gemini-2.5-flash-image`.
- Use structured outputs for scene index, plan, and critic responses.
- Generate TTS WAV files and measure durations with ffprobe through Dev 3's utility.
- Generate textless PNG background plates.
- Log sanitized Gemini call metadata to `logs/gemini_calls.jsonl`.

Required tests:

```bash
pytest tests/backend/integrations tests/backend/prompts -q
```

Acceptance:

- Tests mock Gemini responses and do not call the network.
- No Pro model is used by default.
- Critic prompt states it is blind and forbids visual-quality critique.
- Image prompts include "No text, no letters, no logos."

### Milestone 5: Frontend Pipeline Dashboard

Owner: Dev 1.

Files:

```text
apps/web/
tests/frontend/
```

Tasks:

- Create React + TypeScript app.
- Build a three-panel pipeline dashboard.
- Add project open action.
- Add job action buttons.
- Poll job status.
- Show scene, plan, manifest, critic, and render artifacts.
- Add approve/reject critic cards.
- Add final video preview.

Required tests:

```bash
npm --prefix apps/web test
```

Acceptance:

- UI works against mocked API responses before backend is complete.
- UI works against local FastAPI after backend is complete.
- Long text wraps inside cards and buttons.
- Failed jobs are visible and retryable.

### Milestone 6: Approval Loop

Owners:

- Dev 1 owns UI controls.
- Dev 2 owns API endpoint.
- Dev 3 owns patch validation and manifest write.

Shared contract:

```json
{
  "project_id": "demo_project",
  "approved_suggestion_ids": ["s001"],
  "rejected_suggestion_ids": ["s002"]
}
```

Rules:

- Dev 1 may only send ids.
- Dev 2 may only orchestrate the request.
- Dev 3 applies and validates patches.

Acceptance:

- Rejected suggestions do not alter the manifest.
- Approved suggestions cannot violate duration rules.
- UI refreshes manifest after patch application.

### Milestone 7: Demo Polish

Owners: all, but each dev stays in their lane.

Tasks:

- Verify one-click sample project path.
- Add useful empty and failure states.
- Add run commands to README once code exists.
- Record a known-good demo sequence.
- Freeze model defaults.
- Avoid last-minute scope expansion.

Acceptance:

- The app can be demoed from a clean checkout.
- The final MP4 renders locally.
- The UI looks complete even if a live Gemini endpoint is temporarily unavailable.

## Branch Plan

Use one branch per dev:

```text
dev/frontend-pipeline-ui
dev/backend-job-api
dev/manifest-renderer
dev/gemini-assets-critic
```

Merge order for lowest friction:

```text
1. manifest-renderer contracts
2. backend-job-api
3. gemini-assets-critic
4. frontend-pipeline-ui
5. approval-loop integration branch
```

## Demo-First Definition of Done

A task is done when:

- It has a working local path.
- The relevant unit tests pass.
- The UI or API exposes visible behavior.
- It writes or reads the documented artifact path.
- It does not require another developer to edit their owned folder to unblock it.

## Explicit Cuts

Do not build in the MVP:

- Redis or Celery.
- Login/accounts.
- Cloud storage.
- A full NLE timeline.
- Post-render video critique in the live path.
- Dynamic audio ducking curves.
- Multi-variant generation.
- DaVinci export.
- Pro model fallbacks by default.


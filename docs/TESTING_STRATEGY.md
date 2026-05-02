# Testing Strategy

## Goal

Protect the demo path without burying the team in slow tests. Unit test deterministic logic, mock external Gemini calls, and smoke-test FFmpeg only where it proves the render path works.

## Test Pyramid

```text
Many unit tests
Some API/component tests
Few local integration smoke tests
No live Gemini tests in default CI
```

## Backend Unit Tests

### Job store

Owner: Dev 2.

```text
tests/backend/jobs/test_job_store.py
```

Required coverage:

- Creates queued job.
- Updates progress while running.
- Marks succeeded.
- Marks failed with error.
- Rejects unknown job id.

### Project API

Owner: Dev 2.

```text
tests/backend/api/test_projects.py
tests/backend/api/test_jobs.py
```

Required coverage:

- `POST /projects/open-demo` returns `demo_project`.
- Artifact endpoints return fixture JSON.
- Job endpoints return immediately with `job_id`.
- Job failures are visible through `GET /jobs/{job_id}`.

### Manifest validation

Owner: Dev 3.

```text
tests/backend/manifests/test_contracts.py
tests/backend/manifests/test_duration_reconciliation.py
tests/backend/manifests/test_critic_patches.py
```

Required coverage:

- Fixture `block_manifest.json` validates.
- Duplicate block ids fail.
- Missing font path fails for title blocks.
- `tts_duration > video_duration` extends source clip.
- Trim suggestion above 30 percent fails.
- Rejected critic suggestions do not modify manifest.

### Renderer

Owner: Dev 3.

```text
tests/backend/rendering/test_ffmpeg_commands.py
tests/backend/rendering/test_concat.py
tests/backend/rendering/test_smoke_render.py
```

Required coverage:

- Title block command includes explicit `fontfile`.
- Source clip command applies source volume and TTS fade.
- Concat file uses one `file` line per block.
- Smoke render is skipped if `ffmpeg` is unavailable.
- Smoke render passes `ffprobe` if `ffmpeg` is available.

### Gemini integrations

Owner: Dev 4.

```text
tests/backend/integrations/test_model_policy.py
tests/backend/integrations/test_structured_outputs.py
tests/backend/prompts/test_prompts.py
```

Required coverage:

- Defaults use `gemini-2.5-flash-lite`, `gemini-2.5-flash-preview-tts`, and `gemini-2.5-flash-image`.
- No Pro model is selected by default.
- Structured JSON response parses into Dev 3 models.
- Blind critic prompt forbids visual-quality critique.
- Background prompt includes "No text, no letters, no logos."
- Narration prompt includes 2 words per second limit.

## Frontend Tests

Owner: Dev 1.

```text
tests/frontend/
apps/web/src/**/*.test.tsx
```

Required coverage:

- Dashboard renders empty state.
- Open demo project populates artifact panels.
- Job polling updates progress.
- Failed job displays error and retry action.
- Critic suggestions render approve/reject controls.
- Approved and rejected ids are submitted correctly.
- Final render preview appears when render metadata exists.

## Integration Smoke Tests

Run before the demo:

```bash
pytest tests/backend -q
npm --prefix apps/web test
```

If FFmpeg is installed:

```bash
pytest tests/backend/rendering/test_smoke_render.py -q
```

Manual browser smoke:

```text
1. Start backend.
2. Start frontend.
3. Open demo project.
4. Run pipeline stages in order.
5. Approve one critic suggestion and reject one.
6. Render.
7. Play final MP4.
```

## Tests Not In Default CI

Do not run live Gemini tests by default. They consume credits and introduce network flake. Live Gemini checks should be opt-in:

```bash
RUN_LIVE_GEMINI=1 pytest tests/backend/integrations/test_live_gemini.py -q
```

Live tests should:

- Use one tiny prompt.
- Use cheap models.
- Save no large assets.
- Print estimated cost metadata if available.


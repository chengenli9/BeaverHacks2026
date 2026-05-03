# Scenerio Architecture Report

> Archived planning document. For current setup, endpoints, project layout, and test commands, use `README.md`, `docs/API_AND_DATA_CONTRACTS.md`, `docs/DEMO_RUNBOOK.md`, `docs/TESTING_STRATEGY.md`, and `docs/GEMINI_MODEL_POLICY.md`.

Last verified: 2026-05-02

## Executive Summary

Scenerio is locked as a local-first, async, manifest-driven, block-rendered Gemini rough-cut system. It is not a nonlinear editor. It is a polished pipeline dashboard that turns raw footage into a demo-ready rough cut with observable artifacts at each stage.

The core rule is:

```text
Gemini plans.
Backend validates.
Human approves.
FFmpeg renders.
```

The architecture optimizes for a hackathon demo. It avoids production queueing, cloud storage, user accounts, deep timeline editing, giant FFmpeg filtergraphs, and post-render video critique in the live path. It keeps the parts people will judge visible: pipeline progress, manifest cards, critic suggestions, approvals, and a final MP4 preview.

## Current Repo Critique

The repo began with only `.git` and no committed source, docs, fixtures, or contracts. That creates four immediate risks:

- No stable file ownership boundaries for parallel developers.
- No sample artifacts for frontend and backend work to begin independently.
- No shared data contracts for plan, manifest, critic suggestions, or job state.
- No documented model budget policy, so accidental Pro usage could burn credits.

The necessary structural change is to add documentation, sample fixtures, and explicit ownership boundaries before implementation. This package creates those boundaries without prematurely generating application code.

## Product Concept

Scenerio turns source footage into a polished rough-cut video through a visible, controllable pipeline:

```text
Footage
  -> scene analysis
  -> structured edit plan
  -> narration and textless visual assets
  -> duration reconciliation
  -> manifest critique
  -> human approval
  -> normalized block render
  -> final MP4 concat
```

Gemini is used for interpretation and generation. FFmpeg is used for deterministic media operations. The backend is the authority on timing, file paths, validation, and render safety.

## Architecture Diagram

```text
React + TypeScript UI
  |
  v
FastAPI localhost backend
  |
  v
In-memory job system
  |
  +--> Local project folder
  |
  +--> Gemini API
  |      +--> scene analysis
  |      +--> structured edit planning
  |      +--> TTS narration
  |      +--> Nano Banana textless backgrounds
  |      +--> blind manifest pre-critique
  |
  +--> Manifest validator
  |      +--> duration reconciliation
  |      +--> path normalization
  |      +--> approval patch validation
  |
  +--> FFmpeg block renderer
         +--> normalized block MP4s
         +--> concat demuxer
         +--> final_render.mp4
```

## Non-Negotiable Rules

### 1. No synchronous long-running requests

Every expensive action returns a `job_id`. The browser polls job state.

```http
POST /jobs/render
200 OK
{ "job_id": "job_render_001", "status": "queued" }

GET /jobs/job_render_001
200 OK
{
  "job_id": "job_render_001",
  "status": "running",
  "stage": "rendering_blocks",
  "progress": 0.6,
  "message": "Rendering block 3 of 5",
  "error": null
}
```

For the hackathon, use FastAPI `BackgroundTasks` and an in-memory `JOBS` dictionary. Do not add Redis, Celery, or a production queue until the demo path is done.

### 2. No AI-generated text inside title-card images

Gemini image generation creates textless background plates only. Exact text is rendered by FFmpeg `drawtext` using a bundled font.

Bad image prompt:

```text
Generate a title card that says "Scenerio".
```

Good image prompt:

```text
Generate a cinematic 16:9 abstract technology background. No text, no letters, no logos.
```

### 3. Bundle a known font

Do not depend on system fonts. The renderer must use a repo-controlled path:

```text
assets/fonts/Inter-Bold.ttf
```

Every title block must set `fontfile` explicitly. Missing fonts should fail validation before FFmpeg starts.

### 4. Duration reconciliation happens before render

Gemini may suggest timing, but the backend owns timing.

```python
video_duration = source_end - source_start

if tts_duration > video_duration:
    source_end = source_start + tts_duration
```

Narration generation must also include:

```text
Narration must not exceed 2 words per second of allocated clip duration.
```

### 5. The critic is blind

The pre-render critic receives only `scene_index.json` and `block_manifest.json`. It must not claim to inspect lighting, framing, acting, camera quality, or visual aesthetics.

The critic can evaluate:

- Narrative flow.
- Pacing.
- Ordering.
- Missing context.
- Duration mismatches.
- Obvious manifest problems.

The critic cannot suggest trimming more than 30 percent of a block's current duration.

### 6. Render blocks, then concat

Do not build one giant filtergraph. Each block renders to a complete normalized MP4, then FFmpeg concat demuxer creates `final_render.mp4`.

```text
blocks/
  001_title.mp4
  002_hook.mp4
  003_demo_with_tts.mp4
  004_end.mp4

concat.txt
  file 'blocks/001_title.mp4'
  file 'blocks/002_hook.mp4'
  file 'blocks/003_demo_with_tts.mp4'
  file 'blocks/004_end.mp4'
```

## Component Boundaries

### Frontend UI

Owned by Dev 1.

Responsibilities:

- Pipeline dashboard.
- Action buttons for each job.
- Polling and progress rendering.
- Scene, plan, manifest, critic, and render previews.
- Approval and rejection UX for critic cards.

The UI must not implement media logic, Gemini prompts, manifest reconciliation, or FFmpeg commands.

### Backend API and Jobs

Owned by Dev 2.

Responsibilities:

- FastAPI app boot.
- Local project open/load endpoints.
- `POST /jobs/*` endpoints.
- `GET /jobs/{job_id}` polling.
- In-memory job store.
- Project file serving for JSON artifacts and final render.

The API layer orchestrates services but does not own FFmpeg command construction or Gemini prompts.

### Manifest and Renderer

Owned by Dev 3.

Responsibilities:

- Pydantic contracts for manifests and critic suggestions.
- Duration reconciliation.
- Path validation.
- Approval patch application rules.
- FFmpeg block render commands.
- Concat demuxer list creation.
- Render smoke checks with `ffprobe`.

The renderer consumes manifests and file assets. It does not call Gemini.

### Gemini Integrations and Assets

Owned by Dev 4.

Responsibilities:

- Gemini client wrapper.
- Cheap default model selection.
- Structured output schemas.
- Scene indexing prompts.
- Plan generation prompts.
- TTS generation.
- Textless background generation.
- Blind manifest critic prompt.
- Gemini call logging.

The integration layer produces JSON, WAV, and PNG artifacts. It does not render video.

## Data Flow

```text
1. User opens sample or local project.
2. Backend validates project folder shape.
3. Scene analysis job creates cache/scene_index.json.
4. Plan generation job creates manifests/plan.json.
5. TTS job creates assets/tts/*.wav and measures exact duration with ffprobe.
6. Background job creates assets/backgrounds/*.png.
7. Manifest build job reconciles durations and writes manifests/block_manifest.json.
8. Pre-critique job writes manifests/critic_suggestions.json.
9. UI displays suggestions as approve/reject cards.
10. Approved patches update block_manifest.json.
11. Render job creates blocks/*.mp4.
12. Concat job creates renders/final_render.mp4.
13. UI plays final render.
```

## Gemini Model Budget Policy

Use cheaper models by default:

```text
Scene analysis:       gemini-2.5-flash-lite
Plan generation:      gemini-2.5-flash-lite
Manifest critique:    gemini-2.5-flash-lite
Narration scripting:  gemini-2.5-flash-lite
TTS audio:            gemini-2.5-flash-preview-tts
Background images:    gemini-2.5-flash-image
```

Do not use Pro models in the MVP path. Do not enable search grounding by default. Do not generate multiple unused variants during the live demo. If a fallback is needed, make the model switch explicit in `.env` and log it.

Recommended `.env.example` values:

```bash
GEMINI_API_KEY=
GEMINI_TEXT_MODEL=gemini-2.5-flash-lite
GEMINI_TTS_MODEL=gemini-2.5-flash-preview-tts
GEMINI_IMAGE_MODEL=gemini-2.5-flash-image
GEMINI_ENABLE_GROUNDING=false
GEMINI_MAX_OUTPUT_TOKENS=4096
```

## Backend Endpoints

```text
POST /projects/open-demo
POST /jobs/analyze-scenes
POST /jobs/generate-plan
POST /jobs/generate-tts
POST /jobs/generate-assets
POST /jobs/build-manifest
POST /jobs/precritique
POST /jobs/apply-approved-patches
POST /jobs/render

GET /jobs/{job_id}
GET /projects/{project_id}/scene-index
GET /projects/{project_id}/plan
GET /projects/{project_id}/manifest
GET /projects/{project_id}/critic-suggestions
GET /projects/{project_id}/render
```

## Project Folder Layout

```text
project/
  source/
    demo_footage.mp4

  cache/
    frames/
    audio/
    scene_index.json

  assets/
    backgrounds/
      bg_001.png
    tts/
      tts_002.wav
    fonts/
      Inter-Bold.ttf

  manifests/
    plan.json
    block_manifest.json
    critic_suggestions.json

  blocks/
    001_title.mp4
    002_hook.mp4
    003_demo_with_tts.mp4

  renders/
    final_render.mp4

  logs/
    jobs.jsonl
    gemini_calls.jsonl
    ffmpeg.log
```

## UI Architecture

Build a pipeline dashboard, not a timeline editor.

```text
+----------------------------------------------------------------+
| Scenerio | Analyze | Plan | Pre-Critique | Render           |
+-------------------+-----------------------+--------------------+
| Agent Event Log   | Block Manifest         | Output / Critic    |
|                   |                        |                    |
| [x] Scenes indexed| [001 Title]            | Video preview      |
| [x] Plan generated| [002 Demo + TTS]       |                    |
| [x] TTS measured  | [003 Ending]           | Critic cards       |
| [x] Manifest fixed|                        | Approve / Reject   |
| [ ] Rendering 60% |                        |                    |
+-------------------+-----------------------+--------------------+
```

Required UI states:

- Empty project.
- Demo project loaded.
- Job queued.
- Job running.
- Job failed with actionable error.
- Artifact available.
- Critic suggestions pending approval.
- Final render available.

## Error Handling

All errors should be converted to job failure states with useful messages. The UI should never hang on a failed async action.

Important validation failures:

- Missing `GEMINI_API_KEY` before Gemini jobs.
- Missing `ffmpeg` or `ffprobe` before render jobs.
- Missing `assets/fonts/Inter-Bold.ttf` before title/text blocks render.
- Missing source clip before source blocks render.
- TTS duration exceeds adjusted source media duration.
- Critic suggestion violates max trim limits.
- Final render is missing, zero bytes, or fails `ffprobe`.

## Observability

Write append-only JSONL logs:

```text
logs/jobs.jsonl
logs/gemini_calls.jsonl
logs/ffmpeg.log
```

Never log API keys or full binary payloads. Log model name, stage, prompt category, elapsed time, token counts if available, artifact paths, and sanitized error messages.

## Testing Strategy

Unit tests are required where logic can break the demo:

- Job state transitions.
- Manifest schema validation.
- Duration reconciliation.
- Critic patch constraints.
- FFmpeg command construction.
- Concat list generation.
- Gemini structured-output parsing with mocked responses.
- Frontend polling and failure states.

Integration smoke tests are required for:

- Opening `samples/demo_project`.
- Building a manifest from fixture JSON.
- Rendering a tiny generated color/testsrc block if FFmpeg is installed.
- Serving a final render path.

## Demo Readiness Checklist

- The demo project opens with one button.
- Every pipeline stage has visible progress.
- The UI can show real JSON summaries without exposing hidden reasoning.
- The critic suggestions appear as approve/reject cards.
- Rendering creates normalized block files before final concat.
- `final_render.mp4` plays in the UI.
- A failed Gemini call or FFmpeg render shows a clear retry path.
- The app can run without Redis, Celery, Docker, accounts, or cloud storage.

## Source References

- Gemini structured outputs: https://ai.google.dev/gemini-api/docs/structured-output
- Gemini model list: https://ai.google.dev/gemini-api/docs/models
- Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini TTS: https://ai.google.dev/gemini-api/docs/speech-generation
- Gemini image generation / Nano Banana: https://ai.google.dev/gemini-api/docs/image-generation
- FastAPI background tasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
- FFmpeg drawtext filter: https://ffmpeg.org/ffmpeg-filters.html#drawtext
- FFmpeg concat demuxer: https://ffmpeg.org/ffmpeg-formats.html#concat


# 🏆 Won 1st Place in the Google Best Use of Gemini Track @ BeaverHacks 2026!

# Scenerio

Scenerio is a local-first demo-video editor for turning hackathon footage into a structured rough cut. The current app includes a FastAPI backend, a React/Vite dashboard, Gemini-powered planning and asset steps, deterministic manifest validation, FFmpeg rendering, and Remotion-generated motion/text scenes.

The important rule: project artifacts live on disk. The UI and API read and write JSON manifests, generated assets, block videos, logs, and the final render inside each project folder.

## Current App

- `apps/web` - React 19 + Vite dashboard for projects, media, pipeline jobs, manifests, critic suggestions, and render preview.
- `backend/app` - FastAPI app with project CRUD, media import, background jobs, Gemini integration, manifest mutation, and render endpoints.
- `apps/remotion` - Remotion renderer for generated text/motion scene assets.
- `samples/demo_project` - built-in demo project opened by `POST /projects/open-demo`.
- `projects` - user-created local projects and generated outputs.
- `tests` - backend pytest suite plus frontend Vitest tests under `apps/web/src`.

## Requirements

- Python 3.13
- Node.js and npm
- FFmpeg/ffprobe on `PATH` for real rendering and media probing
- Gemini API key for live AI stages

Install dependencies:

```bash
pip install -r requirements.txt
npm --prefix apps/web install
npm --prefix apps/remotion install
```

Create local config:

```bash
cp .env.example .env
```

Set at least `GEMINI_API_KEY` for live Gemini calls. Without it, cached artifacts and non-AI routes can still be used.

## Run Locally

Backend:

```bash
python3.13 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```bash
npm --prefix apps/web run dev
```

Or start both with:

```bash
./startApp.sh
```

Open the Vite URL printed by the frontend, usually `http://localhost:5173`.

## Pipeline

The dashboard drives these backend jobs:

1. Analyze scenes: `POST /jobs/analyze-scenes?project_id=...`
2. Generate plan: `POST /jobs/generate-plan?project_id=...`
3. Generate TTS: `POST /jobs/generate-tts?project_id=...`
4. Generate assets: `POST /jobs/generate-assets?project_id=...`
5. Build manifest: `POST /jobs/build-manifest?project_id=...`
6. Pre-critique: `POST /jobs/precritique?project_id=...`
7. Apply approved patches: `POST /jobs/apply-approved-patches`
8. Render: `POST /jobs/render?project_id=...`
9. Review render: `POST /jobs/review-render?project_id=...`

Poll job status at `GET /jobs/{job_id}`.

## Project Layout

Every project must contain:

```text
source/       raw uploaded media
cache/        scene indexes, probes, QA frames, temporary renders
assets/       generated backgrounds, images, TTS, fonts, Remotion scene specs
blocks/       per-block rendered MP4s
renders/      final_render.mp4
manifests/    plan.json, block_manifest.json, critic_suggestions.json
logs/         FFmpeg, Remotion, and Gemini logs when present
project.json  metadata for user-created projects
```

The demo project is read from `samples/demo_project`. User projects are stored under `projects`.

## Docs

- [API and data contracts](docs/API_AND_DATA_CONTRACTS.md)
- [Demo runbook](docs/DEMO_RUNBOOK.md)
- [Testing strategy](docs/TESTING_STRATEGY.md)
- [Gemini model policy](docs/GEMINI_MODEL_POLICY.md)

Older planning and handoff docs may still be useful for background, but the files above describe the current runnable app.

## Tests

Backend:

```bash
pytest tests/backend -q
```

Frontend:

```bash
npm --prefix apps/web test
```

Frontend build:

```bash
npm --prefix apps/web run build
```

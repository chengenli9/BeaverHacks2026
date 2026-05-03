# Demo Runbook

## Setup

Start the backend and frontend:

```bash
python3.13 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
npm --prefix apps/web run dev
```

Or:

```bash
./startApp.sh
```

Use `.env` for Gemini settings. Live AI stages need `GEMINI_API_KEY`; cached artifacts and normal project browsing do not.

## Golden Path

1. Open the Vite frontend.
2. Open the built-in Demo Project or create a new project.
3. Import media into `source/` for a new project.
4. Run Analyze Scenes.
5. Run Generate Plan.
6. Review and optionally reorder, delete, prompt-edit, or insert plan beats.
7. Run Generate TTS and Generate Assets.
8. Run Build Manifest.
9. Run Pre-Critique.
10. Approve or reject critic suggestions.
11. Apply Approved Patches.
12. Render.
13. Play the final MP4 from the render preview.
14. Optionally run Review Render for render QA suggestions.

## Fallbacks

If Gemini is unavailable, use an existing project under `projects/` with generated artifacts or the fixture files under `samples/demo_project`.

If FFmpeg fails, inspect `logs/ffmpeg.log` in the project folder and the failed job error from `GET /jobs/{job_id}`.

If the render preview does not refresh, call `GET /projects/{project_id}/render`; the response includes a `cache_key` based on the final render modification time.

## Pre-Demo Check

```bash
pytest tests/backend -q
npm --prefix apps/web test
npm --prefix apps/web run build
```

Also confirm:

- `GET http://localhost:8000/health` returns `{"status":"ok"}`.
- `GET /projects` lists the demo project.
- `GET /projects/{project_id}/render/file` plays or downloads the expected MP4.

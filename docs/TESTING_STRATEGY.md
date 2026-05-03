# Testing Strategy

Keep default tests local, deterministic, and cheap. Do not run live Gemini calls in the normal test path.

## Backend

Run:

```bash
pytest tests/backend -q
```

Current backend coverage includes:

- API routing and project/media endpoints.
- In-memory job creation, progress, success, and failure behavior.
- Gemini service/model-policy behavior with mocked calls.
- Prompt contract checks.
- Scene index, plan, manifest, critic patch, source-bound, multi-source, and duration reconciliation validation.
- Rendering command construction and rendering service behavior.

Useful focused runs:

```bash
pytest tests/backend/api -q
pytest tests/backend/manifests -q
pytest tests/backend/rendering -q
pytest tests/backend/integrations -q
```

## Frontend

Run:

```bash
npm --prefix apps/web test
npm --prefix apps/web run build
```

Frontend tests live in `apps/web/src/__tests__` and cover dashboard behavior plus API client behavior.

## Remotion

Run:

```bash
npm --prefix apps/remotion run build
```

The Python rendering service can call Remotion for motion assets when project blocks include `motion_asset` references.

## Manual Smoke

1. Start backend and frontend.
2. Open or create a project.
3. Import at least one video for a new project.
4. Run the pipeline through render.
5. Confirm `renders/final_render.mp4` exists.
6. Confirm the UI can play `GET /projects/{project_id}/render/file`.

Live Gemini smoke tests should stay opt-in and use the cheapest configured models.

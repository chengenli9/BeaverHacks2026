# Developer Work Split

> Archived planning document. Ownership lanes here are historical and may not match the current codebase. Use `README.md` for the current repo shape.

## Principle

Each developer owns a vertical slice with a clear write scope. Other developers can read those files but should not edit them. If an interface change is needed, write it in the relevant handoff channel or issue first, then let the owning developer make the change.

## Summary Table

| Dev | Role | Primary Mission | Write Scope |
| --- | --- | --- | --- |
| Dev 1 | Frontend Lead | Pipeline dashboard and approval UI | `apps/web/**`, `tests/frontend/**`, `docs/frontend/**` |
| Dev 2 | Backend API Lead | FastAPI app, project loading, job orchestration | `backend/app/api/**`, `backend/app/jobs/**`, `backend/app/projects/**`, `backend/app/main.py`, `tests/backend/api/**`, `tests/backend/jobs/**` |
| Dev 3 | Rendering Lead | Manifest contracts, validation, FFmpeg rendering | `backend/app/manifests/**`, `backend/app/rendering/**`, `tests/backend/manifests/**`, `tests/backend/rendering/**` |
| Dev 4 | AI Integration Lead | Gemini wrappers, prompts, TTS, image assets, critic | `backend/app/integrations/**`, `backend/app/prompts/**`, `backend/app/assets/**`, `tests/backend/integrations/**`, `tests/backend/prompts/**` |

## Shared Read-Only Files

These files are shared references. Avoid editing them during implementation unless the team agrees.

```text
README.md
docs/ARCHITECTURE_REPORT.md
docs/IMPLEMENTATION_PLAN.md
docs/API_AND_DATA_CONTRACTS.md
docs/TESTING_STRATEGY.md
samples/demo_project/
assets/fonts/
```

## Integration Contracts

### Dev 1 consumes Dev 2 API

Dev 1 should code against these endpoints only:

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

### Dev 2 orchestrates Dev 3 and Dev 4 services

Dev 2 can import public service functions after they exist:

```python
from backend.app.manifests.service import build_manifest, apply_approved_patches
from backend.app.rendering.service import render_project
from backend.app.integrations.gemini.service import (
    analyze_scenes,
    generate_plan,
    generate_tts,
    generate_background_assets,
    precritique_manifest,
)
```

Dev 2 should not edit service internals owned by Dev 3 or Dev 4.

### Dev 3 consumes Dev 4 assets

Dev 3 treats the following as file artifacts:

```text
assets/backgrounds/*.png
assets/tts/*.wav
cache/scene_index.json
manifests/plan.json
manifests/critic_suggestions.json
```

Dev 3 does not call Gemini.

### Dev 4 consumes Dev 3 schemas

Dev 4 should return data that validates against Dev 3 contracts. If a schema feels wrong, ask Dev 3 to adjust it rather than forking a second schema.

## Merge Safety Rules

- No shared barrel files unless one owner maintains them.
- No broad formatting changes across the repo.
- No moving files from another developer's owned scope.
- No "cleanup" commits that touch unrelated lanes.
- Use sample fixtures instead of waiting on live Gemini or FFmpeg.
- Keep public interfaces small and documented in tests.

## Integration Day Order

1. Dev 3 lands contracts and fixture validation.
2. Dev 2 lands API and job store against fixtures.
3. Dev 4 lands mocked Gemini service tests, then live calls behind env vars.
4. Dev 1 points UI from mocks to local API.
5. All devs integrate approval loop.
6. All devs run demo checklist.

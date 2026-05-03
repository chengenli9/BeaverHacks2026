# Repository Critique and Changes

> Archived planning document. Use `README.md` and the current docs for the implemented app.

## Initial State

The repository contained only `.git` and no committed project files. There was no implementation to critique for correctness, but the absence of structure was itself a serious hackathon risk.

## Critique

### 1. No architecture source of truth

Without a committed architecture report, each developer would likely build a different version of Scenerio. That would create avoidable merge conflicts and integration churn.

Change made:

```text
docs/ARCHITECTURE_REPORT.md
```

### 2. No implementation sequencing

The locked architecture depends on doing the deterministic render path before live AI complexity. Without a plan, the team could spend the hackathon wiring Gemini before anything can render.

Change made:

```text
docs/IMPLEMENTATION_PLAN.md
```

### 3. No parallel work boundaries

Four devs need four non-overlapping write scopes. The initial repo had no folders to make that obvious.

Changes made:

```text
docs/DEVELOPER_WORK_SPLIT.md
docs/dev-handoffs/DEV1_FRONTEND_PIPELINE_UI.md
docs/dev-handoffs/DEV2_BACKEND_JOBS_API.md
docs/dev-handoffs/DEV3_MANIFEST_RENDERER.md
docs/dev-handoffs/DEV4_GEMINI_ASSETS_CRITIC.md
```

### 4. No data contracts

The pipeline is manifest-driven, so schemas are the system's backbone. If those are vague, every component breaks at integration.

Change made:

```text
docs/API_AND_DATA_CONTRACTS.md
```

### 5. No sample project

The frontend should not wait for backend and Gemini. The backend should not wait for real footage. Fixtures let everyone build immediately.

Change made:

```text
samples/demo_project/
```

### 6. No model budget policy

The architecture requires Gemini, but the MVP must avoid unnecessary credit burn.

Change made:

```text
README.md
docs/ARCHITECTURE_REPORT.md
docs/dev-handoffs/DEV4_GEMINI_ASSETS_CRITIC.md
```

### 7. No render font policy

FFmpeg text rendering can fail across machines if it depends on system fonts.

Change made:

```text
assets/fonts/README.md
samples/demo_project/assets/fonts/README.md
```

## What Should Not Be Changed Yet

Do not introduce production infrastructure before the demo works:

- No Redis.
- No Celery.
- No auth.
- No database.
- No cloud storage.
- No complex timeline editor.
- No cross-repo plugin system.

## Current Recommended Structure

```text
apps/web/
backend/app/api/
backend/app/jobs/
backend/app/projects/
backend/app/manifests/
backend/app/rendering/
backend/app/integrations/gemini/
backend/app/prompts/
assets/fonts/
samples/demo_project/
tests/backend/
tests/frontend/
docs/
```

This shape is intentionally boring. Boring is good here: it gives a hackathon team obvious places to work and leaves the interesting polish for the demo.


# Dev 2 Handoff: Backend Jobs and Project API

## Role

Backend API Lead. Your job is to make the local FastAPI backend reliable, async-looking, and easy for the frontend to consume.

## Write Scope

You own:

```text
backend/app/main.py
backend/app/api/**
backend/app/jobs/**
backend/app/projects/**
tests/backend/api/**
tests/backend/jobs/**
```

You may read renderer and Gemini services, but do not edit them. Import their public functions when they exist.

## Product Goal

Every expensive operation returns immediately with a `job_id`. The UI can poll job state and never hangs during Gemini or FFmpeg work.

## Required Endpoints

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

## Work Plan

### Step 1: FastAPI app

Create:

```text
backend/app/main.py
backend/app/api/routes.py
```

Set up:

- FastAPI app.
- Local CORS for the frontend dev server.
- Health endpoint at `GET /health`.
- Router registration.

### Step 2: Job store

Create:

```text
backend/app/jobs/store.py
backend/app/jobs/models.py
```

Use a simple in-memory dictionary:

```python
JOBS: dict[str, JobStatus] = {}
```

Required operations:

```text
create_job(project_id, stage, message)
mark_running(job_id, message)
update_progress(job_id, progress, message)
mark_succeeded(job_id, message)
mark_failed(job_id, error)
get_job(job_id)
```

Use a lock if background tasks can update from multiple threads.

### Step 3: Background task wrapper

Create:

```text
backend/app/jobs/runner.py
```

It should:

- Mark job running.
- Call the service function.
- Update progress when callbacks are available.
- Mark succeeded.
- Catch exceptions and mark failed.

### Step 4: Project loader

Create:

```text
backend/app/projects/service.py
backend/app/projects/models.py
```

For MVP:

- `open_demo_project()` returns `samples/demo_project`.
- Validate required folders exist.
- Return project id, display name, and artifact availability.

### Step 5: Artifact endpoints

Serve:

```text
cache/scene_index.json
manifests/plan.json
manifests/block_manifest.json
manifests/critic_suggestions.json
renders/final_render.mp4
```

Return a clear 404 if an artifact is not created yet.

### Step 6: Service orchestration

Stub services first so Dev 1 can integrate:

```python
def analyze_scenes(project): ...
def generate_plan(project): ...
def generate_tts(project): ...
def generate_background_assets(project): ...
def build_manifest(project): ...
def precritique_manifest(project): ...
def apply_approved_patches(project, request): ...
def render_project(project): ...
```

Then replace stubs with imports:

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

## Tests You Own

Create tests for:

```text
job creation
job success transition
job failure transition
unknown job 404
open demo project
artifact JSON endpoints
job endpoints return immediately
```

Run:

```bash
pytest tests/backend/jobs tests/backend/api -q
```

## Do Not Touch

```text
apps/web/**
backend/app/manifests/**
backend/app/rendering/**
backend/app/integrations/**
backend/app/prompts/**
samples/**
```

## Agent Prompt For Your Coding Agent

```text
You are Dev 2, Backend API Lead for Scenerio. Work only in backend/app/main.py, backend/app/api, backend/app/jobs, backend/app/projects, tests/backend/api, and tests/backend/jobs. Implement FastAPI endpoints, in-memory jobs, project loading, artifact serving, and background task orchestration. Do not edit frontend, renderer, manifest internals, Gemini integrations, prompts, or sample fixtures. Use stubs until the owning services exist, then import public functions.
```


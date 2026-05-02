# Dev 1 Handoff: Frontend Pipeline Dashboard

## Role

Frontend Lead. Your job is to make DirectorLoop look demo-ready and feel complete. Build the pipeline dashboard, artifact viewers, job progress, approval cards, and final video preview.

## Write Scope

You own:

```text
apps/web/**
tests/frontend/**
docs/frontend/**
```

You may read everything else. Do not edit backend, renderer, Gemini, sample fixtures, or shared contracts unless the team explicitly asks you to.

## Product Goal

The first screen should be the usable app, not a landing page. The UI should look like a polished production tool for preparing a demo video:

- Dense but readable.
- Clear pipeline state.
- High-confidence action buttons.
- Real artifact previews.
- No fake hidden reasoning.
- No oversized marketing hero.

## Required UI Layout

Build a three-panel dashboard:

```text
+----------------------------------------------------------------+
| DirectorLoop | Analyze | Plan | Assets | Pre-Critique | Render  |
+-------------------+-----------------------+--------------------+
| Agent Event Log   | Block Manifest         | Output / Critic    |
|                   |                        |                    |
| Pipeline steps    | Manifest cards         | Video preview      |
| Job progress      | Timing warnings        | Critic cards       |
| Errors/retries    | Block statuses         | Approve / Reject   |
+-------------------+-----------------------+--------------------+
```

## API Surface To Use

Only call these endpoints:

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

### Step 1: Scaffold the app

Create a React + TypeScript app in:

```text
apps/web/
```

Recommended stack:

```text
Vite
React
TypeScript
Vitest
React Testing Library
lucide-react
```

### Step 2: Build API client

Create:

```text
apps/web/src/api/directorloopApi.ts
```

Expose typed functions:

```ts
openDemoProject(): Promise<ProjectSummary>
startJob(kind: JobKind, body?: unknown): Promise<JobStartResponse>
getJob(jobId: string): Promise<JobStatus>
getSceneIndex(projectId: string): Promise<SceneIndex>
getPlan(projectId: string): Promise<Plan>
getManifest(projectId: string): Promise<BlockManifest>
getCriticSuggestions(projectId: string): Promise<CriticSuggestions>
getRender(projectId: string): Promise<RenderSummary>
applyApprovedPatches(request: ApplyPatchesRequest): Promise<JobStartResponse>
```

Use frontend-local types that mirror `docs/API_AND_DATA_CONTRACTS.md`.

### Step 3: Build dashboard state

Create:

```text
apps/web/src/state/pipelineStore.ts
```

Track:

```text
projectId
activeJobs
artifactStatus
sceneIndex
plan
manifest
criticSuggestions
renderSummary
errors
```

Keep state simple. Do not add Redux unless the app is already too hard to reason about.

### Step 4: Build components

Suggested files:

```text
apps/web/src/components/AppShell.tsx
apps/web/src/components/PipelineControls.tsx
apps/web/src/components/EventLog.tsx
apps/web/src/components/ManifestPanel.tsx
apps/web/src/components/CriticPanel.tsx
apps/web/src/components/RenderPreview.tsx
apps/web/src/components/ProgressBar.tsx
apps/web/src/components/StatusBadge.tsx
```

### Step 5: Build polished states

Required states:

- Empty state with "Open Demo Project".
- Loaded state with sample artifacts.
- Queued job.
- Running job with progress.
- Failed job with retry.
- Critic suggestions needing approval.
- Final video ready.

### Step 6: Approval UX

For each critic suggestion:

- Show action, block id, amount, and reason.
- Provide approve and reject controls.
- Keep selection local until user clicks "Apply Approved Changes".
- Send only approved and rejected ids.

Request body:

```json
{
  "project_id": "demo_project",
  "approved_suggestion_ids": ["s001"],
  "rejected_suggestion_ids": ["s002"]
}
```

## Visual Direction

Use a practical production-tool style:

- Dark or neutral shell is acceptable, but avoid a one-note dark blue/slate interface.
- Use restrained accent colors for statuses.
- Use icons for actions where obvious.
- Use cards only for repeated items like blocks and critic suggestions.
- Do not put cards inside cards.
- Do not create a landing page.
- Do not explain keyboard shortcuts or product concepts with visible instructional copy.

## Tests You Own

Create frontend tests for:

```text
empty dashboard renders
open demo populates panels
job polling updates progress
failed job renders retry
critic approval submits approved/rejected ids
render preview appears
```

Run:

```bash
npm --prefix apps/web test
```

## Do Not Touch

```text
backend/**
samples/**
assets/fonts/**
docs/API_AND_DATA_CONTRACTS.md
```

## Agent Prompt For Your Coding Agent

```text
You are Dev 1, Frontend Lead for DirectorLoop. Work only in apps/web, tests/frontend, and docs/frontend. Build a polished React + TypeScript pipeline dashboard against the API contracts in docs/API_AND_DATA_CONTRACTS.md. Do not edit backend, renderer, Gemini, sample fixtures, or shared docs. Use mocked API responses first, then support localhost:8000. The app should open directly into the usable dashboard, show job progress, artifact summaries, critic approve/reject cards, and the final MP4 preview.
```


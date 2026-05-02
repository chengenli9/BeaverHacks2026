# DirectorLoop

DirectorLoop is a local-first, manifest-driven rough-cut editor for turning raw hackathon footage into a polished demo video. The locked architecture is demo-first: Gemini plans and critiques structured manifests, the backend validates every timing decision, humans approve changes, and FFmpeg renders deterministic normalized blocks.

This repository currently contains the architecture and implementation handoff package for a four-developer hackathon build.

## Start Here

- [Architecture report](docs/ARCHITECTURE_REPORT.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Developer work split](docs/DEVELOPER_WORK_SPLIT.md)
- [API and data contracts](docs/API_AND_DATA_CONTRACTS.md)
- [Testing strategy](docs/TESTING_STRATEGY.md)
- [Repository critique and changes](docs/REPO_CRITIQUE_AND_CHANGES.md)
- [Gemini model and credit policy](docs/GEMINI_MODEL_POLICY.md)
- [Demo runbook](docs/DEMO_RUNBOOK.md)

## Four Dev Lanes

- Dev 1: [Frontend pipeline dashboard](docs/dev-handoffs/DEV1_FRONTEND_PIPELINE_UI.md)
- Dev 2: [Backend jobs and project API](docs/dev-handoffs/DEV2_BACKEND_JOBS_API.md)
- Dev 3: [Manifest validation and FFmpeg renderer](docs/dev-handoffs/DEV3_MANIFEST_RENDERER.md)
- Dev 4: [Gemini integrations, prompts, and assets](docs/dev-handoffs/DEV4_GEMINI_ASSETS_CRITIC.md)

## Repo Shape

```text
apps/web/                  React + TypeScript UI owned by Dev 1
backend/app/api/           FastAPI routes owned by Dev 2
backend/app/jobs/          In-memory job system owned by Dev 2
backend/app/projects/      Local project loader owned by Dev 2
backend/app/manifests/     Manifest contracts and reconciliation owned by Dev 3
backend/app/rendering/     FFmpeg block renderer owned by Dev 3
backend/app/integrations/  Gemini API clients owned by Dev 4
backend/app/prompts/       Structured prompts owned by Dev 4
assets/fonts/              Bundled render fonts
samples/demo_project/      Static fixture project for parallel development
tests/                     Test folders partitioned by owner
```

## Cost Policy

All Gemini text planning, scene indexing, and critic endpoints should default to `gemini-2.5-flash-lite`. TTS should default to `gemini-2.5-flash-preview-tts`. Textless background generation should default to `gemini-2.5-flash-image`. Do not use Pro models in the live hackathon path unless the team explicitly opts into a higher-cost fallback.

Copy `.env.example` to `.env` when implementation begins.


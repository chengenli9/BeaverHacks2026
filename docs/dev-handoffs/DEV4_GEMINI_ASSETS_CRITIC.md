# Dev 4 Handoff: Gemini Integrations, Assets, and Blind Critic

## Role

AI Integration Lead. Your job is to make Gemini useful, cheap, structured, and contained. The rest of the app should see file artifacts and validated JSON, not freeform model output.

## Write Scope

You own:

```text
backend/app/integrations/**
backend/app/prompts/**
backend/app/assets/**
tests/backend/integrations/**
tests/backend/prompts/**
```

Do not edit renderer, API orchestration, frontend, or shared sample fixtures unless the team agrees.

## Cost Policy

Default models:

```text
GEMINI_TEXT_MODEL=gemini-2.5-flash-lite
GEMINI_TTS_MODEL=gemini-2.5-flash-preview-tts
GEMINI_IMAGE_MODEL=gemini-2.5-flash-image
```

Rules:

- No Pro models by default.
- No search grounding by default.
- No multi-variant generation in the live demo.
- Log model names and elapsed time.
- Never log API keys.

## Required Outputs

You produce:

```text
cache/scene_index.json
manifests/plan.json
assets/tts/*.wav
assets/backgrounds/*.png
manifests/critic_suggestions.json
logs/gemini_calls.jsonl
```

The renderer consumes these as files. It should not know Gemini exists.

## Work Plan

### Step 1: Gemini client wrapper

Create:

```text
backend/app/integrations/gemini/client.py
backend/app/integrations/gemini/settings.py
backend/app/integrations/gemini/service.py
```

Settings:

```text
GEMINI_API_KEY
GEMINI_TEXT_MODEL
GEMINI_TTS_MODEL
GEMINI_IMAGE_MODEL
GEMINI_ENABLE_GROUNDING
GEMINI_MAX_OUTPUT_TOKENS
```

### Step 2: Prompt files

Create:

```text
backend/app/prompts/scene_analysis.md
backend/app/prompts/plan_generation.md
backend/app/prompts/narration.md
backend/app/prompts/background_plate.md
backend/app/prompts/blind_manifest_critic.md
```

### Step 3: Scene analysis

Function:

```text
analyze_scenes(project_path) -> cache/scene_index.json
```

Use structured output. Return JSON matching `docs/API_AND_DATA_CONTRACTS.md`.

### Step 4: Plan generation

Function:

```text
generate_plan(project_path) -> manifests/plan.json
```

Use structured output. Constrain narration:

```text
Narration must not exceed 2 words per second of allocated clip duration.
```

### Step 5: TTS generation

Function:

```text
generate_tts(project_path) -> assets/tts/*.wav
```

Use `gemini-2.5-flash-preview-tts` by default.

After each WAV is written:

- Ask Dev 3's renderer utility to measure duration, or implement a local helper that can later be replaced.
- Store exact `tts_duration` where manifest build can consume it.

### Step 6: Background plates

Function:

```text
generate_background_assets(project_path) -> assets/backgrounds/*.png
```

Prompt must include:

```text
No text, no letters, no logos.
```

Use `gemini-2.5-flash-image` by default. Do not use Nano Banana Pro in the MVP path.

### Step 7: Blind manifest critic

Function:

```text
precritique_manifest(project_path) -> manifests/critic_suggestions.json
```

Critic input:

```text
cache/scene_index.json
manifests/block_manifest.json
```

Critic prompt must include:

```text
You are reviewing a text-based edit manifest, not the video itself.
Only critique narrative flow, pacing, ordering, duration, missing context, and obvious manifest problems.
Do not critique lighting, framing, acting, camera quality, or visual aesthetics.
Do not suggest trimming more than 30% of a block's current duration.
Do not suggest edits that violate block duration constraints.
Return JSON only.
```

### Step 8: Logging

Append sanitized metadata:

```text
logs/gemini_calls.jsonl
```

Fields:

```text
timestamp
project_id
stage
model
elapsed_ms
input_token_count
output_token_count
artifact_path
error
```

## Tests You Own

Create tests for:

```text
default model settings are cheap
Pro models are not used by default
scene response parses as JSON
plan response parses as JSON
critic response parses as JSON
critic prompt contains blind constraints
background prompt forbids text
narration prompt enforces 2 words per second
Gemini call logger redacts API keys
```

Run:

```bash
pytest tests/backend/integrations tests/backend/prompts -q
```

## Do Not Touch

```text
apps/web/**
backend/app/api/**
backend/app/jobs/**
backend/app/projects/**
backend/app/manifests/**
backend/app/rendering/**
samples/**
```

## Agent Prompt For Your Coding Agent

```text
You are Dev 4, Gemini Integration Lead for DirectorLoop. Work only in backend/app/integrations, backend/app/prompts, backend/app/assets, tests/backend/integrations, and tests/backend/prompts. Implement Gemini client wrappers, cheap model defaults, structured-output parsing, scene analysis, plan generation, TTS WAV generation, textless background generation, blind manifest critique, and sanitized Gemini logging. Do not edit frontend, API orchestration, manifest validation, rendering, or sample fixtures.
```


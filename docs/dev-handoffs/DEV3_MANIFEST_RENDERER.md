# Dev 3 Handoff: Manifest Validation and FFmpeg Renderer

## Role

Rendering Lead. Your job is to make the manifest deterministic and the render path boring, reliable, and demo-safe.

## Write Scope

You own:

```text
backend/app/manifests/**
backend/app/rendering/**
tests/backend/manifests/**
tests/backend/rendering/**
```

You are also the owner of schema decisions. Other devs should consume your public models instead of duplicating contracts.

## Product Goal

Given a valid `block_manifest.json`, render each block as a normalized MP4 and concatenate them into `renders/final_render.mp4`.

## Required Manifest Rules

- All paths are project-relative.
- `block_id` values are unique.
- Title/text blocks require `fontfile`.
- `assets/fonts/Inter-Bold.ttf` must exist before rendering text blocks.
- Source clip duration is `source_end - source_start`.
- If `tts_duration > video_duration`, update `source_end` before writing the manifest.
- Critic trims cannot exceed 30 percent of a block duration.
- Rejected suggestions do not alter the manifest.

## Work Plan

### Step 1: Manifest models

Create:

```text
backend/app/manifests/models.py
```

Models:

```text
RenderSettings
TitleBlock
SourceClipBlock
EndCardBlock
BlockManifest
CriticSuggestion
CriticSuggestions
ApplyPatchesRequest
```

Use Pydantic discriminated unions for block types if the codebase supports it cleanly.

### Step 2: Manifest service

Create:

```text
backend/app/manifests/service.py
```

Functions:

```text
load_scene_index(project_path)
load_plan(project_path)
load_manifest(project_path)
write_manifest(project_path, manifest)
build_manifest(project_path)
reconcile_durations(manifest)
apply_approved_patches(project_path, request)
```

### Step 3: Duration reconciliation

Implement exactly:

```python
video_duration = source_end - source_start

if tts_duration > video_duration:
    source_end = source_start + tts_duration
```

After reconciliation:

```text
video_duration == source_end - source_start
video_duration >= tts_duration
```

### Step 4: Renderer command builder

Create:

```text
backend/app/rendering/commands.py
```

Functions:

```text
build_title_block_command(project_path, block, settings)
build_source_clip_command(project_path, block, settings)
build_concat_command(project_path, manifest)
```

Do not execute commands in the command builder. Return argument arrays for safe subprocess usage.

### Step 5: Renderer service

Create:

```text
backend/app/rendering/service.py
```

Functions:

```text
check_ffmpeg_available()
render_block(project_path, block, settings)
render_project(project_path, progress_callback=None)
write_concat_file(project_path, manifest)
probe_render(path)
```

### Step 6: FFmpeg normalization

Every block should normalize to:

```text
1920x1080
30 fps
libx264
aac
48000 Hz audio
yuv420p
```

Use one complete MP4 per block. Never build one giant multi-block filtergraph.

### Step 7: Final concat

Write:

```text
concat.txt
```

Content:

```text
file 'blocks/001_title.mp4'
file 'blocks/002_demo.mp4'
file 'blocks/003_end.mp4'
```

Then create:

```text
renders/final_render.mp4
```

## Tests You Own

Create tests for:

```text
fixture manifests validate
duplicate block ids fail
missing font fails title validation
duration reconciliation extends source_end
critic trims above 30 percent fail
approved patch applies
rejected patch is ignored
title command includes fontfile
source command includes TTS input when present
concat file has one line per block
smoke render passes when ffmpeg exists
```

Run:

```bash
pytest tests/backend/manifests tests/backend/rendering -q
```

## Do Not Touch

```text
apps/web/**
backend/app/api/**
backend/app/jobs/**
backend/app/projects/**
backend/app/integrations/**
backend/app/prompts/**
```

## Agent Prompt For Your Coding Agent

```text
You are Dev 3, Manifest and Rendering Lead for Scenerio. Work only in backend/app/manifests, backend/app/rendering, tests/backend/manifests, and tests/backend/rendering. Implement Pydantic manifest contracts, duration reconciliation, critic patch validation, FFmpeg command builders, block rendering, concat demuxer output, and ffprobe smoke checks. Do not call Gemini and do not edit frontend or API orchestration.
```


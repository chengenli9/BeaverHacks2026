# API and Data Contracts

## API Conventions

Base URL during development:

```text
http://localhost:8000
```

All job creation endpoints return immediately:

```json
{
  "job_id": "job_001",
  "status": "queued"
}
```

All artifact endpoints return JSON except the final render endpoint, which returns either a file response or a JSON object containing a local URL/path the frontend can load.

## Job Status

```json
{
  "job_id": "job_render_001",
  "project_id": "demo_project",
  "status": "running",
  "stage": "rendering_blocks",
  "progress": 0.6,
  "message": "Rendering block 3 of 5",
  "error": null,
  "created_at": "2026-05-02T20:00:00Z",
  "updated_at": "2026-05-02T20:00:05Z"
}
```

Allowed `status` values:

```text
queued
running
succeeded
failed
cancelled
```

## Scene Index

File:

```text
cache/scene_index.json
```

Contract:

```json
{
  "project_id": "demo_project",
  "source": "source/demo_footage.mp4",
  "source_duration": 42.0,
  "scenes": [
    {
      "scene_id": "scene_001",
      "start": 0.0,
      "end": 8.0,
      "summary": "Opening shot of the team explaining the project.",
      "visual_tags": ["team", "intro", "talking-head"],
      "audio_notes": "Clear speech with light room noise",
      "demo_relevance": 0.8
    }
  ]
}
```

Rules:

- `end` must be greater than `start`.
- Scene ranges must be within `source_duration`.
- `demo_relevance` is a float from `0.0` to `1.0`.

## Plan

File:

```text
manifests/plan.json
```

Contract:

```json
{
  "project_id": "demo_project",
  "title": "Scenerio Demo Cut",
  "target_duration": 30.0,
  "story_arc": [
    "Name the problem",
    "Show the pipeline",
    "Show the rendered result"
  ],
  "beats": [
    {
      "beat_id": "beat_001",
      "type": "title",
      "goal": "Brand the demo instantly",
      "scene_id": null,
      "duration": 3.0,
      "narration": null,
      "onscreen_text": "Scenerio"
    },
    {
      "beat_id": "beat_002",
      "type": "source_clip",
      "goal": "Show the workflow problem",
      "scene_id": "scene_001",
      "duration": 6.5,
      "narration": "Raw footage becomes a structured edit plan in seconds.",
      "onscreen_text": null
    }
  ]
}
```

Rules:

- `duration` must be positive.
- Source beats must reference known scenes.
- Narration must respect 2 words per second of allocated duration.

## Block Manifest

File:

```text
manifests/block_manifest.json
```

Contract:

```json
{
  "project_id": "demo_project",
  "version": 1,
  "render_settings": {
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "video_codec": "libx264",
    "audio_codec": "aac",
    "sample_rate": 48000,
    "pixel_format": "yuv420p"
  },
  "blocks": [
    {
      "block_id": "001_title",
      "type": "title",
      "background_asset": "assets/backgrounds/bg_001.png",
      "text": "Scenerio",
      "duration": 3.0,
      "fontfile": "assets/fonts/Inter-Bold.ttf",
      "rendered_path": "blocks/001_title.mp4"
    },
    {
      "block_id": "002_demo",
      "type": "source_clip",
      "source": "source/demo_footage.mp4",
      "source_start": 12.0,
      "source_end": 18.5,
      "video_duration": 6.5,
      "tts_asset": "assets/tts/tts_002.wav",
      "tts_duration": 5.8,
      "source_audio_volume": 0.15,
      "tts_fade_seconds": 0.5,
      "rendered_path": "blocks/002_demo.mp4"
    }
  ]
}
```

Rules:

- `block_id` must be unique.
- Every path is project-relative.
- `fontfile` is required for text/title blocks.
- `video_duration` must equal `source_end - source_start` after reconciliation.
- If `tts_duration > video_duration`, increase `source_end` before writing the manifest.
- `source_audio_volume` must be between `0.0` and `1.0`.

## Critic Suggestions

File:

```text
manifests/critic_suggestions.json
```

Contract:

```json
{
  "project_id": "demo_project",
  "critic_scope": "blind_manifest_only",
  "suggestions": [
    {
      "suggestion_id": "s001",
      "block_id": "002_demo",
      "action": "trim_end",
      "amount_seconds": 1.0,
      "max_allowed_trim_seconds": 1.95,
      "reason": "The block appears to continue after the narration ends.",
      "requires_approval": true
    }
  ]
}
```

Allowed actions for MVP:

```text
trim_end
extend_end
reorder_after
replace_text
lower_source_audio
```

Rules:

- Suggestions are advisory until approved.
- `requires_approval` must be true for all MVP suggestions.
- Trim suggestions cannot exceed 30 percent of current block duration.
- Suggestions cannot critique visual quality because the critic is blind.

## Apply Approved Patches Request

```json
{
  "project_id": "demo_project",
  "approved_suggestion_ids": ["s001"],
  "rejected_suggestion_ids": ["s002"]
}
```

Response:

```json
{
  "job_id": "job_apply_patches_001",
  "status": "queued"
}
```

## Final Render Response

Preferred JSON response for the frontend:

```json
{
  "project_id": "demo_project",
  "render_path": "renders/final_render.mp4",
  "url": "http://localhost:8000/projects/demo_project/render/file",
  "duration": 29.7,
  "bytes": 1842042
}
```


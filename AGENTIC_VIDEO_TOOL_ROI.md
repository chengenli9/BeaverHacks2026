# Agentic Video Tool ROI Notes

Observed on 2026-05-02. This repo is already pointed in a good hackathon direction: local-first, manifest-driven, FastAPI jobs, Pydantic contracts, Gemini for structured planning, and FFmpeg for deterministic rendering. The highest-ROI improvements are not "more agents"; they are better media evidence for the agents and more useful review actions.

## Current Tool Stack Read

What is working:

- Python + FastAPI is the right backend surface for a hackathon because the media, schema, and job code are all in one language.
- Pydantic contracts in `backend/app/manifests/models.py` are a real strength. Keep making model output prove itself against these contracts.
- FFmpeg block rendering is the right choice. The repo avoids a giant filtergraph and renders normalized blocks before concat, which is much easier to debug live.
- Gemini structured JSON is a good fit for scene indexing, plan generation, narration cleanup, background prompts, and manifest suggestions.
- The frontend is correctly presenting an approval loop instead of pretending the agent can silently edit the video.

What is hurting ROI:

- The critic is "blind manifest only", so it mostly guesses from scene summaries and timings. That explains why suggestions feel bland or oddly justified.
- Scene segmentation is currently too model-dependent. `scene_index.json` can become a soft, subjective artifact instead of a measured one.
- The critic action vocabulary is narrow and uneven. It can propose `reorder_after`, but `apply_suggestions_to_manifest` does not implement it. It can lower audio, but the UI type does not expose `source_audio_volume`.
- Critique cards show the reason but not a concrete before/after, affected timestamps, confidence, or expected viewer benefit.
- The render path verifies container health, but there is no post-render quality pass for black frames, silence, unreadable title text, or narration/video mismatch.

## Highest ROI Additions

### 1. PySceneDetect for deterministic shot boundaries

ROI: very high. Cost: low.

Add PySceneDetect as a preprocessing tool before Gemini scene analysis. Use it to produce candidate shot boundaries, representative frame paths, and scene stills. Then ask Gemini to label those detected shots instead of asking Gemini to infer both boundaries and meaning from the whole video.

Why it helps:

- Gives the agent measured cut points.
- Makes scene analysis cheaper and more repeatable.
- Gives the UI useful thumbnails for scene cards.
- Gives the critic real segment evidence to refer to.

Recommended output artifact:

```text
cache/shot_index.json
cache/frames/shot_001_start.jpg
cache/frames/shot_001_mid.jpg
cache/frames/shot_001_end.jpg
```

Reference: [PySceneDetect CLI docs](https://www.scenedetect.com/cli/) and [PySceneDetect latest docs](https://www.scenedetect.com/docs/latest/).

### 2. ffprobe metadata extraction as a first-class tool

ROI: very high. Cost: very low.

The repo already uses `ffprobe` for render validation and audio detection. Promote it into a reusable media-inspection step that writes:

```text
cache/media_probe.json
```

Include duration, streams, fps, resolution, audio sample rate, rotation, and loudness-adjacent basics. Use that data in validation, UI display, and critic prompts.

Why it helps:

- Prevents the model from guessing duration and stream facts.
- Makes error messages better before rendering.
- Lets the critic flag concrete problems like "source has no audio" or "render is 8 seconds longer than manifest".

Reference: [ffprobe documentation](https://ffmpeg.org/ffprobe.html).

### 3. Speech-to-text transcript with timestamps

ROI: very high if hackathon footage has speech. Cost: medium.

Since the project already uses Python for text generation, the best next text tool is not more generation. It is transcription. Add a transcript artifact that captures what the raw footage actually says:

```text
cache/transcript.json
```

For a hackathon, the fastest path is an API transcription call or a local Whisper-family tool, depending on available keys/GPU. The transcript should include segment timestamps and, ideally, word timestamps. The plan generator can then cut around actual spoken content instead of generic scene summaries.

Why it helps:

- Enables "find the demo moment where we say X".
- Makes narration decisions less redundant with source audio.
- Lets the critic detect if TTS talks over important original speech.
- Gives the UI searchable footage.

Reference: [OpenAI speech-to-text docs](https://platform.openai.com/docs/guides/speech-to-text) and [WhisperX paper](https://arxiv.org/abs/2303.00747) for word-level timestamp alignment ideas.

### 4. A post-render critic, separate from the blind pre-critic

ROI: very high. Cost: medium.

Keep the blind critic, but demote it to "manifest lint". Add a second critic after render that can inspect the actual MP4 or sampled frames plus audio/transcript artifacts.

Suggested split:

- `precritique`: structured manifest lint before render.
- `render_qa`: deterministic media checks after render.
- `creative_review`: multimodal review using final render, sampled frames, transcript, and manifest.

This is the change most likely to make critique feel useful. The current critic is safe because it is blind, but an editor's critique is valuable precisely because it sees the finished cut.

Reference: [Gemini video understanding docs](https://ai.google.dev/gemini-api/docs/video-understanding).

### 5. Lightweight image/frame checks with Pillow or OpenCV

ROI: high. Cost: low to medium.

The repo already depends on Pillow and uses it for title-card compositing. Extend that into simple frame checks:

- sample N frames from rendered blocks with FFmpeg
- compute average brightness and contrast
- detect all-black/near-empty frames
- confirm title text has enough contrast against its background
- generate thumbnails for before/after critic cards

This avoids making the model responsible for objective QA.

### 6. Loudness and silence checks with FFmpeg filters

ROI: high. Cost: low.

Use FFmpeg filters such as `silencedetect`, `volumedetect`, or `ebur128` in a small audio-analysis command. Write:

```text
cache/audio_analysis.json
```

Then the critic can say "source audio is present but too loud under narration" with evidence, not vibes. This also makes `lower_source_audio` a much more credible suggestion.

### 7. JSON Schema / Pydantic schemas passed directly to Gemini

ROI: medium-high. Cost: low.

`complete_json` currently sets `response_mime_type="application/json"` and then parses `response.text`. That is good, but the repo can get more reliability by passing explicit response schemas derived from the Pydantic contracts for scene index, plan, and critic suggestions.

Why it helps:

- Fewer malformed or stale fields.
- Less manual normalization after generation.
- Better agent handoff between steps.

Reference: [Gemini structured output docs](https://ai.google.dev/gemini-api/docs/structured-output).

### 8. Use Python generation for text edits, not media facts

ROI: high. Cost: process change.

The repo already uses Python around text generation. The improvement is to stop asking the model to infer measurable media facts. Let Python tools produce facts, then ask the model to make editorial choices from those facts.

Good split:

- Python/FFmpeg/PySceneDetect: duration, cuts, fps, stream info, silence, thumbnails, frame stats.
- Gemini/text model: story structure, clip labels, narration wording, critique reasoning, patch proposals.
- Pydantic: validation and limits.
- Human: approvals.

## Critique Functionality Critique

The current critique approach is not useless, but it is mislabeled. It is closer to a manifest linter than an editor.

Specific issues:

- It cannot see the final render, so it cannot judge watchability.
- It cannot compare narration audio against visible footage.
- It cannot detect empty frames, awkward cuts, unreadable text, bad audio mix, or dead air.
- It has no confidence, severity, category, or evidence fields.
- It suggests micro-trims without showing the viewer-level problem.
- `reorder_after` is allowed by the model contract but deliberately not implemented in patch application.
- The UI requires all suggestions to be approved or rejected before applying, which slows iteration when suggestions are low-value.
- The sample critic reasons are weak. One says a block matches the combined scene length exactly and still suggests trimming, which undermines trust.

Better framing:

```text
Critique should answer:
1. What viewer problem will this fix?
2. What evidence did the system use?
3. What exact edit will be made?
4. What risk does the edit carry?
5. Can I preview before approving?
```

## Better Critic Contract

Replace the current thin suggestion object with an evidence-backed object:

```json
{
  "suggestion_id": "s001",
  "stage": "pre_render_manifest_lint",
  "category": "pacing",
  "severity": "medium",
  "confidence": 0.74,
  "block_id": "003_beat_003",
  "time_range": { "start": 8.0, "end": 11.0 },
  "viewer_problem": "The demo beat repeats the same visual state without adding new information.",
  "evidence": [
    "shot_003 and shot_004 have near-identical labels",
    "no transcript segment is attached",
    "block duration is 3.0s with no narration"
  ],
  "action": "trim_end",
  "amount_seconds": 0.6,
  "before_summary": "3.0s source clip",
  "after_summary": "2.4s source clip",
  "risk": "May make the transition feel abrupt",
  "requires_approval": true
}
```

This would make the UI card immediately more helpful without requiring a full nonlinear editor.

## Better Critic Pipeline

Recommended hackathon pipeline:

```text
1. inspect-media
   -> cache/media_probe.json

2. detect-shots
   -> cache/shot_index.json + thumbnails

3. transcribe
   -> cache/transcript.json

4. analyze-scenes
   -> Gemini labels measured shots using thumbnails, transcript, and probe data

5. generate-plan
   -> Gemini creates beat plan from measured evidence

6. build-manifest
   -> Python reconciles duration and assets

7. precritique
   -> manifest lint only

8. render
   -> FFmpeg blocks + final MP4

9. render-qa
   -> Python checks black frames, duration, streams, silence, text contrast

10. creative-review
   -> Gemini reviews sampled final render evidence and proposes backed edits
```

## Current Tools Worth Improving Instead Of Replacing

### FFmpeg

Keep it. Improve it with reusable probe/analyze commands, progress parsing, per-block thumbnails, and audio loudness analysis.

### Pillow

Keep it. It is already solving Windows drawtext pain. Improve title layout with wrapping, safe margins, dynamic font sizing, and contrast checks.

### Gemini

Keep it, but narrow its job. Gemini should be the editorial brain over measured artifacts, not the source of truth for timings, stream metadata, or objective QA.

### Pydantic

Lean harder into it. Add schemas for `media_probe`, `shot_index`, `transcript`, `render_qa`, and richer critic suggestions.

### Frontend critic UI

Improve before adding a complex timeline. Add categories, severity, confidence, evidence chips, affected time range, and "apply selected" rather than requiring every suggestion to be decided.

## Low ROI Or Risky For This Hackathon

- Full timeline editor: impressive but too much scope.
- Cloud storage/auth/accounts: not needed for judging the core idea.
- Celery/Redis: useful later, not needed for a local demo.
- MoviePy as the main renderer: convenient Python API, but this repo already has a more transparent FFmpeg renderer. MoviePy can be a helper for prototypes, not the core render path.
- Multi-agent orchestration framework: likely more ceremony than value. The artifacts already form the agent handoff protocol.
- Generating many background variants: expensive and mostly irrelevant to the agentic editing claim.

## Recommended Implementation Order

1. Add `inspect-media` with `ffprobe` JSON output.
2. Add PySceneDetect shot detection and thumbnails.
3. Add transcript extraction if footage includes speech.
4. Rewrite critic output around evidence, category, severity, confidence, and viewer problem.
5. Add post-render QA checks before creative review.
6. Add a multimodal post-render creative review only after deterministic QA exists.

The north star: make every model call consume better evidence and produce a patch the user can understand, preview, and trust.


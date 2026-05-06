# Scenerio Commercial Architecture Proposal

> Formerly DirectorLoop / BeaverHacks2026.  
> Goal: evolve the 24-hour hackathon prototype into a real commercial AI video-editing product.

This document is intentionally forward-looking. It does **not** criticize the hackathon architecture for what it was — it was the right shape for shipping fast. Instead, it separates:

1. What is worth preserving.
2. What was a hackathon shortcut.
3. What the commercial architecture should become.
4. Which features would make Scenerio meaningfully differentiated.
5. Which low-hanging fixes should happen first.

---

## 1. Executive Summary

Scenerio’s strongest idea is not “AI generates a video.” Its strongest idea is:

> **An AI-native, manifest-driven video editor where every step is inspectable, editable, cacheable, and reviewable.**

The current architecture already has a valuable spine:

```text
Source media
  → scene/video analysis
  → editable plan
  → block manifest
  → rendered timeline
  → AI critic / patch loop
```

That should stay. The commercial product should not throw away the manifest architecture. Instead, it should harden it into a production-grade media graph with durable state, parallel workers, semantic asset indexing, provider abstraction, and export/import compatibility with real editing workflows.

The biggest strategic recommendation:

> **Scenerio should become an AI assistant sitting on top of a real timeline/media graph, not a one-shot video generator.**

A one-shot generator competes directly with Runway, Pika, Veo, CapCut, and every foundation-model UI. A timeline-native assistant that can ingest arbitrary media, understand it, search it, propose edits, render previews, export to professional formats, and preserve human control is a more defensible product.

---

## 2. Current Architecture Scan

### 2.1 Backend

Current backend stack:

- FastAPI API server.
- File-system project storage under `projects/`.
- Pydantic models for scene indexes, plans, manifests, blocks, audio tracks, critic suggestions.
- Gemini integration for scene analysis, plan generation, image generation, TTS, render review, and plan editing.
- FFmpeg for source clip extraction, image card rendering, concat, and audio overlay.
- Remotion bridge for animated text/card scenes.
- In-memory job store with FastAPI `BackgroundTasks`.

Key backend files:

- `backend/app/api/routes.py` — API surface and job enqueueing.
- `backend/app/manifests/models.py` — core domain model.
- `backend/app/manifests/service.py` — plan → manifest conversion and plan mutations.
- `backend/app/integrations/gemini/service.py` — all AI calls.
- `backend/app/rendering/service.py` — block render loop, render cache, concat, audio overlay.
- `backend/app/rendering/commands.py` — FFmpeg command construction.
- `backend/app/rendering/remotion_bridge.py` — Node/Remotion subprocess bridge.
- `backend/app/projects/service.py` — project CRUD and media import.
- `backend/app/jobs/runner.py` / `store.py` — minimal background jobs.

### 2.2 Frontend

Current frontend stack:

- React 19 + Vite.
- Context + `useReducer` store in `pipelineStore.ts`.
- Polling-based job updates.
- Three-panel editor layout:
  - media browser,
  - center player/plan/manifest tabs,
  - output/chat/critic panel,
  - bottom timeline.
- Optimistic reorder/delete.
- Preview-then-apply AI plan editing with visual diff.

Key frontend files:

- `apps/web/src/api/scenerioApi.ts` — typed API client.
- `apps/web/src/state/pipelineStore.ts` — global application state and job poller.
- `apps/web/src/components/CenterPanel.tsx` — player, scenes, plan, manifest UI.
- `apps/web/src/components/Timeline.tsx` — timeline UI.
- `apps/web/src/components/ChatPanel.tsx` — AI edit chat.
- `apps/web/src/components/DiffReviewBar.tsx` — proposed-plan accept/reject UX.

### 2.3 What is already good

Preserve these patterns:

1. **Manifest-driven editing**
   - Plan and manifest are separate. Good.
   - The plan captures creative intent; the manifest captures deterministic render instructions.

2. **Typed domain models**
   - Pydantic discriminated unions for block types are the correct foundation.
   - This enables validation, migration, UI generation, and provider-safe contracts.

3. **Block-level render caching**
   - Content-addressed block cache is exactly the right idea.
   - Reorder/delete should stay deterministic and avoid unnecessary AI calls.

4. **Preview-then-apply AI edits**
   - AI suggestions should not silently mutate the timeline.
   - The diff approval UX is a major product strength.

5. **Critic/reviewer loop**
   - Render → critique → suggested patches is a differentiated workflow.
   - This can evolve into multi-agent creative review.

6. **Fallback rendering**
   - Remotion → Pillow/FFmpeg fallback was pragmatic and should remain as a reliability layer.

---

## 3. Hackathon Shortcuts to Replace

These were reasonable in 24 hours, but should not survive into a commercial architecture.

### 3.1 File-based persistence

Current:

- Projects live as folders and JSON files.
- Jobs live in an in-memory dictionary.
- Artifacts live as scattered local files.

Commercial issue:

- No multi-user isolation.
- No queryability.
- No transaction boundaries.
- No safe concurrent writes.
- No horizontal scaling.
- Server restart loses job state.

Replace with:

- PostgreSQL for durable metadata.
- Object storage for media/artifacts.
- Redis only for ephemeral cache/locks, not source-of-truth state.
- Versioned artifact manifests.

### 3.2 FastAPI `BackgroundTasks`

Current:

- Long-running work executes through FastAPI background tasks.
- No durable queue.
- No cancellation.
- No retry policy.
- No worker isolation.

Commercial issue:

- Renders, model calls, and media analysis are long-running, failure-prone workflows.
- Users need resumability and observability.

Replace with:

- **Temporal** for the core pipeline workflow.
- Optional Celery/Dramatiq for simple fire-and-forget tasks.

Recommended:

```text
FastAPI API server
  → creates workflow/run in Temporal
  → Temporal orchestrates activities
      - media probing
      - chunking
      - model calls
      - asset generation
      - block rendering
      - final assembly
      - review
  → workers execute activities
  → frontend receives progress through SSE/WebSocket
```

Why Temporal over Celery for this product:

- Video creation is a stateful workflow, not a single job.
- Needs retries, timeouts, compensation, child workflows, cancellation, progress, and resume-after-crash.
- Temporal gives workflow history and observability.
- Celery is simpler but pushes retry/idempotency logic into application code.

A reasonable staged path:

1. MVP production: Dramatiq/Celery + Redis/RabbitMQ.
2. Serious beta/commercial: Temporal.
3. Large scale: Temporal + autoscaled GPU/CPU worker pools.

### 3.3 Single-provider AI integration

Current:

- Gemini is deeply embedded as the analysis/planning/image/TTS/review provider.

Commercial issue:

- Vendor lock-in.
- Cost volatility.
- Model outages break the product.
- Different providers are best at different tasks.

Replace with provider interfaces:

```python
class VideoUnderstandingProvider:
    def analyze(video_refs, prompt, schema): ...

class TextReasoningProvider:
    def complete_json(prompt, schema): ...

class ImageGenerationProvider:
    def generate(prompt, style, size): ...

class SpeechProvider:
    def synthesize(text, voice, timing_hints): ...

class EmbeddingProvider:
    def embed_video_chunk(video_ref): ...
    def embed_text(query): ...
```

Provider registry examples:

- Video understanding:
  - Gemini 2.5/3.x video models.
  - GPT-4o / GPT-5-class multimodal models.
  - Claude multimodal where video frame extraction is acceptable.
  - Qwen-VL local/self-hosted for lower-cost extraction.

- Embeddings:
  - Gemini Embedding for native video embeddings.
  - Qwen3-VL-Embedding local.
  - CLIP/SigLIP-derived frame embeddings for fallback.

- Image generation:
  - Gemini/Imagen.
  - Flux.
  - OpenAI Images.
  - FAL/Replicate hosted models.
  - Local ComfyUI where available.

- TTS/STT/audio:
  - ElevenLabs.
  - OpenAI TTS/STT.
  - Google Cloud TTS/STT.
  - Whisper/faster-whisper local.
  - Lyria or similar music generation when available.

### 3.4 Polling-based frontend updates

Current:

- Frontend polls job status every second.

Replace with:

- SSE for job progress and artifact readiness.
- WebSocket only where bidirectional live collaboration is needed.
- Keep polling as fallback.

Recommendation:

- Use **SSE first** for pipeline progress because it is simpler, reliable, and server-to-client only.
- Use **WebSockets/Yjs** later for collaborative timeline editing.

### 3.5 Monolithic global frontend store

Current:

- One giant React reducer owns everything.

Commercial issue:

- Re-renders scale poorly.
- Complex state transitions become fragile.
- Collaboration and offline editing become hard.

Replace with:

- Server-state cache: TanStack Query.
- Timeline/editor state: Zustand or Jotai.
- Collaborative document state: Yjs later.
- Derived selectors for timeline, artifact availability, and job status.

---

## 4. Proposed Commercial Architecture

### 4.1 High-level system

```text
                         ┌─────────────────────────┐
                         │        Web App          │
                         │ React timeline editor   │
                         │ Chat + diff review      │
                         └───────────┬─────────────┘
                                     │ HTTPS + SSE/WS
                                     ▼
┌────────────────────────────────────────────────────────────────┐
│                         API Layer                              │
│ FastAPI / typed REST / auth / project permissions / billing    │
└───────────────┬────────────────────────────┬───────────────────┘
                │                            │
                ▼                            ▼
      ┌──────────────────┐        ┌────────────────────┐
      │   PostgreSQL     │        │ Object Storage      │
      │ users/projects   │        │ source media        │
      │ timeline graph   │        │ proxies/renders     │
      │ jobs/artifacts   │        │ generated assets    │
      └──────────────────┘        └────────────────────┘
                │                            │
                └────────────┬───────────────┘
                             ▼
                  ┌─────────────────────┐
                  │ Temporal Workflows   │
                  │ pipeline orchestration│
                  └──────────┬──────────┘
                             │
      ┌──────────────────────┼──────────────────────┐
      ▼                      ▼                      ▼
┌──────────────┐      ┌──────────────┐      ┌────────────────┐
│ CPU Workers  │      │ GPU Workers  │      │ AI API Workers │
│ ffprobe      │      │ local models │      │ Gemini/OpenAI  │
│ chunking     │      │ image/video  │      │ ElevenLabs     │
│ FFmpeg       │      │ rendering    │      │ batch jobs     │
└──────────────┘      └──────────────┘      └────────────────┘
      │                      │                      │
      └──────────────────────┼──────────────────────┘
                             ▼
                    ┌────────────────┐
                    │ Artifact Index │
                    │ metadata +     │
                    │ vector DB      │
                    └────────────────┘
```

### 4.2 Core data model shift

Current model:

```text
Project → SceneIndex → Plan → Manifest → Render
```

Commercial model:

```text
Workspace
  → Project
    → MediaAsset[]
      → MediaAnalysis[]
      → EmbeddingChunk[]
    → TimelineDocument
      → Tracks[]
      → Clips[]
      → Blocks[]
      → Effects[]
      → Captions[]
      → Audio[]
    → PlanProposals[]
    → RenderJobs[]
    → Exports[]
```

The current `Plan` and `BlockManifest` can become views over this richer timeline graph.

Recommended split:

- **TimelineDocument**: canonical editable source of truth.
- **PlanProposal**: AI-generated edit intent / suggested changes.
- **RenderManifest**: deterministic render instructions generated from timeline.
- **ArtifactManifest**: references to files, previews, generated assets, and cache entries.

This prevents the AI plan from becoming the only timeline representation.

### 4.3 Timeline graph

A commercial timeline should support:

- Multiple video tracks.
- Multiple audio tracks.
- Nested sequences.
- Clip-level trims.
- Speed ramps.
- Transitions.
- Captions/subtitles.
- Generated images/videos.
- Text layers.
- Adjustment/effect layers.
- Keyframes.
- Asset references.
- User edits independent from AI suggestions.

Suggested simplified JSON shape:

```json
{
  "timeline_id": "tl_123",
  "version": 17,
  "duration": 92.4,
  "tracks": [
    {
      "track_id": "v1",
      "kind": "video",
      "clips": [
        {
          "clip_id": "clip_001",
          "asset_id": "asset_source_a",
          "timeline_start": 0,
          "duration": 6.2,
          "source_start": 34.1,
          "source_end": 40.3,
          "effects": [],
          "metadata_ref": "analysis_chunk_42"
        }
      ]
    }
  ]
}
```

The current block manifest can be generated from this for rendering.

---

## 5. Pipeline Architecture

### 5.1 Current pipeline

```text
Import
  → analyze-scenes
  → generate-plan
  → generate-tts
  → generate-assets
  → build-manifest
  → render
  → review-render
```

### 5.2 Commercial pipeline

```text
Import media
  → probe media
  → generate proxy files
  → chunk media
  → analyze chunks
  → transcribe audio
  → embed chunks
  → index media library
  → generate / update timeline proposal
  → user accepts/rejects changes
  → render preview
  → render final
  → AI review
  → publish/export
```

Critical change:

> Analysis should be asset-centric and cached. Plan generation should consume cached analysis, not repeatedly reprocess source videos.

### 5.3 Threading and parallelism plan

The user’s brainstorm said: “Thread the heck out of this.” Correct. The biggest speedups are obvious.

#### Parallelize media analysis

Current likely bottleneck:

- Analyze multiple files sequentially.
- Upload/process entire video through Gemini.

Commercial approach:

1. Generate low-resolution proxies.
2. Split each video into chunks.
3. Process chunks in parallel.
4. Cache every chunk analysis by content hash.
5. Merge chunk summaries into video-level summaries.

```text
video.mp4
  → proxy_480p_5fps.mp4
  → chunks:
      chunk 000: 00:00-00:30
      chunk 001: 00:25-00:55
      chunk 002: 00:50-01:20
  → parallel analysis + embeddings
  → Chroma/pgvector index
  → scene/object/action/transcript cache
```

#### Parallelize TTS

Current:

- TTS per beat is sequential.

Commercial:

- Run all TTS jobs concurrently with provider-specific rate limits.
- Cache by `(provider, voice, normalized_text, style, speed)` hash.
- Precompute duration and waveform metadata.

#### Parallelize image generation

Current:

- Background/image cards generated sequentially.

Commercial:

- Fan out image-generation jobs.
- Cache by prompt/style/model/seed/aspect ratio.
- Generate multiple candidates for hero assets.
- Allow user selection.

#### Parallelize block rendering

Current:

- Blocks render sequentially.

Commercial:

- Render independent blocks concurrently.
- Use content-addressed cache.
- Use worker pool sized by CPU/GPU capacity.
- Concatenate only changed ranges when possible.

```text
Timeline change touches blocks 4, 8, 9
  → reuse cached blocks 1-3, 5-7, 10+
  → render blocks 4/8/9 in parallel
  → concat via stream copy
```

#### Use Batch API where latency is less important

Gemini Batch API is useful for:

- Large media-library analysis.
- Bulk transcription/summarization.
- Chunk-level tagging.
- Offline review passes.
- Nightly re-indexing.

Do **not** use batch where the user expects an immediate chat response.

Recommended policy:

- Interactive edits: low-latency online model API.
- Background library ingestion: Batch API, lower cost.
- Re-analysis of uploaded folders: Batch API.
- Long-form report generation: Batch API if asynchronous.

---

## 6. Semantic Video Search and Media Library

This may be the highest-leverage feature.

User idea:

> “Scan/do feature extraction on videos, cache video content, give huge repo to it, semantically select videos — use semantic video search to extract relevant sections — ssrajadh/sentrysearch.”

Yes. This is strategically important.

### 6.1 Why it matters

For a commercial editor, the hard problem is not only generating content. It is finding the right moment in a pile of raw footage.

A user should be able to say:

- “Find shots where the founder is smiling.”
- “Use the part where the robot arm fails.”
- “Find B-roll of the city at night.”
- “Find clips with high energy and no camera shake.”
- “Find the moment where someone mentions revenue.”

### 6.2 SentrySearch architecture

SentrySearch approach:

- Split videos into overlapping chunks.
- Embed each chunk using Gemini Embedding API or local Qwen3-VL.
- Store vectors in ChromaDB.
- Embed text/image query into same vector space.
- Retrieve closest chunks.
- Trim matching clip from source video.

This maps extremely well to Scenerio.

### 6.3 Scenerio implementation

Recommended storage:

- MVP/local: SQLite + ChromaDB.
- Production: PostgreSQL + pgvector, or Qdrant if vector workload becomes heavy.
- Object storage for media/proxies/chunks.

Recommended chunk metadata:

```json
{
  "chunk_id": "chunk_abc",
  "asset_id": "asset_123",
  "source_start": 125.0,
  "source_end": 155.0,
  "embedding_model": "gemini-embedding-video-v2",
  "summary": "Close-up of skateboard trick attempt; fall at end",
  "objects": ["skateboard", "helmet", "ramp"],
  "actions": ["jumping", "falling"],
  "transcript": "...",
  "quality": {
    "sharpness": 0.82,
    "motion": 0.74,
    "audio_clarity": 0.66
  }
}
```

### 6.4 Product UX

Add a “Smart Media Browser”:

- Search bar: natural-language video search.
- Results as playable clip ranges.
- One-click insert into timeline.
- “Use more like this.”
- “Avoid clips like this.”
- Filters:
  - source file,
  - person,
  - location,
  - transcript text,
  - visual similarity,
  - shot quality,
  - duration,
  - aspect ratio.

This becomes a core differentiator.

---

## 7. Multi-Track Editing and Gemini Context Problem

User idea:

> “More video tracks stacked — problem: Gemini context; find efficient way to abstract content of other tracks; possibly just pass in manifest values?”

Correct problem. Do not pass entire media context into Gemini every time.

### 7.1 Solution: timeline context compiler

Build a service that compiles only the relevant timeline context for the model.

Inputs:

- User request.
- Current selection.
- Visible time range.
- Active tracks.
- Clip summaries.
- Transcript snippets.
- Render thumbnails.
- Semantic search results.

Output:

- Compact timeline context.

Example:

```text
Current timeline around 00:35-00:55:

V3 text overlay:
- 00:38-00:44: "Built in 24 hours"

V2 generated b-roll:
- 00:34-00:40: AI image of hackathon room, slow zoom

V1 source clips:
- 00:31-00:45: asset_12, founders coding, high energy
- 00:45-00:56: asset_08, demo screen recording

A1 voiceover:
- 00:30-00:50: "We started with a pile of clips..."

Music:
- 00:00-01:20: Ascending Momentum, -18 LUFS
```

### 7.2 Context levels

Use tiered context:

1. **Manifest-level context**
   - Clip IDs, timings, block types, text, asset references.
   - Cheap and deterministic.

2. **Analysis-level context**
   - Summaries, transcripts, tags, embeddings.
   - Cached.

3. **Visual context**
   - Representative frames or thumbnails.
   - Only when needed.

4. **Full media context**
   - Expensive; only for selected clips or review passes.

### 7.3 Avoid full-context Gemini calls

Rule:

> Most timeline edits should be proposed from structured timeline metadata and cached analysis, not by sending full videos again.

---

## 8. Asset Generation Ideas

### 8.1 Green-screen generation + local keying

User idea:

> “Have nanobanana generate green screens, run them through local corridor key to get perfect key frames.”

Interpreting “nanobanana” as an image/video generation provider or internal generation step, this is a strong idea.

Workflow:

```text
Prompt: "robot mascot dancing, full body, green screen background"
  → generate subject on clean chroma background
  → run local chroma key / segmentation
  → produce transparent PNG/video alpha asset
  → insert as overlay track
```

Why this matters:

- Transparent overlays are more composable than flat generated images.
- Lets AI-generated assets behave like real editing elements.
- Works well for stickers, presenters, mascots, products, annotations.

Recommended implementation:

- Start with generated still PNGs with green/blue background.
- Use robust chroma key with OpenCV or FFmpeg `chromakey` where stable.
- Better: use segmentation models like SAM2 or RMBG for alpha extraction.
- Store as transparent PNG/WebM ProRes 4444 equivalent if video.

### 8.2 PNG → animation models

User idea:

> “PNG —> animation models..?”

Yes. This should become an `image_to_video` asset provider.

Provider interface:

```python
class ImageToVideoProvider:
    def animate(image_ref, prompt, duration, aspect_ratio, motion_strength): ...
```

Candidate providers/models:

- Wan 2.1 image-to-video via FAL/Replicate/self-hosted.
- Runway image-to-video.
- Kling image-to-video.
- Pika image-to-video.
- AnimateDiff/ComfyUI for local workflows.
- Stable Video Diffusion for self-hosted fallback.

Product usage:

- Animate title-card backgrounds.
- Turn generated storyboards into moving clips.
- Create B-roll from stills.
- Animate imported product images.
- Add subtle parallax/zoom even when full I2V is too expensive.

Recommendation:

- Start with hosted API for speed.
- Add local ComfyUI provider later for power users.
- Cache generated videos aggressively.

### 8.3 Native Veo / Lyria / TTS / STT

User idea:

> “Native Veo3/Lyria3/TTS/STT.”

Treat these as provider plugins, not core assumptions.

Capabilities:

- Video generation: Veo, Runway, Kling, Pika, Wan.
- Music generation: Lyria, Suno-like providers, local AudioCraft.
- TTS: ElevenLabs/OpenAI/Google.
- STT: Whisper/Google/OpenAI.

Product feature:

- “Generate missing shot.”
- “Replace this weak B-roll with generated clip.”
- “Generate music bed matching the emotional arc.”
- “Create voiceover from this script.”
- “Auto-caption and align transcript.”

---

## 9. Export and Interoperability

User idea:

> “Export in timeline-editable formats as well as MP4s.”

Yes. This is a commercial-grade feature.

### 9.1 Recommended formats

#### OpenTimelineIO

Best internal interchange target.

Pros:

- Designed for editorial timeline interchange.
- Python library available.
- Good match for Scenerio’s manifest/timeline model.
- Can convert to/from some other formats.

Cons:

- Not universally native in all editors without plugins/workflows.

#### FCPXML

Best for Final Cut Pro and increasingly useful for interchange.

Pros:

- XML format.
- Easier to generate than AAF.
- Supports timelines, assets, clips, audio, effects subset.

Cons:

- Final Cut’s magnetic timeline model differs from traditional tracks.
- Effects/transitions need careful mapping.

#### EDL

Simple legacy fallback.

Pros:

- Easy to generate.
- Supported by many editors.

Cons:

- Very limited.
- Mostly cuts-only.
- Weak support for multi-track/effects.

#### AAF

Professional interchange, especially for Avid/Premiere workflows.

Pros:

- Widely used in professional post.

Cons:

- Complex.
- Harder to generate correctly.
- Not the first target.

### 9.2 Recommended export roadmap

1. MP4 final render.
2. ZIP project bundle:
   - MP4,
   - source media references,
   - manifest JSON,
   - captions SRT/VTT,
   - thumbnails,
   - generated assets.
3. OpenTimelineIO `.otio`.
4. FCPXML.
5. EDL cuts-only.
6. AAF only if professional workflows demand it.

### 9.3 Internal benefit

Even before user-facing export, adopting an OpenTimelineIO-inspired internal model will improve architecture quality.

---

## 10. Google Drive and External Storage

User idea:

> “Integrate with Google Drive (see Google Drive videos/photos in GUI), see project files.”

Yes, but avoid copying huge files unnecessarily.

Recommended flow:

1. User connects Google account.
2. Scenerio lists Drive files with picker/search.
3. User selects videos/photos.
4. Scenerio imports metadata first.
5. Worker downloads or streams selected files into object storage/proxy generation.
6. Keep original Drive file ID as external source metadata.

Product UX:

- Left panel sources:
  - Local uploads.
  - Google Drive.
  - Google Photos if accessible.
  - YouTube/private channel later.
  - Existing Scenerio asset library.

Implementation details:

- Store OAuth tokens encrypted.
- Respect Drive permissions.
- Generate local proxies for editing.
- Deduplicate by file ID + checksum.

---

## 11. Deep Research / Local Asset Storage

User idea:

> “Deep research/local asset storage for in-depth reports; use gemini 3.1 pro? tbh better to just expose endpoint to existing harnesses + make it painless w a skill.”

Agree with the second half.

Do not make Scenerio itself a giant research-agent platform. Instead:

- Expose clean project/media/timeline APIs.
- Provide a first-class “agent harness” endpoint.
- Provide skills/templates for external agents to use Scenerio.

Example endpoints:

```text
GET /projects/{id}/context
GET /projects/{id}/media/search?q=...
POST /projects/{id}/timeline/propose
POST /projects/{id}/timeline/apply-proposal
POST /projects/{id}/assets/generate
```

Then a research agent can:

- Pull project context.
- Analyze market/domain/source docs.
- Generate a script.
- Search existing media for matching shots.
- Propose timeline edits.
- Leave them for user approval.

This keeps Scenerio focused as a media/timeline platform while still being agent-friendly.

---

## 12. Reviewer Should Propose New Blocks

User idea:

> “Have reviewer propose new blocks from input directory.”

This is excellent.

Current critic reviews rendered output. Commercial critic should also inspect:

- Timeline structure.
- Source media library.
- Unused high-quality clips.
- Transcript.
- Brand/style guide.
- Target platform.

Example reviewer suggestions:

- “The intro lacks visual hook. Add 2-second close-up from `clip_042` at 00:15.”
- “There is a dead-air gap at 00:37; trim 0.8s.”
- “The claim about traction would benefit from screenshot image_card using `metrics.png`.”
- “The outro should add CTA card.”
- “Clip at 00:52 is blurry; replace with semantically similar shot from `camera_b.mp4`.”

Reviewer architecture:

```text
review_render
  → visual/audio QA of output
review_timeline
  → structural critique of timeline
review_media_opportunities
  → search unused media for better shots
review_brand
  → style/brand consistency
```

All suggestions should produce typed proposals:

```json
{
  "suggestion_id": "sug_123",
  "type": "insert_clip",
  "target_time": 12.5,
  "source_asset_id": "asset_77",
  "source_start": 31.2,
  "source_end": 34.8,
  "reason": "Adds visual proof of the product working"
}
```

---

## 13. Basic Editor Features to Add

User idea ended with:

> “Add basic video-editing features that exist in other editors.”

Prioritize features that unlock real editing without exploding scope.

### 13.1 Must-have editing primitives

1. Trim clip start/end in timeline.
2. Split clip at playhead.
3. Ripple delete.
4. Multi-select clips.
5. Drag clips between tracks.
6. Snap to clip boundaries/playhead.
7. Undo/redo across all timeline edits.
8. Text overlay editing.
9. Volume per clip/track.
10. Mute/solo tracks.
11. Captions/subtitles.
12. Export captions as SRT/VTT.

### 13.2 Next layer

1. Transitions.
2. Crop/scale/position.
3. Speed changes.
4. Freeze frame.
5. Color presets/LUTs.
6. Audio fades.
7. Noise reduction integration.
8. Beat-sync cuts to music.
9. Template library.
10. Brand kit.

### 13.3 AI-native editor features

1. “Tighten pacing.”
2. “Make this more dramatic.”
3. “Find better B-roll.”
4. “Remove dead air.”
5. “Generate missing transition.”
6. “Make a TikTok cut from this long video.”
7. “Create 5 variants for A/B testing.”
8. “Apply this style to all scene cards.”
9. “Rewrite captions for clarity.”
10. “Auto-cut to transcript highlights.”

---

## 14. Product Differentiation

Scenerio should avoid becoming “another AI video generator UI.” Better positioning:

> **Scenerio is an AI-native video editor that understands your media library and proposes editable timelines.**

Differentiators:

1. **Semantic media search**
   - Find moments in raw footage by meaning.

2. **Editable AI proposals**
   - AI changes are diffs, not destructive mutations.

3. **Manifest/timeline transparency**
   - Users can inspect and modify the plan.

4. **Render critic loop**
   - AI reviews the actual output, not just the script.

5. **Provider flexibility**
   - Gemini/OpenAI/Qwen/local providers.

6. **Professional export**
   - MP4 + OTIO/FCPXML/EDL.

7. **Local/power-user mode**
   - Optional local embeddings/rendering/ComfyUI pipeline.

8. **Agent-friendly API**
   - External agents can create proposals without owning the UI.

---

## 15. Low-Hanging Fruit / Obvious Bugs / Quick Wins

These should be done before major rewrites.

### 15.1 Performance quick wins

1. Parallelize artifact hydration in frontend with `Promise.all`.
2. Parallelize TTS generation with bounded concurrency.
3. Parallelize image/background generation with bounded concurrency.
4. Parallelize independent block rendering.
5. Add model/API response caching for chat and plan edits.
6. Add duplicate-job prevention for render/review jobs.
7. Debounce or cancel stale plan-edit preview jobs.
8. Generate low-res previews before full-res renders.

### 15.2 UX quick wins

1. Rename UI/project references from DirectorLoop to Scenerio.
2. Add a “what changed?” summary after AI proposal.
3. Add progress percentages per pipeline stage.
4. Show estimated cost/time before expensive AI jobs.
5. Show cache hits: “7/9 blocks reused.”
6. Add “render preview quality” vs “render final quality.”
7. Add drag-to-trim in timeline.
8. Add split-at-playhead.
9. Add keyboard shortcuts.
10. Add source clip preview before insertion.

### 15.3 Reliability quick wins

1. Add file upload type/size validation.
2. Add project-level lock around mutating jobs.
3. Add JSON artifact version fields.
4. Add atomic writes for artifacts.
5. Add cleanup for temp/cache files.
6. Add retry with exponential backoff for model calls.
7. Add health check for FFmpeg, Remotion, Gemini key, disk space.
8. Add structured logs with job/project IDs.

### 15.4 Security quick wins

1. Add authentication before anything public.
2. Disable `allow_origins=["*"]` for production.
3. Add upload MIME/extension allowlist.
4. Serve user-uploaded files with safe content disposition.
5. Add per-user rate limits.
6. Redact internal file paths and stack traces from API errors.
7. Add project ownership checks to every endpoint.

### 15.5 Developer quick wins

1. Create Docker Compose for API + frontend + Redis/Postgres.
2. Add `.env.example`.
3. Add smoke test script for full pipeline.
4. Add tests for plan mutations and render manifest generation.
5. Add API schema docs/examples.
6. Split `gemini/service.py` into smaller modules.
7. Split `routes.py` into routers by domain.

---

## 16. Suggested Roadmap

### Phase 0: Cleanup and rename

Goal: make the current prototype coherent as Scenerio.

- Rename visible DirectorLoop references.
- Create `SCENERIO_ARCHITECTURE.md` / product docs.
- Add environment docs.
- Add smoke tests.
- Fix obvious frontend hydration/polling inefficiencies.

### Phase 1: Production foundation

Goal: safe private beta.

- PostgreSQL metadata.
- Auth and project ownership.
- Durable job queue.
- Object storage abstraction.
- Upload validation.
- Structured logging.
- SSE progress updates.
- Atomic artifact writes.

### Phase 2: Faster pipeline

Goal: make it feel good.

- Parallel TTS/image/block rendering.
- Content-addressed AI cache.
- Preview-quality render mode.
- Batch API for background analysis.
- Job cancellation.
- Render deduplication.

### Phase 3: Real media library

Goal: differentiate.

- Proxy generation.
- Chunked video analysis.
- STT/transcripts.
- Video embeddings.
- Semantic media browser.
- Reviewer proposes clips from unused media.

### Phase 4: Real timeline editor

Goal: become usable beyond demos.

- Multi-track timeline model.
- Trim/split/ripple edit.
- Captions.
- Audio controls.
- Text overlays.
- Timeline proposal diffs.
- OTIO/FCPXML export.

### Phase 5: AI asset generation platform

Goal: AI-native creative power.

- Image-to-video provider.
- Generated transparent overlays.
- TTS/STT provider registry.
- Generated music provider.
- Brand kit/style memory.
- A/B variant generation.

### Phase 6: Collaboration and teams

Goal: commercial SaaS.

- Workspaces.
- Team projects.
- Comments/review links.
- Version history.
- Yjs/CRDT collaborative timeline editing.
- Billing/usage tracking.

---

## 17. Recommended Technical Choices

### Backend

- API: FastAPI can stay.
- Database: PostgreSQL.
- Vector search: pgvector first; Qdrant if needed.
- Queue/workflows: Temporal preferred; Celery/Dramatiq acceptable interim.
- Object storage: S3-compatible abstraction; Cloudflare R2 is attractive for cost.
- Cache: Redis.
- Render workers: containerized CPU/GPU workers.
- Observability: OpenTelemetry + Sentry + structured JSON logs.

### Frontend

- React can stay.
- Server state: TanStack Query.
- Editor state: Zustand/Jotai.
- Collaboration later: Yjs.
- Timeline UI: custom canvas/SVG/DOM hybrid, or evaluate timeline-specific libraries.
- Job progress: SSE.
- Media preview: HLS/proxy files for long videos.

### AI Providers

- Text/planning: Gemini, OpenAI, Anthropic/provider abstraction.
- Video understanding: Gemini first; Qwen-VL local fallback.
- Embeddings: Gemini native video embedding + Qwen3-VL local.
- Image generation: Gemini/Imagen + Flux/FAL/Replicate.
- Image-to-video: Wan/Kling/Runway/Pika provider abstraction.
- TTS: ElevenLabs/OpenAI/Google.
- STT: Whisper/OpenAI/Google.

### Export

- Internal: Scenerio timeline JSON.
- Interchange: OpenTimelineIO.
- Pro editor: FCPXML.
- Legacy: EDL.
- Captions: SRT/VTT.
- Final: MP4/HLS.

---

## 18. Key Architectural Principle

The commercial version should be built around this rule:

> **Never do expensive AI or render work if a cached structured artifact can answer the question.**

That means:

- Analyze media once.
- Store chunk-level understanding.
- Generate timeline proposals from cached context.
- Render only changed blocks.
- Review from proxies when possible.
- Use batch APIs for non-interactive work.
- Keep every AI output as a typed, reviewable proposal.

---

## 19. Final Recommendation

Do not rewrite everything immediately.

The current architecture is a strong prototype because the core separation — scene index, plan, manifest, render, review — is right. The immediate path should be:

1. Preserve manifest-driven editing.
2. Add durable state and job orchestration.
3. Thread/parallelize the obvious slow stages.
4. Build semantic media search.
5. Expand the timeline model.
6. Add professional exports.
7. Add provider abstraction.

If Scenerio does those things, it stops being a hackathon demo and becomes a credible AI-native editing platform.

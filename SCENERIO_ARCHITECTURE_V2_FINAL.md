# Scenerio Architecture V2 — Local-First Agentic Video Editor

> Consolidated architecture after codebase inspection, research, Gemini 3.1 Pro critique passes, and latest product direction.  
> This replaces the earlier hackathon-to-product framing. Scenerio is now treated as a serious commercial product direction, not a BeaverHacks demo plan.

---

## 0. Executive Decision

Scenerio should become:

> **A local-first, agentic video editor that understands a messy media folder, selects relevant video/audio/image assets, proposes editable timeline changes, validates every manifest update, and keeps the user in control through reviewable diffs.**

It should not be:

- a one-shot text-to-video generator,
- a SaaS-first video upload platform,
- a batch processor that blindly ingests every file,
- an AI editor that silently rewrites the whole project,
- a chat app bolted onto FFmpeg.

The product should feel closer to:

```text
Premiere / Final Cut / CapCut Desktop
  + semantic media search
  + a strong agent mode
  + granular manifest/timeline tools
  + validator/checker gate after every edit
  + task-specific creative skills
```

The core promise:

> **Give Scenerio a goal and a folder of messy local media. It finds the relevant assets, proposes a rough cut as timeline diffs, lets the user approve or refine edits, and exports a polished video locally.**

---

## 1. Product Thesis

Scenerio’s strongest differentiator is not “AI generates video.” It is:

> **Reviewable AI timeline diffs over local multimodal media.**

The core product loop:

```text
Drop or link a messy local project folder
  → scan video/audio/image/document assets lightly
  → summarize what the user wants from chat/project context
  → retrieve/select relevant assets for the goal
  → lazily deepen analysis only on likely-relevant assets
  → agent proposes timeline/manifest changes through tools
  → checker validates the proposal after every update
  → user sees visual diff and rationale
  → user accepts/rejects/tweaks manually
  → reviewer suggests improvements, including unused footage/assets
  → local preview/final render
  → export MP4/captions/project bundle/timeline formats
```

The most important product ideas:

1. Local-first media/project ownership.
2. Multimodal intake: video, audio, images, later docs/scripts.
3. Selective retrieval instead of ingest-everything processing.
4. A beefier main agent mode with tool access, not fragile full-document rewrites.
5. Granular manifest/timeline edit tools.
6. Deterministic checker/validator after every AI update.
7. Reviewer agent that can search unused media and suggest missing footage.
8. Task-specific skills for short-form, trailers, tech demos, product videos, etc.
9. Lightweight helper agents for low-context tasks.
10. Real editing escape hatches: trim, split, source monitor, captions, undo/redo.

---

## 2. Target Users and Use Cases

### 2.1 Best initial ICP

Start with users who have valuable raw media but low patience for editing:

- indie founders,
- product builders,
- hackathon teams after the event,
- students making demos,
- small creators,
- event recap creators,
- technical teams making launch/pitch/demo videos.

Even though the origin was a hackathon project, the product direction is now broader: Scenerio should be a real assistant editor for anyone with messy project media.

### 2.2 Strong wedge

Positioning:

> “Don’t upload 20GB to a cloud editor. Don’t learn Premiere just to make a demo. Point Scenerio at your local folder, tell it the story, review the timeline diffs, and export.”

### 2.3 First high-value formats

Task-specific modes/skills should cover:

- short-form social cut,
- product demo,
- technical walkthrough,
- launch trailer,
- event recap,
- pitch video,
- tutorial/explainer,
- testimonial/interview edit,
- before/after transformation video,
- YouTube horizontal cut.

---

## 3. Core Architecture Overview

Recommended local-first architecture:

```text
Desktop / local web shell
  ├─ React editor UI
  ├─ local Python backend / sidecar
  ├─ local SQLite project database
  ├─ local media index + vector/text search
  ├─ local job runner
  ├─ FFmpeg / Remotion / render workers
  ├─ provider adapters for cloud/local AI
  └─ optional cloud services later
```

High-level data flow:

```text
Local files/folders
  → Asset Index
  → Derivatives: probes, proxies, thumbnails, waveforms, transcripts, OCR, captions, embeddings
  → Retrieval Packet based on user goal + chat summary
  → Main Agent Mode
      → task skill selection
      → context compiler
      → manifest/timeline edit tools
      → checker/validator after every update
      → proposal diff
  → Reviewer Agent
      → output QA
      → unused media opportunity search
      → prompt/goal alignment check
      → proposed fixes
  → Render Graph
  → Exports
```

### 3.1 Preserve from current system

The current codebase got several things right:

- typed plan/manifest models,
- manifest-driven rendering,
- AI proposal before hard mutation,
- visual diff concept,
- render critic/reviewer loop,
- render cache instinct,
- deterministic rebuilds for simple mutations,
- Remotion/Pillow/FFmpeg hybrid rendering.

Do not throw this away. Generalize it.

### 3.2 Main correction

The current `Plan → BlockManifest → Render` spine is useful, but commercial Scenerio needs a richer canonical timeline/media model underneath it.

Recommended direction:

```text
AssetIndex + TimelineDocument = canonical project state
PlanProposal = AI creative intent / proposed patches
RenderManifest = deterministic render target derived from timeline
BlockManifest = transitional/simple render target, not long-term canonical state
```

Short-term:

- keep block manifest as a derived/render artifact,
- introduce timeline/manifest patch tools around existing structures,
- compile timeline/proposal changes into the current manifest where possible.

Long-term:

- make a frame/rational-time multi-track timeline canonical,
- generate render graph/manifest from the timeline.

---

## 4. Local Project Bundle

A Scenerio project should be a portable folder/bundle, similar to a traditional editor project.

```text
MyProject.scenerio/
  project.sqlite
  project.json
  media/
    originals/              # only if copied/package mode
    external_refs.json       # linked files and fingerprints
  proxies/
    video/
    audio/
    thumbnails/
    waveforms/
  analysis/
    transcripts/
    ocr/
    captions/
    summaries/
    embeddings/
  timeline/
    timeline_v001.json
    timeline_v002.json
    proposals/
    manifest_versions/
  assets/
    generated_images/
    generated_video/
    tts/
    music/
    downloaded/
  agents/
    chat_summaries/
    task_runs/
    tool_traces/
    reviews/
  renders/
    preview/
    final/
  cache/
    ai/
    render_graph/
    remotion/
    downloads/
  exports/
    final.mp4
    captions.srt
    timeline.otio
```

### 4.1 Import modes

Scenerio should not force upload/copy of all media.

Modes:

1. **Link in place**
   - Default for local media.
   - Store original path + fingerprint.

2. **Copy into project**
   - User explicitly packages project.

3. **Proxy-only import**
   - Keep originals external; generate proxies locally.

4. **Generated/downloaded asset**
   - Store generated or web-downloaded assets under `assets/downloaded/` or generated folders.

5. **Remote reference later**
   - Drive/cloud source ID plus local proxy/cache.

---

## 5. Multimodal Asset Index

Scenerio must treat video, audio, and images as first-class media.

### 5.1 Supported asset types

Video:

- screen recordings,
- webcam takes,
- phone clips,
- B-roll,
- downloaded clips,
- generated video.

Audio:

- voiceover,
- interview audio,
- podcast/meeting recordings,
- music,
- sound effects,
- ambient sound,
- generated speech/music.

Images:

- logos,
- screenshots,
- slides,
- diagrams,
- product stills,
- thumbnails,
- brand assets,
- generated images.

Documents later:

- scripts,
- README files,
- pitch notes,
- brand guides,
- transcripts.

### 5.2 Lightweight scan first

Do not deeply ingest everything immediately.

```text
Add folder
  → enumerate supported files
  → ffprobe/image probe/basic metadata
  → fingerprint/dedupe
  → user can include/exclude/pin
  → relevance pass from filenames + metadata + existing summaries
  → only then generate proxies/transcripts/OCR/embeddings for likely assets
```

This avoids:

- slow startup,
- token waste,
- unnecessary cloud uploads,
- disk blowup,
- irrelevant footage contaminating the plan.

### 5.3 Asset index tables

SQLite tables should include:

```text
assets
  id
  media_type                 -- video | audio | image | document
  original_path
  path_type                  -- linked | copied | generated | downloaded | remote
  fingerprint
  duration
  width
  height
  sample_rate
  channels
  fps
  codec
  metadata_json
  user_status                -- included | excluded | pinned | hidden
  created_at
  updated_at

asset_derivatives
  id
  asset_id
  derivative_type            -- proxy | thumbnail | waveform | transcript | ocr | caption | embedding | summary
  path
  content_hash
  tool_or_model
  tool_or_model_version
  input_hash
  created_at

asset_segments
  id
  asset_id
  segment_type               -- shot | transcript_chunk | audio_phrase | image_region | scene | slide_region
  start_time
  end_time
  text
  summary
  tags_json
  quality_json
  embedding_id

asset_relevance_runs
  id
  project_id
  prompt_hash
  chat_summary_id
  created_at
  selected_asset_ids_json
  rejected_asset_ids_json
  uncertain_asset_ids_json
  rationale_json
```

### 5.4 Audio pipeline

```text
audio asset
  → ffprobe metadata
  → waveform JSON
  → transcript if speech
  → silence/music/speech segmentation
  → chunk summaries
  → embeddings
  → timeline-capable audio clips
```

Audio should support:

- independent trimming,
- audio-only source monitor,
- transcript editing,
- voiceover-driven video selection,
- music/SFX tracks,
- ducking/fades/loudness normalization.

### 5.5 Image pipeline

```text
image asset
  → dimensions/metadata
  → thumbnail
  → perceptual hash / duplicate detection
  → OCR if screenshot/slide
  → image caption/semantic tags
  → embeddings
  → still clip or overlay candidate
```

Images should support:

- still clips with duration,
- Ken Burns moves,
- overlays above video,
- logo/title/end-card use,
- generated animation via image-to-video provider.

---

## 6. Selective Retrieval and Relevance Selection

Before any major planning/editing call, Scenerio should build a retrieval packet.

### 6.1 Inputs to relevance

- current user prompt,
- summarized chat/project intent,
- selected task skill,
- filenames/folder names,
- media metadata,
- transcript chunks,
- OCR chunks,
- image captions,
- visual summaries,
- quality scores,
- user pins/exclusions,
- existing timeline contents,
- reviewer findings.

### 6.2 Output retrieval packet

```json
{
  "project_goal_summary": "60-second technical product demo for Scenerio",
  "task_skill": "tech_product_demo",
  "selected_assets": [
    {
      "asset_id": "asset_login_flow_mp4",
      "media_type": "video",
      "candidate_ranges": [
        {"start": 12.4, "end": 19.8, "reason": "shows requested login flow"}
      ],
      "confidence": 0.91
    },
    {
      "asset_id": "asset_logo_png",
      "media_type": "image",
      "suggested_use": "intro/outro branding",
      "confidence": 0.88
    }
  ],
  "excluded_assets": [
    {
      "asset_id": "asset_random_download",
      "reason": "low semantic match and duplicate visual content"
    }
  ],
  "uncertain_assets": [
    {
      "asset_id": "asset_ambiguous_broll",
      "reason": "possibly useful but lacks transcript/OCR signal"
    }
  ],
  "must_use": [],
  "must_not_use": []
}
```

### 6.3 Planning rule

The main agent and planner should not receive an unfiltered dump of all project assets.

They receive:

- compact project goal summary,
- relevant timeline context,
- selected asset summaries,
- candidate source ranges,
- constraints,
- skill guidance,
- available tool list.

This keeps context small and prevents the model from overfitting to irrelevant footage.

---

## 7. Chat History and Project Intent Memory

The reviewer and main agent must know what the user actually wants.

### 7.1 Store summarized chat intent

Maintain a rolling `project_intent_summary` separate from raw chat logs.

```text
chat messages
  → intent summarizer
  → project_intent_summary
  → constraints/preferences/exclusions
  → reviewer/main-agent context
```

Example:

```json
{
  "summary_id": "intent_017",
  "project_goal": "Create a serious commercial launch/demo video for Scenerio, not a hackathon recap.",
  "must_include": ["local-first", "agentic editor", "reviewable timeline diffs"],
  "must_avoid": ["SaaS-first framing", "hackathon-only language"],
  "style_preferences": ["polished", "technical but clear", "fast-paced"],
  "target_audience": ["founders", "technical creators", "small product teams"],
  "open_questions": []
}
```

### 7.2 Reviewer receives intent summary

Every reviewer pass should receive:

- current timeline/manifest summary,
- rendered preview artifacts if available,
- selected asset index / unused media opportunities,
- project intent summary,
- target platform/aspect ratio,
- task skill rubric.

The reviewer should critique against the user’s actual stated goal, not generic video quality.

---

## 8. Agent Mode Architecture

Agent Mode is the next-level Scenerio product layer.

### 8.1 Main agent

Use a beefier model for main agent mode.

The main agent should be able to:

- understand the user’s goal,
- select a task skill,
- query the media index,
- inspect timeline/manifest summaries,
- call granular manifest/timeline edit tools,
- call web/search/download tools where allowed,
- request small helper-agent tasks,
- run checker/validator after every change,
- produce a user-reviewable proposal diff.

It should not directly rewrite the entire manifest document on every request unless explicitly necessary.

### 8.2 Tool-first editing, not full-document replacement

Bad pattern:

```text
LLM receives entire manifest
  → LLM outputs entire replacement manifest
  → app hopes it still works
```

Correct pattern:

```text
LLM receives compact context
  → LLM calls typed edit tools
  → each tool modifies only relevant parts
  → checker validates current manifest/timeline
  → if checker fails, agent repairs with targeted tools
  → proposal diff shown to user
```

### 8.3 Agent loop

```text
User request
  → update project intent summary
  → choose task skill
  → compile context
  → retrieve relevant assets
  → main agent plans edits
  → tool call: patch/insert/trim/update manifest/timeline
  → checker validates
  → if fail: repair loop with error context
  → generate proposal summary + diff
  → optional reviewer pass
  → user accepts/rejects
```

### 8.4 Approval boundary

Agent mode can create proposals automatically, but applying destructive edits should still respect user control.

Modes:

1. **Suggest mode**
   - Agent only creates proposal.

2. **Agent draft mode**
   - Agent may iteratively update a draft/proposal timeline, but not overwrite accepted timeline.

3. **Autopilot within scope**
   - User grants bounded permission:
     - selected range only,
     - captions only,
     - B-roll only,
     - unlocked tracks only,
     - under cost/time limit.

4. **Never touch locked media**
   - Locked clips/tracks/ranges are enforcement constraints in validators, not just prompt text.

---

## 9. Granular Manifest and Timeline Tools

The main agent needs typed tools. These tools should be small, validated, and composable.

### 9.1 Read/query tools

```text
get_project_intent_summary()
get_timeline_summary(range?, tracks?)
get_manifest_summary(block_ids?)
get_asset(asset_id)
search_assets(query, media_types?, filters?)
search_timeline(query, range?)
get_clip_context(clip_id)
get_render_status()
get_checker_report()
```

### 9.2 Timeline/manifest edit tools

Start with tool coverage for current manifest/block model, then mirror them in the future timeline model.

```text
insert_clip(track_id, timeline_start, asset_id, source_start, source_end, options)
insert_image_clip(track_id, timeline_start, asset_id, duration, motion_preset)
insert_audio_clip(track_id, timeline_start, asset_id, source_start, source_end, volume)
insert_text_overlay(track_id, timeline_start, duration, text, style)
insert_scene_card(position, text, style)
insert_end_card(text, style)
trim_clip(clip_id, new_source_start, new_source_end)
split_clip(clip_id, at_time)
delete_clip(clip_id, ripple=false)
move_clip(clip_id, target_track_id, timeline_start)
replace_clip(clip_id, new_asset_id, source_start, source_end)
update_text(block_or_clip_id, text)
update_style(block_or_clip_id, style_patch)
update_audio_volume(clip_id, volume, fade_in?, fade_out?)
set_caption_text(caption_id, text)
add_caption_range(start, end, text, style)
lock_clip(clip_id)
lock_track(track_id)
```

### 9.3 Manifest rewrite tool

The user specifically wants the main agent to call a manifest rewrite as a tool. Keep it, but make it explicit and gated.

```text
rewrite_manifest(scope, instructions, constraints)
```

Rules:

- It writes to a proposal/draft manifest, never directly to final accepted state.
- Scope must be explicit:
  - full manifest,
  - selected blocks,
  - selected timeline range,
  - captions only,
  - audio only,
  - scene cards only.
- It must output structured diffs/change list.
- It must immediately run checker.
- It should be used only when smaller tools are insufficient.

### 9.4 Patch format

All agent edits should reduce to typed patches/proposal changes.

```json
{
  "proposal_id": "prop_123",
  "target_timeline_version": 17,
  "changes": [
    {
      "change_id": "chg_001",
      "op": "insert_clip",
      "track_id": "v1",
      "timeline_start": {"value": 300, "timescale": 30},
      "asset_id": "asset_demo_screen",
      "source_start": {"value": 900, "timescale": 30},
      "duration": {"value": 150, "timescale": 30},
      "reason": "Shows the requested dashboard proof point."
    }
  ]
}
```

---

## 10. Checker / Validator Gate

Every manifest/timeline update by the agent must go through a checker.

### 10.1 Checker stages

```text
schema validation
  → reference validation
  → timeline consistency validation
  → renderability validation
  → policy/scope validation
  → optional preview render smoke test
  → reviewer/QA pass
```

### 10.2 Required checks

Schema/reference:

- JSON/Pydantic schema valid,
- all asset IDs exist,
- all source ranges are within asset duration,
- no missing generated/downloaded files,
- no path traversal,
- no invalid media type usage.

Timeline:

- no negative durations,
- rational/frame time valid,
- clips fit allowed tracks,
- captions within timeline duration,
- audio clips have valid sample rates/channels or conversion path,
- locked clips/tracks/ranges untouched,
- proposal targets the current timeline version.

Renderability:

- FFmpeg command generation succeeds in dry-run mode,
- Remotion props validate,
- required fonts/assets exist,
- aspect ratio/export preset valid,
- captions stay in safe area if checked.

Policy:

- user cost/cloud consent respected,
- web-downloaded media has source/license metadata,
- no raw model-generated shell commands,
- no tool call outside allowed project scope.

### 10.3 Failure behavior

If checker fails:

```text
checker report
  → agent receives concise failure context
  → agent repairs with smallest relevant tool call
  → checker reruns
  → retry limit reached? surface failure to user with suggested fix
```

The user should never discover invalid manifests by rendering a broken output five minutes later.

---

## 11. Reviewer Agent

The reviewer should evolve from “critique final render” into a multi-stage quality and opportunity system.

### 11.1 Reviewer inputs

- project intent summary,
- current timeline/manifest summary,
- accepted proposal history,
- rendered preview or sampled frames,
- audio waveform/loudness report,
- captions/transcript,
- selected target format/platform,
- unused asset index/search results,
- task skill rubric.

### 11.2 Reviewer responsibilities

The reviewer can suggest:

- include other footage if relevant,
- replace weak/blurry/irrelevant clips,
- add missing proof/demo shot,
- add logo/screenshot/slide/image asset,
- insert B-roll over boring A-roll,
- tighten pacing,
- fix captions,
- adjust audio/music levels,
- add title/CTA card,
- respect target format conventions.

Example:

```json
{
  "suggestion_id": "sug_042",
  "type": "include_other_footage",
  "proposed_change": {
    "op": "insert_clip",
    "asset_id": "asset_dashboard_success_mp4",
    "source_start": 31.2,
    "source_end": 35.8,
    "timeline_start": 18.0
  },
  "reason": "The user asked to emphasize the product working, but the current cut never shows the successful dashboard state. This unused clip has OCR text matching 'Completed render'.",
  "confidence": 0.87
}
```

### 11.3 Reviewer passes

```text
review_render
  → black frames, audio clipping, text/caption issues, pacing

review_timeline
  → structure, timing, track use, missing narrative beats

review_media_opportunities
  → search unused assets for stronger clips/images/audio

review_prompt_alignment
  → compare project intent summary against current cut

review_platform_fit
  → short-form/trailer/demo conventions for target format
```

### 11.4 Reviewer outputs are proposals

Reviewer suggestions must be typed proposal changes, not vague comments.

The user can:

- accept individual reviewer suggestions,
- ask main agent to implement selected suggestions,
- reject suggestions,
- ask for alternatives.

---

## 12. Skills System for Creative Tasks

Scenerio should ship with domain/task skills that guide the main agent and reviewer.

### 12.1 What a skill contains

Each skill should define:

- ideal structure,
- pacing rules,
- typical duration,
- target platforms,
- asset selection heuristics,
- required beats,
- caption/text style,
- audio/music expectations,
- review rubric,
- forbidden/common mistakes,
- manifest/timeline edit patterns.

### 12.2 Initial skill packs

```text
short_form_social
  - hook in first 1-2 seconds
  - aggressive captions
  - fast cuts
  - vertical safe areas
  - punchy CTA

tech_product_demo
  - problem → product → proof → outcome → CTA
  - screen recordings prioritized
  - zoom/crop to UI details
  - captions explain technical value

launch_trailer
  - mood arc
  - cinematic pacing
  - title cards
  - music/beat sync
  - dramatic reveal

event_recap
  - atmosphere → people → highlights → outcome
  - variety of shots
  - music-forward
  - logos/sponsor cards

tutorial_explainer
  - clear steps
  - slower pacing
  - callouts/arrows/text overlays
  - transcript/caption accuracy prioritized

interview_testimonial
  - transcript highlight selection
  - remove filler/dead air
  - B-roll over jump cuts
  - preserve speaker authenticity
```

### 12.3 Skill selection

Agent mode should choose or ask for a skill:

```text
User: “Make this into a punchy demo for Twitter”
  → skill: short_form_social + tech_product_demo

User: “Cut a serious launch trailer”
  → skill: launch_trailer
```

The selected skill becomes part of:

- retrieval selection,
- planning prompt,
- checker expectations,
- reviewer rubric,
- export defaults.

---

## 13. Lightweight Helper Agents

The main agent can delegate small tasks to cheaper/current lightweight agents to save context and cost.

### 13.1 Delegation pattern

Main agent remains responsible for final proposal integrity. Helper agents produce bounded artifacts only.

Good helper tasks:

- summarize a long transcript,
- label candidate clips,
- find likely logo/screenshot/image assets,
- generate alternative captions,
- produce music/SFX suggestions,
- inspect one asset for relevance,
- write title-card copy variants,
- check whether a timeline range satisfies a skill rubric.

Bad helper tasks:

- directly mutate accepted timeline,
- apply changes without checker,
- make broad architectural decisions,
- download external assets without main-agent approval/scope.

### 13.2 Helper output contract

Helper agents should return structured outputs:

```json
{
  "task": "find_relevant_broll",
  "candidate_assets": [
    {
      "asset_id": "asset_17",
      "range": {"start": 14.0, "end": 19.2},
      "reason": "matches user request for team collaboration",
      "confidence": 0.82
    }
  ]
}
```

The main agent then decides whether to call edit tools.

---

## 14. Web Search and Downloaded Assets

The main agent can use the web when appropriate, but this must be explicit and tracked.

### 14.1 Allowed uses

- find public logos/brand assets,
- download royalty-free stock/photo/video when user permits,
- gather public screenshots/product references,
- research topic facts for script accuracy,
- fetch open-license media.

### 14.2 Asset record for downloads

Every web-downloaded asset needs metadata:

```text
source_url
retrieved_at
license/status
attribution
content_hash
original_filename
usage_notes
```

### 14.3 Consent and safety

- Ask/confirm when licensing is uncertain or paid media is involved.
- Never silently use copyrighted media as if it were owned.
- Store downloads under project `assets/downloaded/`.
- Run the same asset indexing pipeline as local files.

---

## 15. Timeline Model V2

The current block list is too 1D for real editing. Scenerio needs an OTIO-inspired timeline with rational/frame-based time.

### 15.1 Timeline requirements

Early:

- multiple video tracks,
- multiple audio tracks,
- image clips,
- audio-only clips,
- text overlays,
- captions,
- trim/split/ripple delete,
- clip volume/fades,
- lock/mute/solo,
- undo/redo,
- source monitor in/out.

Later:

- transitions,
- keyframes,
- nested sequences,
- speed changes,
- masks/alpha overlays,
- adjustment layers,
- effects stack.

### 15.2 Rational time example

```json
{
  "fps": {"numerator": 30000, "denominator": 1001},
  "timeline": {
    "tracks": [
      {
        "track_id": "v1",
        "kind": "video",
        "items": [
          {
            "item_id": "clip_001",
            "type": "clip",
            "asset_id": "asset_screen_recording",
            "timeline_start": {"value": 300, "timescale": 30},
            "source_start": {"value": 900, "timescale": 30},
            "duration": {"value": 150, "timescale": 30}
          }
        ]
      }
    ]
  }
}
```

### 15.3 Migration plan

Do not rewrite everything at once.

1. Keep current block manifest as render target.
2. Add proposal patch model and manifest edit tools around current blocks.
3. Add asset index that supports video/audio/image.
4. Add timeline document in parallel.
5. Compile timeline → current block manifest for simple sequences.
6. Expand renderer to support multi-track/filter graph.
7. Eventually make timeline canonical and block manifest derived.

---

## 16. Rendering Architecture

### 16.1 Short-term

Keep current FFmpeg/Remotion rendering, but add:

- proxy preview render mode,
- draft/final quality modes,
- render cache hit visibility,
- master audio bus with limiter,
- safe image/text rendering path that avoids drawtext/fontconfig problems,
- preview smoke tests in checker.

### 16.2 Long-term render graph

Move from block concat to render graph/dirty-range rendering:

```text
source/proxy decode cache
  → generated graphics cache
  → timeline segment render cache
  → audio mix cache
  → final mux/export
```

Benefits:

- only re-render changed regions,
- support overlays/transitions/PiP,
- support audio routing,
- better preview performance.

### 16.3 FFmpeg pitfalls to respect

- concat `-c copy` is fast but only works for uniform simple blocks,
- overlays/transitions require filter graphs/re-encode for affected ranges,
- audio `amix` should include limiter/loudness handling,
- text should be pre-rendered with Pillow/Remotion rather than relying on fragile drawtext/fontconfig paths.

---

## 17. AI Provider and Context Architecture

### 17.1 Provider adapters

Keep one provider per capability initially, but isolate behind adapters:

```text
TextPlanningProvider
VideoUnderstandingProvider
SpeechToTextProvider
TextToSpeechProvider
EmbeddingProvider
ImageGenerationProvider
ImageToVideoProvider
WebSearchProvider
RenderReviewProvider
```

### 17.2 Every AI call records

```text
provider
model
prompt version/hash
schema version
skill version
context compiler version
input artifact hashes
output artifact refs
latency
estimated cost
cache hit/miss
error/refusal status
```

### 17.3 Context compiler

Most agent edits should use compact structured context, not full raw media.

Context tiers:

1. Project intent summary.
2. Timeline/manifest summary.
3. Selected range/clip context.
4. Relevant asset retrieval packet.
5. Transcript/OCR/summary chunks.
6. Representative frames only when needed.
7. Full media only for dedicated analysis/review calls.

### 17.4 Prompt injection boundaries

Treat as untrusted:

- transcript text,
- OCR text,
- filenames,
- captions,
- web page text,
- downloaded metadata,
- helper-agent outputs.

Wrap in explicit boundaries and validate all outputs in code.

---

## 18. Durable Local Jobs

Replace in-memory jobs with SQLite-backed durable jobs.

```text
jobs table
  + job_events table
  + worker process/thread pool
  + cancellation tokens
  + retry policy
  + startup recovery
  + bounded concurrency
```

Important job types:

- scan_folder,
- probe_asset,
- generate_proxy,
- transcribe_asset,
- ocr_asset,
- summarize_asset,
- embed_asset_segments,
- relevance_select_assets,
- agent_propose_edits,
- checker_validate,
- review_timeline,
- render_preview,
- render_final,
- download_asset.

Concurrency rules:

- many probes in parallel,
- bounded proxy generation,
- provider calls rate-limited,
- one final render per project,
- cancel stale preview renders,
- mutating timeline/manifest jobs use project lock.

---

## 19. Export Strategy

Early exports:

1. MP4 final render.
2. 9:16, 16:9, 1:1, 4:5 presets.
3. Burned-in captions.
4. SRT/VTT sidecar.
5. Thumbnail export.
6. Project bundle zip.

Later timeline/editable exports:

1. OpenTimelineIO `.otio`.
2. FCPXML.
3. EDL cuts-only.
4. AAF only if serious professional workflows demand it.

---

## 20. Roadmap

### Phase 0 — Clean commercial direction

- Rename visible product references to Scenerio.
- Remove hackathon-only positioning from product docs/UI.
- Keep `SCENERIO_LOW_HANGING_FRUIT_CHECKLIST.md` as execution checklist.
- Add a serious demo project and no-setup demo path.

### Phase 1 — Agent-safe manifest editing

- Define proposal patch schema.
- Build manifest/timeline edit tools:
  - insert,
  - trim,
  - split,
  - delete,
  - replace,
  - update text/style/audio.
- Add manifest rewrite tool with explicit scope.
- Add checker/validator that runs after every edit.
- Add repair loop for checker failures.
- Preserve visual diff and partial accept/reject.

### Phase 2 — Multimodal asset index

- Accept/link video/audio/image files.
- Add media type detection and validation.
- Add lightweight folder scan.
- Add asset include/exclude/pin states.
- Generate thumbnails, waveforms, proxies lazily.
- Add OCR/image captions/transcripts as derivatives.

### Phase 3 — Selective retrieval

- Add search over filenames/metadata/transcripts/OCR/summaries.
- Build retrieval packet for the main agent.
- Add relevance run records and rationales.
- Let reviewer search unused media for better footage.

### Phase 4 — Real editor basics

- Source monitor.
- Set in/out points.
- Split at playhead.
- Drag trim.
- Ripple delete.
- Timeline zoom/snap.
- Undo/redo.
- Basic audio volume/fades/waveforms.

### Phase 5 — Reviewer and skills

- Project intent summarizer from chat history.
- Reviewer receives project intent summary.
- Reviewer suggests unused footage/assets where relevant.
- Add skill packs:
  - short-form,
  - tech demo,
  - launch trailer,
  - event recap,
  - tutorial,
  - interview/testimonial.

### Phase 6 — Durable local project hardening

- SQLite project database.
- Durable job runner.
- Artifact lineage/cache keys.
- Provider call logs.
- Atomic writes.
- Project locks.
- Health checks.

### Phase 7 — Timeline V2 / render graph

- Introduce frame/rational-time timeline.
- Compile timeline → current manifest initially.
- Add multi-track support.
- Add render graph / dirty range rendering.
- Add master audio bus.

### Phase 8 — Optional cloud/web/generated media

Only after the local product loop works:

- web search/download assets,
- Drive import,
- cloud batch indexing,
- cloud render acceleration,
- image-to-video generation,
- generated music/voice,
- share/review links,
- collaboration/sync.

---

## 21. What to Cut or Defer

Do not prioritize yet:

- Kubernetes/Temporal/Postgres SaaS by default,
- collaboration,
- billing,
- enterprise auth/teams,
- AAF export,
- full provider marketplace,
- generated B-roll/music as the core path,
- complete timeline rewrite before validating agent-safe manifest tools,
- cloud-only media storage,
- ingesting/analyzing every asset eagerly.

---

## 22. Final Recommendation

Scenerio’s next-level architecture should be built around this loop:

```text
Local multimodal media folder
  → lightweight asset index
  → project intent summary from chat
  → selective retrieval of relevant assets
  → skill-guided main agent mode
  → granular manifest/timeline edit tools
  → checker gate after every update
  → reviewer suggests fixes and missing footage
  → user-approved timeline diffs
  → local preview/final render
```

If Scenerio nails this, it becomes meaningfully different from one-shot AI video generators and traditional editors.

The core product is not “AI makes a video.”

The core product is:

> **An assistant editor that understands your local media library, knows what you are trying to make, and safely edits the timeline through validated, reviewable tools.**

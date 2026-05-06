# Scenerio Low-Hanging Fruit Checklist

Practical next steps for turning Scenerio into a serious local-first agentic video editor. This checklist intentionally keeps execution grounded: build the smallest useful pieces that make the product feel real.

---

## Highest-Impact First 15

1. [ ] Rename visible product references to Scenerio and remove hackathon-only framing.
2. [ ] Add folder/file intake for video, audio, and image assets.
3. [ ] Add lightweight asset scan before deep analysis.
4. [ ] Add include / exclude / pin controls for assets.
5. [ ] Add project intent summary generated from chat history.
6. [ ] Define typed proposal patch schema.
7. [ ] Build granular manifest edit tools instead of full-document rewrites.
8. [ ] Add scoped `rewrite_manifest` tool for rare broad changes.
9. [ ] Run checker/validator after every agent manifest/timeline update.
10. [ ] Show checker failures to the agent for repair, then to user if unrecoverable.
11. [ ] Add visual timeline diff + partial accept/reject per change.
12. [ ] Add source monitor with in/out points.
13. [ ] Add split-at-playhead and drag trim.
14. [ ] Add reviewer pass that can suggest unused relevant footage/assets.
15. [ ] Add first task skills: `short_form_social`, `tech_product_demo`, `launch_trailer`.

---

## 1. Product Coherence

- [ ] Rename visible `DirectorLoop` references to `Scenerio`.
- [ ] Update README title and product copy.
- [ ] Remove hackathon-only framing from user-facing materials.
- [ ] Add tagline:
  - “AI rough cuts from messy local media.”
  - “Search your footage by meaning. Approve AI edits as timeline diffs.”
- [ ] Add a known-good serious demo project with cached artifacts.

---

## 2. Multimodal Intake

Scenerio should accept more than video.

- [ ] Support video files as source assets.
- [ ] Support audio files as first-class assets:
  - [ ] voiceover,
  - [ ] interview audio,
  - [ ] music,
  - [ ] SFX,
  - [ ] meeting/podcast recordings.
- [ ] Support image files as first-class assets:
  - [ ] logos,
  - [ ] screenshots,
  - [ ] slides,
  - [ ] diagrams,
  - [ ] product stills,
  - [ ] thumbnails.
- [ ] Add media type detection.
- [ ] Add MIME/extension allowlist.
- [ ] Add file size/duration limits.
- [ ] Do not deep-analyze everything immediately.

---

## 3. Lightweight Asset Index

- [ ] Add local asset records with:
  - [ ] asset ID,
  - [ ] media type,
  - [ ] original path,
  - [ ] linked/copied/generated/downloaded mode,
  - [ ] fingerprint/hash,
  - [ ] duration/resolution/audio metadata,
  - [ ] user status: included/excluded/pinned/hidden.
- [ ] Add lightweight folder scan.
- [ ] Add duplicate detection.
- [ ] Add include/exclude/pin UI.
- [ ] Add lazy derivatives:
  - [ ] video proxy,
  - [ ] thumbnails,
  - [ ] waveform,
  - [ ] transcript,
  - [ ] OCR,
  - [ ] image caption,
  - [ ] summaries,
  - [ ] embeddings.

---

## 4. Selective Retrieval

Scenerio should select relevant assets for the goal instead of using everything.

- [ ] Generate project intent summary from chat/user prompts.
- [ ] Retrieve relevant assets from:
  - [ ] filenames,
  - [ ] folder names,
  - [ ] metadata,
  - [ ] transcripts,
  - [ ] OCR,
  - [ ] image captions,
  - [ ] summaries,
  - [ ] embeddings,
  - [ ] user pins/exclusions.
- [ ] Produce retrieval packet for agent/planner:
  - [ ] selected assets,
  - [ ] candidate ranges,
  - [ ] excluded assets,
  - [ ] uncertain assets,
  - [ ] rationales.
- [ ] Show “Scenerio found these useful assets” before/while generating proposal.
- [ ] Let user override relevance choices.

---

## 5. Agent Mode Foundation

The main agent should be a stronger model that edits through tools.

- [ ] Add agent mode entry point.
- [ ] Feed agent compact context:
  - [ ] project intent summary,
  - [ ] current timeline/manifest summary,
  - [ ] retrieval packet,
  - [ ] selected task skill,
  - [ ] user constraints.
- [ ] Add tool-call trace storage.
- [ ] Add cost/time estimate for agent jobs.
- [ ] Add scope selector:
  - [ ] whole project,
  - [ ] selected range,
  - [ ] selected clips,
  - [ ] captions only,
  - [ ] audio only,
  - [ ] B-roll only,
  - [ ] unlocked tracks only.
- [ ] Add autopilot modes:
  - [ ] suggest only,
  - [ ] draft proposal,
  - [ ] bounded autopilot.

---

## 6. Granular Manifest / Timeline Tools

Avoid rewriting the full document whenever possible.

Read/query tools:

- [ ] `get_project_intent_summary`
- [ ] `get_timeline_summary`
- [ ] `get_manifest_summary`
- [ ] `search_assets`
- [ ] `search_timeline`
- [ ] `get_clip_context`
- [ ] `get_checker_report`

Edit tools:

- [ ] `insert_clip`
- [ ] `insert_image_clip`
- [ ] `insert_audio_clip`
- [ ] `insert_text_overlay`
- [ ] `insert_scene_card`
- [ ] `trim_clip`
- [ ] `split_clip`
- [ ] `delete_clip`
- [ ] `move_clip`
- [ ] `replace_clip`
- [ ] `update_text`
- [ ] `update_style`
- [ ] `update_audio_volume`
- [ ] `set_caption_text`
- [ ] `lock_clip`
- [ ] `lock_track`

Broad tool:

- [ ] Scoped `rewrite_manifest(scope, instructions, constraints)`.
- [ ] Ensure rewrite writes only to proposal/draft state.
- [ ] Ensure rewrite immediately runs checker.

---

## 7. Checker / Validator Gate

Every agent update must pass checker.

- [ ] Schema validation.
- [ ] Asset reference validation.
- [ ] Source range validation.
- [ ] Timeline duration validation.
- [ ] Locked clip/track enforcement.
- [ ] Caption timing validation.
- [ ] Renderability dry-run.
- [ ] Remotion prop validation.
- [ ] Missing asset/font validation.
- [ ] Cloud/cost consent validation.
- [ ] No model-generated shell/FFmpeg commands.
- [ ] No path traversal.
- [ ] Checker report format for agent repair.
- [ ] Retry/repair loop with max attempts.

---

## 8. Reviewer Improvements

Reviewer should not only critique the final render. It should suggest missing/relevant assets.

- [ ] Reviewer receives project intent summary.
- [ ] Reviewer receives current timeline/manifest summary.
- [ ] Reviewer receives target skill/platform.
- [ ] Reviewer searches unused assets.
- [ ] Reviewer can suggest:
  - [ ] include other footage,
  - [ ] replace weak clip,
  - [ ] add screenshot/logo/image,
  - [ ] add missing proof/demo shot,
  - [ ] add B-roll over boring section,
  - [ ] tighten pacing,
  - [ ] fix captions,
  - [ ] adjust audio/music.
- [ ] Reviewer suggestions are typed proposal changes.
- [ ] User can accept/reject individual reviewer suggestions.

---

## 9. Skills

Add task-specific skill packs.

- [ ] `short_form_social`
  - [ ] hook in 1-2 seconds,
  - [ ] fast cuts,
  - [ ] aggressive captions,
  - [ ] vertical safe area,
  - [ ] CTA.
- [ ] `tech_product_demo`
  - [ ] problem → product → proof → outcome,
  - [ ] screen recordings prioritized,
  - [ ] zoom/crop UI details,
  - [ ] proof shots required.
- [ ] `launch_trailer`
  - [ ] mood arc,
  - [ ] title cards,
  - [ ] music pacing,
  - [ ] dramatic reveal.
- [ ] `event_recap`
- [ ] `tutorial_explainer`
- [ ] `interview_testimonial`
- [ ] Skill selected by agent from user prompt.
- [ ] Skill used by reviewer as rubric.

---

## 10. Timeline Trust Features

AI is only useful if users can fix it.

- [ ] Split clip at playhead.
- [ ] Drag trim start/end.
- [ ] Ripple delete.
- [ ] Timeline zoom.
- [ ] Snapping.
- [ ] Source monitor / source preview.
- [ ] Set in/out points.
- [ ] Insert source range into timeline.
- [ ] Undo/redo.
- [ ] Lock clip/track/range.
- [ ] Basic audio waveforms.
- [ ] Clip volume/fades.

Keyboard shortcuts:

- [ ] Space: play/pause.
- [ ] S or Cmd/Ctrl+K: split.
- [ ] Delete: delete selected clip.
- [ ] Cmd/Ctrl+Z: undo.
- [ ] Cmd/Ctrl+Shift+Z: redo.
- [ ] +/-: zoom.

---

## 11. AI Proposal UX

- [ ] AI proposal summary:
  - “Shortened intro by 4.2s, added 2 B-roll clips, rewrote 3 captions.”
- [ ] Before/after duration.
- [ ] Visual timeline diff:
  - [ ] green added,
  - [ ] red removed,
  - [ ] yellow modified,
  - [ ] blue reordered.
- [ ] Reason for each change.
- [ ] Confidence per change.
- [ ] Accept/reject individual changes.
- [ ] Revert accepted AI proposal.
- [ ] Ask follow-up from proposal.
- [ ] Show checker status on proposal.

---

## 12. Captions / Transcript MVP

- [ ] Generate transcript with timestamps.
- [ ] Show transcript synced to playhead.
- [ ] Click transcript text to seek.
- [ ] Auto-generate captions.
- [ ] Edit caption text.
- [ ] Burn captions into MP4.
- [ ] Export SRT/VTT.
- [ ] Caption style presets.
- [ ] Safe-area guides for 9:16.
- [ ] AI commands:
  - [ ] remove filler words,
  - [ ] remove silence,
  - [ ] find best quote,
  - [ ] make captions punchier.

---

## 13. Semantic Search MVP

- [ ] Chunk local videos by scene/time.
- [ ] Transcribe audio/video speech.
- [ ] OCR screenshots/video frames.
- [ ] Caption/summarize images.
- [ ] Generate chunk summaries.
- [ ] Embed transcript + summaries.
- [ ] Store embeddings locally.
- [ ] Search query → playable timestamp/image/audio results.
- [ ] Insert search result into timeline.
- [ ] Replace selected clip with search result.
- [ ] “Find similar.”

Search examples:

- “screen recording of dashboard.”
- “best proof that the app works.”
- “founder explaining the problem.”
- “logo or brand image.”
- “energetic B-roll.”
- “music that feels cinematic.”

---

## 14. Performance Wins

- [ ] Parallelize frontend artifact hydration with `Promise.all`.
- [ ] Parallelize media probes.
- [ ] Parallelize proxy/thumbnail/waveform generation with bounded concurrency.
- [ ] Parallelize TTS generation with provider limits.
- [ ] Parallelize image/background generation with provider limits.
- [ ] Parallelize independent block renders.
- [ ] Add preview/final quality modes.
- [ ] Cancel stale preview renders when timeline changes.
- [ ] Add duplicate-job prevention.
- [ ] Show cache hits.

---

## 15. Local-First Hardening

- [ ] Add/import local project SQLite database.
- [ ] Support import modes:
  - [ ] link in place,
  - [ ] copy into project,
  - [ ] proxy only,
  - [ ] generated/downloaded asset.
- [ ] Add structured project folder.
- [ ] Add durable local job table.
- [ ] Add job events.
- [ ] Add artifact lineage/cache keys.
- [ ] Add provider call logs.
- [ ] Add atomic writes.
- [ ] Add cleanup for temp/cache files.
- [ ] Add project-level mutation lock.

---

## 16. Web / Downloaded Assets

- [ ] Add explicit user permission for web search/download.
- [ ] Download to project `assets/downloaded/`.
- [ ] Store source URL/license/attribution metadata.
- [ ] Run downloaded media through asset index.
- [ ] Let main agent propose downloaded assets as timeline additions.
- [ ] Flag uncertain licensing.

---

## 17. Export / Publish Polish

- [ ] Export presets:
  - [ ] 9:16 TikTok/Reels/Shorts,
  - [ ] 16:9 YouTube/demo,
  - [ ] 1:1 square,
  - [ ] 4:5 social.
- [ ] Burn captions.
- [ ] Export SRT/VTT.
- [ ] Thumbnail/frame export.
- [ ] Loudness normalization.
- [ ] MP4 bitrate/quality selector.
- [ ] Project bundle zip.
- [ ] OpenTimelineIO export later.
- [ ] FCPXML later.

---

## 18. Reliability / Safety Quick Wins

- [ ] Retry/backoff for model calls.
- [ ] Health check for:
  - [ ] FFmpeg,
  - [ ] Remotion,
  - [ ] provider API keys,
  - [ ] disk space.
- [ ] Prompt version IDs.
- [ ] Schema version IDs.
- [ ] Skill version IDs.
- [ ] Context compiler version IDs.
- [ ] Provider call logs.
- [ ] Strict AI proposal validators.
- [ ] Prompt-injection boundaries for transcript/media/web text.
- [ ] User confirmation before expensive/cloud calls.
- [ ] No raw local filesystem paths in model prompts unless necessary.
- [ ] No model-generated shell/FFmpeg commands.

---

## 19. Code Cleanup

- [ ] Split `backend/app/integrations/gemini/service.py` into modules:
  - [ ] scene analysis,
  - [ ] plan generation,
  - [ ] asset generation,
  - [ ] TTS/STT,
  - [ ] review,
  - [ ] plan editing,
  - [ ] agent tools.
- [ ] Split `backend/app/api/routes.py` into routers:
  - [ ] projects,
  - [ ] jobs,
  - [ ] artifacts,
  - [ ] media/assets,
  - [ ] plan/timeline,
  - [ ] agent.
- [ ] Add tests for:
  - [ ] manifest/timeline tools,
  - [ ] checker failures,
  - [ ] proposal validation,
  - [ ] path safety,
  - [ ] asset intake,
  - [ ] relevance selection,
  - [ ] render cache keys.
- [ ] Add `.env.example`.
- [ ] Add setup docs for Windows/WSL confusion.
- [ ] Add smoke test script for full demo pipeline.

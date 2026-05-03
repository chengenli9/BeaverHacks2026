# Demo Runbook

## Goal

Make the hackathon demo feel complete even if one live Gemini call is slow or unavailable.

## Golden Path

```text
1. Open Scenerio.
2. Click Open Demo Project.
3. Click Analyze.
4. Show scene_index.json summary.
5. Click Plan.
6. Show plan beats.
7. Click Generate TTS and Assets.
8. Show asset statuses.
9. Click Build Manifest.
10. Show block cards and duration reconciliation.
11. Click Pre-Critique.
12. Approve one suggestion and reject one suggestion.
13. Click Apply Approved Changes.
14. Click Render.
15. Show block render progress.
16. Play final_render.mp4.
```

## Fallback Path

If Gemini fails:

```text
1. Load committed fixture JSON from samples/demo_project.
2. Show that the same UI works with cached artifacts.
3. Continue to manifest and render.
```

If FFmpeg fails:

```text
1. Show the manifest cards and critic approval loop.
2. Open logs/ffmpeg.log and show the actionable validation error.
3. Explain that the renderer fails before producing a broken MP4.
```

If the source video is missing:

```text
1. Show sample JSON.
2. Show manifest validation reporting source/demo_footage.mp4 as missing.
3. Drop a demo MP4 into samples/demo_project/source and retry.
```

## Demo Polish Checklist

- Browser starts on the app dashboard.
- No terminal-only steps are required during the main demo.
- The Open Demo Project action works first.
- Long-running stages visibly progress.
- Error messages are visible in the UI.
- Critic cards are human-approval cards, not automatic changes.
- Final render preview is visible in the right panel.
- `.env` uses cheap Gemini defaults.
- Pro models are not selected.
- The room can understand the product in 20 seconds.


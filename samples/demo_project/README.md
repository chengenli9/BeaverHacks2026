# Demo Project Fixture

This fixture lets all four dev lanes work in parallel before the live Gemini and FFmpeg paths are complete.

Expected runtime files:

```text
source/demo_footage.mp4
assets/backgrounds/bg_001.png
assets/backgrounds/bg_003.png
assets/tts/tts_002.wav
assets/fonts/Inter-Bold.ttf
blocks/*.mp4
renders/final_render.mp4
logs/*.jsonl
```

Committed fixture files:

```text
cache/scene_index.json
manifests/plan.json
manifests/block_manifest.json
manifests/critic_suggestions.json
```

The committed manifest references generated media paths that may not exist yet. Renderer validation should report missing source, font, background, or TTS files clearly.


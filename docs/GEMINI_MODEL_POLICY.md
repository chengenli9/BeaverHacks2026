# Gemini Model and Credit Policy

Last repo-verified: 2026-05-03

## Goal

Use Gemini where it makes the demo better, but default to cheaper models so the team does not burn credits during repeated hackathon runs.

## Default Model Matrix

| Pipeline stage | Default model | Reason |
| --- | --- | --- |
| Scene analysis | `gemini-3.1-flash-lite-preview` | Cheap default text model configured in `backend/app/integrations/gemini/settings.py`. |
| Plan generation | `gemini-3.1-flash-lite-preview` | Structured JSON planning does not need Pro by default. |
| Narration script generation | `gemini-3.1-flash-lite-preview` | Short text generation with strict duration constraints. |
| Manifest pre-critique | `gemini-3.1-flash-lite-preview` | Blind text-only critique over JSON artifacts. |
| Render review | `gemini-3.1-flash-lite-preview` | Render QA should stay on the same cheap text default. |
| TTS narration | `gemini-2.5-flash-preview-tts` | Lower-cost Flash TTS path for controllable speech. |
| Textless backgrounds | `gemini-2.5-flash-image` | Speed and cost before high-end image quality. |

## Environment Variables

Use:

```bash
GEMINI_TEXT_MODEL=gemini-3.1-flash-lite-preview
GEMINI_TTS_MODEL=gemini-2.5-flash-preview-tts
GEMINI_IMAGE_MODEL=gemini-2.5-flash-image
GEMINI_ENABLE_GROUNDING=false
GEMINI_MAX_OUTPUT_TOKENS=4096
```

## Hard Rules

- Do not use Gemini Pro in the MVP path.
- Do not enable search grounding by default.
- Do not generate multiple variants unless the user explicitly requests variants.
- Do not ask image models to render typography for the live path.
- Do not retry expensive calls more than once automatically.
- Do not run live Gemini tests in default CI.

## Allowed Fallbacks

If the configured Flash-Lite text model produces invalid structured JSON twice, the endpoint may return a job failure with a clear retry message. Do not silently switch to a Pro model.

If image generation fails, use a local placeholder background so the renderer can still complete the demo.

If TTS fails, use source audio only and mark the block as missing narration in the UI.

## Logging

Log this metadata to `logs/gemini_calls.jsonl`:

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

Never log:

```text
GEMINI_API_KEY
raw binary image data
raw binary audio data
full private source transcript unless the user opts in
```

## Source References

- Gemini model list: https://ai.google.dev/gemini-api/docs/models
- Gemini pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini structured outputs: https://ai.google.dev/gemini-api/docs/structured-output
- Gemini TTS: https://ai.google.dev/gemini-api/docs/speech-generation
- Gemini image generation: https://ai.google.dev/gemini-api/docs/image-generation

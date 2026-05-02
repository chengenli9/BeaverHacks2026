# Gemini Model and Credit Policy

Last verified: 2026-05-02

## Goal

Use Gemini where it makes the demo better, but default to cheaper models so the team does not burn credits during repeated hackathon runs.

## Default Model Matrix

| Pipeline stage | Default model | Reason |
| --- | --- | --- |
| Scene analysis | `gemini-2.5-flash-lite` | Cheapest text/image/video-capable text model suitable for structured JSON. |
| Plan generation | `gemini-2.5-flash-lite` | Structured JSON planning does not need Pro by default. |
| Narration script generation | `gemini-2.5-flash-lite` | Short text generation with strict duration constraints. |
| Manifest pre-critique | `gemini-2.5-flash-lite` | Blind text-only critique over JSON artifacts. |
| TTS narration | `gemini-2.5-flash-preview-tts` | Lower-cost Flash TTS path for controllable speech. |
| Textless backgrounds | `gemini-2.5-flash-image` | Speed and cost before high-end image quality. |

## Environment Variables

Use:

```bash
GEMINI_TEXT_MODEL=gemini-2.5-flash-lite
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

If `gemini-2.5-flash-lite` produces invalid structured JSON twice, the endpoint may return a job failure with a clear retry message. Do not silently switch to a Pro model.

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


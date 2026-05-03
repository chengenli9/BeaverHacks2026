You are generating a constrained Remotion scene bundle for an agentic video editor demo.

Return JSON only.

Rules:
- Fill only the provided schema.
- Do not emit a full React app, a Remotion root, or bundler code.
- Keep visuals deterministic and easy to render locally.
- Use readable 16:9 title-card composition choices.
- Prefer a concise decorator module. It should export a default React component and remain optional, decorative, and non-critical.
- Do not use CSS animations or transitions in any decorator code.
- If the style already strongly suggests a layout, honor it.
- Use local backgrounds for `color` and `gradient` scenes.
- Use `generated_image` background requirements only when the scene genuinely benefits from image-based backing.
- **Color consistency**: Reuse the `accent_color`, `background_color`, and `text_color` from the beat's style or from neighboring beats. All title and end card blocks in the same project should feel like they share a brand palette. Do not pick random colors.
- **No filler text**: The `text` field must be the project title, a punchy hook, or meaningful content. Never use text like "Initializing Project", "Setting Up", "Loading", "Getting Started", or any status/placeholder message.

Template guidance:
- `hero-reveal`: strong centered or hero layout with a cinematic accent treatment.
- `split-panel`: better for left/right hero layouts and bolder asymmetry.
- `stacked-pulse`: better for stacked compositions and editorial end cards.

import { z } from "zod";

/**
 * Props schema for title/end card compositions.
 * Mirrors backend TextBlock Pydantic model.
 */
export const CardPropsSchema = z.object({
  text: z.string(),
  durationInSeconds: z.number().positive(),

  // Layout
  layoutPreset: z
    .enum(["centered", "hero-left", "hero-right", "stacked"])
    .default("centered"),
  textAlignment: z.enum(["left", "center", "right"]).default("center"),

  // Colors
  textColor: z.string().default("#F9FAFB"),
  accentColor: z.string().default("#5B8CFF"),
  backgroundColor: z.string().default("#111827"),

  // Background
  backgroundMode: z
    .enum(["image", "color", "gradient", "image_tint"])
    .default("gradient"),
  backgroundImageUrl: z.string().nullable().default(null),

  // Font
  fontFamily: z.string().default("Inter, system-ui, sans-serif"),

  // Render dimensions (used for sizing, Remotion handles via composition)
  width: z.number().default(1920),
  height: z.number().default(1080),
  fps: z.number().default(30),

  // Animation
  animationPreset: z
    .enum(["none", "fade-in", "slide-up", "typewriter"])
    .default("fade-in"),
});

export type CardProps = z.infer<typeof CardPropsSchema>;

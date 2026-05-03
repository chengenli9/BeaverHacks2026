import React, { type ComponentType } from "react";
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

export interface GeneratedTextSceneSpec {
  version: number;
  block_type: "title" | "scene_card" | "end_card";
  text: string;
  duration_seconds: number;
  runtime_template: "hero-reveal" | "split-panel" | "stacked-pulse";
  layout_preset: "centered" | "hero-left" | "hero-right" | "stacked";
  text_alignment: "left" | "center" | "right";
  font_family: string;
  font_variant: string;
  text_color: string;
  accent_color: string;
  background_mode: "image" | "color" | "gradient" | "image_tint";
  background_color: string;
  background_image_path: string | null;
  animation_preset: "fade-in" | "slide-up" | "typewriter";
  show_glass_panel: boolean;
  show_accent_bar: boolean;
}

export interface RuntimeDecoratorProps {
  scene: GeneratedTextSceneSpec;
  frame: number;
  fps: number;
  width: number;
  height: number;
}

type DecoratorComponent = ComponentType<RuntimeDecoratorProps> | null | undefined;

export const GeneratedTextScene: React.FC<{
  scene: GeneratedTextSceneSpec;
  Decorator?: DecoratorComponent;
}> = ({ scene, Decorator }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const fadeFrames = Math.max(1, Math.round(fps * 0.8));

  const opacity = interpolate(frame, [0, fadeFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const translateY =
    scene.animation_preset === "slide-up" || scene.runtime_template === "stacked-pulse"
      ? interpolate(frame, [0, fadeFrames], [36, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.cubic),
        })
      : 0;
  const scale = scene.runtime_template === "hero-reveal"
    ? interpolate(frame, [0, fadeFrames], [0.96, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.out(Easing.cubic),
      })
    : 1;

  const layout = getLayoutBox(scene.layout_preset);
  const alignItems =
    scene.text_alignment === "left"
      ? "flex-start"
      : scene.text_alignment === "right"
        ? "flex-end"
        : "center";

  return (
    <AbsoluteFill
      style={{
        overflow: "hidden",
        backgroundColor: scene.background_color,
        fontFamily: getFontFamily(scene.font_family),
      }}
    >
      <BackgroundLayer scene={scene} />

      {scene.show_glass_panel ? (
        <div
          style={{
            position: "absolute",
            left: `${layout.left - 3}%`,
            top: `${layout.top - 3}%`,
            width: `${layout.width + 6}%`,
            height: `${layout.height + 8}%`,
            borderRadius: scene.runtime_template === "stacked-pulse" ? 48 : 36,
            background: "rgba(7, 10, 18, 0.42)",
            border: "1px solid rgba(255,255,255,0.08)",
            opacity,
            transform: `scale(${scale})`,
          }}
        />
      ) : null}

      {scene.show_accent_bar ? <AccentChrome scene={scene} layout={layout} opacity={opacity} /> : null}

      <div
        style={{
          position: "absolute",
          left: `${layout.left}%`,
          top: `${layout.top}%`,
          width: `${layout.width}%`,
          height: `${layout.height}%`,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems,
          textAlign: scene.text_alignment,
          opacity,
          transform: `translateY(${translateY}px) scale(${scale})`,
        }}
      >
        <div
          style={{
            color: scene.text_color,
            fontWeight: scene.font_variant === "regular" ? 500 : 700,
            fontSize: scene.block_type === "title"
              ? "clamp(3.2rem, 8vw, 8.5rem)"
              : scene.block_type === "end_card"
                ? "clamp(2.8rem, 7vw, 7.5rem)"
                : scene.block_type === "scene_card"
                  ? "clamp(2.4rem, 6vw, 6.6rem)"
                  : scene.runtime_template === "stacked-pulse"
                    ? "clamp(2.4rem, 6vw, 6.6rem)"
                    : "clamp(2.1rem, 5.2vw, 6rem)",
            lineHeight: 1.12,
            maxWidth: "100%",
            textShadow: "0 6px 32px rgba(0,0,0,0.35)",
            whiteSpace: "pre-wrap",
          }}
        >
          {renderText(scene.text, scene.animation_preset, frame, fps)}
        </div>
      </div>

      {Decorator ? <Decorator scene={scene} frame={frame} fps={fps} width={width} height={height} /> : null}
    </AbsoluteFill>
  );
};

const BackgroundLayer: React.FC<{ scene: GeneratedTextSceneSpec }> = ({ scene }) => {
  const imagePath = scene.background_image_path
    ? scene.background_image_path.startsWith("/") || scene.background_image_path.startsWith("http")
      ? scene.background_image_path
      : staticFile(scene.background_image_path)
    : null;

  const gradient = `linear-gradient(135deg, ${scene.background_color} 0%, ${scene.accent_color} 130%)`;
  return (
    <AbsoluteFill>
      {scene.background_mode === "image" || scene.background_mode === "image_tint" ? (
        <>
          {imagePath ? <Img src={imagePath} style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : null}
          {scene.background_mode === "image_tint" ? (
            <div style={{ position: "absolute", inset: 0, background: gradient, opacity: 0.48 }} />
          ) : null}
        </>
      ) : scene.background_mode === "gradient" ? (
        <div style={{ position: "absolute", inset: 0, background: gradient }} />
      ) : null}

      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(circle at 70% 20%, rgba(255,255,255,0.10), transparent 32%), radial-gradient(circle at 18% 78%, rgba(255,255,255,0.06), transparent 28%)",
        }}
      />
    </AbsoluteFill>
  );
};

const AccentChrome: React.FC<{
  scene: GeneratedTextSceneSpec;
  layout: ReturnType<typeof getLayoutBox>;
  opacity: number;
}> = ({ scene, layout, opacity }) => {
  if (scene.runtime_template === "split-panel") {
    const side = scene.layout_preset === "hero-right" ? "right" : "left";
    return (
      <div
        style={{
          position: "absolute",
          [side]: `${100 - (layout.left + layout.width) + 1.5}%`,
          top: `${layout.top}%`,
          width: 12,
          height: `${layout.height}%`,
          borderRadius: 999,
          backgroundColor: scene.accent_color,
          opacity,
        }}
      />
    );
  }

  return (
    <div
      style={{
        position: "absolute",
        left: `${layout.left}%`,
        top: `${Math.max(6, layout.top - 6)}%`,
        width: scene.runtime_template === "stacked-pulse" ? "18%" : "14%",
        height: 14,
        borderRadius: 999,
        backgroundColor: scene.accent_color,
        opacity,
      }}
    />
  );
};

const getLayoutBox = (preset: GeneratedTextSceneSpec["layout_preset"]) => {
  switch (preset) {
    case "hero-left":
      return { left: 10, top: 20, width: 42, height: 58 };
    case "hero-right":
      return { left: 48, top: 20, width: 42, height: 58 };
    case "stacked":
      return { left: 14, top: 22, width: 72, height: 44 };
    default:
      return { left: 16, top: 24, width: 68, height: 50 };
  }
};

const getFontFamily = (fontFamily: string) => {
  switch (fontFamily) {
    case "display-serif":
      return "Georgia, 'Times New Roman', serif";
    case "mono-tech":
      return "'IBM Plex Mono', Consolas, monospace";
    case "editorial":
      return "'Trebuchet MS', 'Segoe UI', sans-serif";
    default:
      return "Inter, system-ui, sans-serif";
  }
};

const renderText = (text: string, preset: GeneratedTextSceneSpec["animation_preset"], frame: number, fps: number) => {
  if (preset !== "typewriter") {
    return text;
  }
  const chars = Math.max(1, Math.floor((frame / Math.max(1, fps / 8)) + 1));
  return text.slice(0, chars);
};

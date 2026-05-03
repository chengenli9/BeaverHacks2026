import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
  Img,
  staticFile,
} from "remotion";
import type { CardProps } from "./schemas/card-props";

/**
 * TitleCard / EndCard composition.
 * Ports the Pillow _render_text_overlay() visuals to React/CSS with animation.
 */
export const CardComposition: React.FC<CardProps> = (props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const {
    text,
    layoutPreset,
    textAlignment,
    textColor,
    accentColor,
    backgroundColor,
    backgroundMode,
    backgroundImageUrl,
    fontFamily,
    animationPreset,
  } = props;

  // --- Animation timing ---
  const fadeInDuration = 0.8; // seconds
  const fadeInFrames = fadeInDuration * fps;

  // Master opacity for "fade-in"
  const masterOpacity =
    animationPreset === "none"
      ? 1
      : interpolate(frame, [0, fadeInFrames], [0, 1], {
          extrapolateRight: "clamp",
        });

  // Text slide-up offset
  const slideOffset =
    animationPreset === "slide-up"
      ? interpolate(frame, [0, fadeInFrames], [40, 0], {
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.cubic),
        })
      : 0;

  // Panel scale-in (subtle)
  const panelScale =
    animationPreset === "none"
      ? 1
      : interpolate(frame, [0, fadeInFrames * 0.6], [0.92, 1], {
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.cubic),
        });

  // --- Text layout box (mirrors Pillow _text_box_for_layout) ---
  const textBoxes: Record<string, [number, number, number, number]> = {
    centered: [16, 22, 84, 78],
    "hero-left": [10, 18, 54, 82],
    "hero-right": [46, 18, 90, 82],
    stacked: [14, 18, 86, 68],
  };
  const [tlx, tly, brx, bry] = textBoxes[layoutPreset] ?? textBoxes.centered;

  // --- Panel bounds ---
  const panelPadX = layoutPreset === "stacked" ? 2.8 : 3.4;
  const panelPadTop = layoutPreset === "stacked" ? 2.4 : 3.0;
  const panelPadBot = layoutPreset === "stacked" ? 4.2 : 3.0;

  // --- Lines (split on newline, CSS handles wrapping) ---
  const paragraphs = text.split("\n").filter((p) => p.length > 0);
  const displayLines = paragraphs.length > 0 ? paragraphs : [text];

  // --- Accent bar positioning ---
  const isHero = layoutPreset === "hero-left" || layoutPreset === "hero-right";

  return (
    <AbsoluteFill
      style={{
        width: "100%",
        height: "100%",
        position: "relative",
        overflow: "hidden",
        fontFamily,
      }}
    >
      {/* --- Background layer --- */}
      <BackgroundLayer
        backgroundColor={backgroundColor}
        accentColor={accentColor}
        backgroundMode={backgroundMode}
        backgroundImageUrl={backgroundImageUrl}
      />

      {/* --- Bokeh accents (ellipse + rect with heavy blur) --- */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "8%",
            width: "55%",
            height: "74%",
            borderRadius: "50%",
            backgroundColor: accentColor,
            opacity: 0.12,
            filter: "blur(92px)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: "5%",
            top: "72%",
            width: "35%",
            height: "20%",
            backgroundColor: accentColor,
            opacity: 0.05,
            filter: "blur(92px)",
          }}
        />
      </div>

      {/* --- Glass panel --- */}
      <div
        style={{
          position: "absolute",
          left: `${tlx - panelPadX}%`,
          top: `${tly - panelPadTop}%`,
          right: `${100 - brx - panelPadX}%`,
          bottom: `${100 - bry - panelPadBot}%`,
          backgroundColor: "rgba(7, 10, 18, 0.48)",
          borderRadius: 40,
          backdropFilter: "blur(1px)",
          transform: `scale(${panelScale})`,
          opacity: masterOpacity,
        }}
      >
        {/* Accent bar */}
        {isHero ? (
          <div
            style={{
              position: "absolute",
              left: layoutPreset === "hero-left" ? 20 : undefined,
              right: layoutPreset === "hero-right" ? 20 : undefined,
              top: 28,
              bottom: 28,
              width: 12,
              borderRadius: 6,
              backgroundColor: accentColor,
            }}
          />
        ) : (
          <div
            style={{
              position: "absolute",
              left: 24,
              top: 20,
              width: 196,
              height: 14,
              borderRadius: 7,
              backgroundColor: accentColor,
            }}
          />
        )}
      </div>

      {/* --- Text layer --- */}
      <div
        style={{
          position: "absolute",
          left: `${tlx}%`,
          top: `${tly}%`,
          right: `${100 - brx}%`,
          bottom: `${100 - bry}%`,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems:
            textAlignment === "left"
              ? "flex-start"
              : textAlignment === "right"
                ? "flex-end"
                : "center",
          opacity: masterOpacity,
          transform: `translateY(${slideOffset}px)`,
          paddingLeft: isHero && layoutPreset === "hero-left" ? 40 : 0,
          paddingRight: isHero && layoutPreset === "hero-right" ? 40 : 0,
        }}
      >
        {displayLines.map((line, i) => (
          <div
            key={i}
            style={{
              color: textColor,
              fontSize: "clamp(2rem, 5.5vw, 6rem)",
              fontWeight: 700,
              lineHeight: 1.18,
              textAlign: textAlignment,
              width: "100%",
              textShadow: "4px 4px 0px rgba(0,0,0,0.66)",
              letterSpacing: "-0.01em",
            }}
          >
            {animationPreset === "typewriter"
              ? typewriterText(line, frame, fps, i)
              : line}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};

/**
 * Background layer component -- handles gradient, color, image, image_tint modes.
 */
const BackgroundLayer: React.FC<{
  backgroundColor: string;
  accentColor: string;
  backgroundMode: string;
  backgroundImageUrl: string | null;
}> = ({ backgroundColor, accentColor, backgroundMode, backgroundImageUrl }) => {
  const gradient = `linear-gradient(to bottom, ${backgroundColor} 0%, ${accentColor}65 100%)`;

  // Resolve background image URL
  // Public-relative paths (from render-card) start with "/" -- use staticFile
  // HTTP URLs pass through
  const resolvedImageUrl = backgroundImageUrl
    ? backgroundImageUrl.startsWith("http")
      ? backgroundImageUrl
      : backgroundImageUrl.startsWith("/")
        ? staticFile(backgroundImageUrl.slice(1))  // strip leading /
        : backgroundImageUrl
    : null;

  return (
    <AbsoluteFill>
      {/* Base color or gradient */}
      {(backgroundMode === "color" ||
        backgroundMode === "gradient" ||
        backgroundMode === "image_tint") && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: backgroundMode === "color" ? backgroundColor : gradient,
          }}
        />
      )}

      {/* Background image */}
      {backgroundMode !== "color" && resolvedImageUrl && (
        <Img
          src={resolvedImageUrl}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
      )}

      {/* Tint overlay for image_tint mode */}
      {backgroundMode === "image_tint" && (
        <>
          <div
            style={{
              position: "absolute",
              inset: 0,
              backgroundColor,
              opacity: 0.28,
            }}
          />
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: `linear-gradient(to bottom, ${accentColor}18 0%, ${accentColor}5A 100%)`,
            }}
          />
        </>
      )}

      {/* If image mode with no image, fall back to gradient */}
      {backgroundMode === "image" && !resolvedImageUrl && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: gradient,
          }}
        />
      )}
    </AbsoluteFill>
  );
};

/**
 * Returns text revealed character by character for typewriter effect.
 */
function typewriterText(
  text: string,
  frame: number,
  fps: number,
  lineIndex: number,
): string {
  const charsPerSecond = 18;
  const delaySeconds = lineIndex * 0.4;
  const startFrame = delaySeconds * fps;
  const framesSinceStart = Math.max(0, frame - startFrame);
  const charsToReveal = Math.floor(
    (framesSinceStart / fps) * charsPerSecond,
  );
  return text.slice(0, Math.min(charsToReveal, text.length));
}

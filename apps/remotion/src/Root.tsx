import React from "react";
import { Composition } from "remotion";
import { CardComposition } from "./CardComposition";
import { CardPropsSchema } from "./schemas/card-props";
import type { CardProps } from "./schemas/card-props";

const defaultProps: CardProps = {
  text: "Scenerio",
  durationInSeconds: 3,
  layoutPreset: "centered",
  textAlignment: "center",
  textColor: "#F9FAFB",
  accentColor: "#5B8CFF",
  backgroundColor: "#111827",
  backgroundMode: "gradient",
  backgroundImageUrl: null,
  fontFamily: "Inter, system-ui, sans-serif",
  width: 1920,
  height: 1080,
  fps: 30,
  animationPreset: "fade-in",
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="TitleCard"
        component={CardComposition}
        schema={CardPropsSchema}
        defaultProps={defaultProps}
        durationInFrames={90}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="EndCard"
        component={CardComposition}
        schema={CardPropsSchema}
        defaultProps={defaultProps}
        durationInFrames={90}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};

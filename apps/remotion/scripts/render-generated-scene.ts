import { bundle } from "@remotion/bundler";
import { getCompositions, renderMedia, renderStill } from "@remotion/renderer";
import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, isAbsolute, join, relative, resolve } from "node:path";
import { parseArgs } from "node:util";

type SceneSpec = {
  duration_seconds: number;
  background_image_path: string | null;
};

const toImportPath = (fromDir: string, targetFile: string) => {
  const rel = relative(fromDir, targetFile).replace(/\\/g, "/");
  return rel.startsWith(".") ? rel : `./${rel}`;
};

const resolveFromWorkspace = (workspaceRoot: string, input: string) => {
  return isAbsolute(input) ? input : resolve(workspaceRoot, input);
};

async function main() {
  const { values } = parseArgs({
    options: {
      "project-path": { type: "string" },
      "block-id": { type: "string" },
      "scene-spec": { type: "string" },
      decorator: { type: "string" },
      output: { type: "string" },
      fps: { type: "string", default: "30" },
      width: { type: "string", default: "1920" },
      height: { type: "string", default: "1080" },
      mode: { type: "string", default: "video" },
    },
    strict: true,
  });

  if (!values["project-path"] || !values["block-id"] || !values["scene-spec"] || !values.output) {
    throw new Error("Missing required arguments for generated scene render.");
  }

  const remotionRoot = resolve(import.meta.dirname, "..");
  const workspaceRoot = resolve(remotionRoot, "..");
  const projectPath = resolveFromWorkspace(workspaceRoot, String(values["project-path"]));
  const blockId = String(values["block-id"]);
  const sceneSpecPath = resolveFromWorkspace(workspaceRoot, String(values["scene-spec"]));
  const decoratorPath = values.decorator ? resolveFromWorkspace(workspaceRoot, String(values.decorator)) : null;
  const outputPath = resolveFromWorkspace(workspaceRoot, String(values.output));
  const fps = Number.parseInt(String(values.fps), 10);
  const width = Number.parseInt(String(values.width), 10);
  const height = Number.parseInt(String(values.height), 10);
  const mode = String(values.mode);

  mkdirSync(dirname(outputPath), { recursive: true });

  const tempDir = mkdtempSync(join(tmpdir(), `directorloop-remotion-${blockId}-`));
  const publicDir = resolve(remotionRoot, "public");
  mkdirSync(publicDir, { recursive: true });

  const sceneSpec = JSON.parse(readFileSync(sceneSpecPath, "utf-8")) as SceneSpec;
  if (sceneSpec.background_image_path) {
    const sourcePath = resolve(projectPath, sceneSpec.background_image_path);
    if (existsSync(sourcePath)) {
      const copiedName = `_generated_${blockId}_${basename(sourcePath)}`;
      copyFileSync(sourcePath, join(publicDir, copiedName));
      sceneSpec.background_image_path = `/${copiedName}`;
    }
  }

  writeFileSync(join(tempDir, "scene.json"), JSON.stringify(sceneSpec, null, 2), "utf-8");
  if (decoratorPath && existsSync(decoratorPath)) {
    copyFileSync(decoratorPath, join(tempDir, "decorator.tsx"));
  } else {
    writeFileSync(join(tempDir, "decorator.tsx"), "export default function Decorator(){ return null; }\n", "utf-8");
  }

  const generatedSceneImport = toImportPath(tempDir, resolve(remotionRoot, "src", "GeneratedTextScene.tsx"));
  writeFileSync(
    join(tempDir, "Root.tsx"),
    [
      'import React from "react";',
      'import { Composition } from "remotion";',
      `import { GeneratedTextScene } from "${generatedSceneImport}";`,
      'import scene from "./scene.json";',
      'import Decorator from "./decorator";',
      "const SceneWrapper = () => <GeneratedTextScene scene={scene} Decorator={Decorator} />;",
      "",
      "export const RemotionRoot = () => {",
      `  const fps = ${fps};`,
      `  const width = ${width};`,
      `  const height = ${height};`,
      "  const durationInFrames = Math.max(1, Math.round(scene.duration_seconds * fps));",
      "  return (",
      "    <Composition",
      '      id="GeneratedTextScene"',
      "      component={SceneWrapper}",
      "      durationInFrames={durationInFrames}",
      "      fps={fps}",
      "      width={width}",
      "      height={height}",
      "    />",
      "  );",
      "};",
      "",
    ].join("\n"),
    "utf-8",
  );
  writeFileSync(
    join(tempDir, "index.ts"),
    ['import { registerRoot } from "remotion";', 'import { RemotionRoot } from "./Root";', "registerRoot(RemotionRoot);\n"].join("\n"),
    "utf-8",
  );

  const bundleLocation = await bundle({
    entryPoint: join(tempDir, "index.ts"),
    publicDir,
  });
  const compositions = await getCompositions(bundleLocation);
  const composition = compositions.find((c) => c.id === "GeneratedTextScene");
  if (!composition) {
    throw new Error("GeneratedTextScene composition not found.");
  }

  try {
    if (mode === "still") {
      const frame = Math.max(0, Math.min(Math.round(fps), composition.durationInFrames - 1));
      await renderStill({
        serveUrl: bundleLocation,
        composition: {
          ...composition,
          fps,
          width,
          height,
          durationInFrames: Math.max(1, Math.round(sceneSpec.duration_seconds * fps)),
        },
        output: outputPath,
        frame,
        imageFormat: "png",
      });
    } else {
      await renderMedia({
        serveUrl: bundleLocation,
        composition: {
          ...composition,
          fps,
          width,
          height,
          durationInFrames: Math.max(1, Math.round(sceneSpec.duration_seconds * fps)),
        },
        codec: "h264",
        outputLocation: outputPath,
        inputProps: {},
      });
    }
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error("[render-generated-scene] Fatal error:", error);
  process.exit(1);
});

/**
 * render-card.ts
 *
 * Headless Remotion renderer for Scenerio title/end cards.
 * Called by the Python backend as a subprocess.
 *
 * Usage:
 *   npx tsx scripts/render-card.ts \
 *     --composition TitleCard \
 *     --props '{"text":"Hello","durationInSeconds":3}' \
 *     --output /path/to/blocks/001_title.mp4
 *
 * For background images, pass the absolute path as backgroundImageUrl.
 * The script will copy it into the Remotion public/ directory so the
 * browser can access it. Set backgroundImageUrl to "SERVE:<relative-path>"
 * after the first copy to skip re-copying.
 */
import { bundle } from "@remotion/bundler";
import { renderMedia, getCompositions } from "@remotion/renderer";
import type { FfmpegOverrideFn } from "@remotion/renderer";
import { spawnSync } from "node:child_process";
import { parseArgs } from "node:util";
import { existsSync, mkdirSync, copyFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, resolve, basename, join } from "node:path";

type HardwareAccelerationOption = "disable" | "if-possible" | "required";

const resolveSystemBinary = (binary: "ffmpeg" | "ffprobe"): string | null => {
  const command = process.platform === "win32" ? "where" : "which";
  const result = spawnSync(command, [binary], { encoding: "utf-8" });
  if (result.status !== 0) {
    return null;
  }

  return result.stdout
    .split(/\r?\n/)
    .map((line) => line.trim())
    .find(Boolean) ?? null;
};

const prepareBinariesDirectory = (remotionRoot: string, tempDir: string, videoCodec: string): string | null => {
  if (videoCodec !== "h264_nvenc" && !process.env.REMOTION_FFMPEG_DIR) {
    return null;
  }

  const ffmpegPath = process.env.REMOTION_FFMPEG_PATH ?? resolveSystemBinary("ffmpeg");
  const ffprobePath = process.env.REMOTION_FFPROBE_PATH ?? resolveSystemBinary("ffprobe");
  const compositorDir = resolve(remotionRoot, "node_modules", "@remotion", "compositor-win32-x64-msvc");
  const remotionExe = join(compositorDir, process.platform === "win32" ? "remotion.exe" : "remotion");
  if (!ffmpegPath || !ffprobePath || !existsSync(remotionExe)) {
    return null;
  }

  const shimDir = join(tempDir, "binaries");
  mkdirSync(shimDir, { recursive: true });
  copyFileSync(remotionExe, join(shimDir, basename(remotionExe)));
  copyFileSync(ffmpegPath, join(shimDir, basename(ffmpegPath)));
  copyFileSync(ffprobePath, join(shimDir, basename(ffprobePath)));
  return shimDir;
};

const resolveRenderOverrides = (videoCodec: string): {
  hardwareAcceleration: HardwareAccelerationOption;
  ffmpegOverride?: FfmpegOverrideFn;
} => {
  if (videoCodec === "h264_nvenc") {
    return {
      hardwareAcceleration: "if-possible",
      ffmpegOverride: ({ args }) =>
        args.map((arg, index, allArgs) => {
          if (arg === "libx264" && index > 0 && allArgs[index - 1] === "-c:v") {
            return "h264_nvenc";
          }
          return arg;
        }),
    };
  }

  return { hardwareAcceleration: "disable" };
};

async function main() {
  const { values } = parseArgs({
    options: {
      composition: { type: "string", default: "TitleCard" },
      props: { type: "string" },
      "props-file": { type: "string" },
      output: { type: "string" },
      fps: { type: "string", default: "30" },
      width: { type: "string", default: "1920" },
      height: { type: "string", default: "1080" },
      "video-codec": { type: "string", default: "libx264" },
      help: { type: "boolean", default: false },
    },
    strict: true,
  });

  if (values.help) {
    console.log(`Usage: render-card [options]

Options:
  --composition   Composition ID: TitleCard or EndCard (default: TitleCard)
  --props         JSON string with card props
  --props-file    Path to JSON file with card props
  --output        Output MP4 file path (required)
  --fps           Frame rate (default: 30)
  --width         Width in pixels (default: 1920)
  --height        Height in pixels (default: 1080)
`);
    process.exit(0);
  }

  if (!values.output) {
    console.error("Error: --output is required");
    process.exit(1);
  }

  const outputPath = resolve(values.output);
  const outputDir = dirname(outputPath);
  if (!existsSync(outputDir)) {
    mkdirSync(outputDir, { recursive: true });
  }

  // Parse props
  let inputProps: Record<string, unknown> = {};
  if (values["props-file"]) {
    const { readFileSync } = await import("node:fs");
    inputProps = JSON.parse(readFileSync(values["props-file"], "utf-8"));
  } else if (values.props) {
    inputProps = JSON.parse(values.props);
  }

  const fps = parseInt(values.fps!, 10);
  const width = parseInt(values.width!, 10);
  const height = parseInt(values.height!, 10);
  const videoCodec = String(values["video-codec"]);
  const { hardwareAcceleration, ffmpegOverride } = resolveRenderOverrides(videoCodec);

  // Duration in frames
  const durationInSeconds =
    typeof inputProps.durationInSeconds === "number"
      ? inputProps.durationInSeconds
      : 3;
  const durationInFrames = Math.round(durationInSeconds * fps);

  // Resolve the Remotion entry point relative to this script
  const remotionRoot = resolve(import.meta.dirname, "..");
  const tempDir = mkdtempSync(join(tmpdir(), "scenerio-render-card-"));
  const binariesDirectory = prepareBinariesDirectory(remotionRoot, tempDir, videoCodec);
  const entryPoint = resolve(remotionRoot, "src", "index.ts");

  console.log(`[render-card] Composition: ${values.composition}`);
  console.log(`[render-card] Duration: ${durationInFrames} frames (${durationInSeconds}s @ ${fps}fps)`);
  console.log(`[render-card] Resolution: ${width}x${height}`);
  console.log(`[render-card] Output: ${outputPath}`);

  // Handle background images: copy into public/ so Remotion's staticFile can serve them
  const publicDir = resolve(remotionRoot, "public");
  if (!existsSync(publicDir)) {
    mkdirSync(publicDir, { recursive: true });
  }

  if (
    inputProps.backgroundImageUrl &&
    typeof inputProps.backgroundImageUrl === "string" &&
    !inputProps.backgroundImageUrl.startsWith("http") &&
    !inputProps.backgroundImageUrl.startsWith("/")
  ) {
    const srcPath = resolve(String(inputProps.backgroundImageUrl));
    if (existsSync(srcPath)) {
      const destName = `_bg_${basename(srcPath)}`;
      const destPath = join(publicDir, destName);
      copyFileSync(srcPath, destPath);
      // Replace with the public path that the Remotion component will resolve
      // We use a special prefix that the component understands
      inputProps.backgroundImageUrl = `/${destName}`;
    }
  } else if (
    inputProps.backgroundImageUrl &&
    typeof inputProps.backgroundImageUrl === "string" &&
    String(inputProps.backgroundImageUrl).startsWith("/")
  ) {
    // Absolute local path -- copy to public
    const srcPath = String(inputProps.backgroundImageUrl);
    if (existsSync(srcPath)) {
      const destName = `_bg_${basename(srcPath)}`;
      const destPath = join(publicDir, destName);
      copyFileSync(srcPath, destPath);
      inputProps.backgroundImageUrl = `/${destName}`;
    }
  }

  // Step 1: Bundle the Remotion project
  console.log(`[render-card] Bundling...`);
  const bundleLocation = await bundle({
    entryPoint,
    publicDir,
  });
  console.log(`[render-card] Bundled to: ${bundleLocation}`);

  // Step 2: Get the composition
  const compositions = await getCompositions(bundleLocation, {
    inputProps,
    binariesDirectory,
  });
  const composition = compositions.find((c) => c.id === values.composition);
  if (!composition) {
    const available = compositions.map((c) => c.id).join(", ");
    console.error(
      `[render-card] Composition "${values.composition}" not found. Available: ${available}`,
    );
    process.exit(1);
  }

  console.log(`[render-card] Found composition: ${composition.id}`);

  // Step 3: Render
  console.log(`[render-card] Rendering...`);
  try {
    await renderMedia({
      serveUrl: bundleLocation,
      composition: {
        ...composition,
        durationInFrames,
        fps,
        width,
        height,
      },
      codec: "h264",
      outputLocation: outputPath,
      inputProps,
      hardwareAcceleration,
      ffmpegOverride,
      binariesDirectory,
      onProgress: ({ progress }) => {
        const pct = Math.round(progress * 100);
        if (pct % 10 === 0) {
          console.log(`[render-card] Progress: ${pct}%`);
        }
      },
      // No audio -- the Python backend will mux silent audio via FFmpeg
      muted: true,
    });

    console.log(`[render-card] Done: ${outputPath}`);
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
}

main().catch((err) => {
  console.error("[render-card] Fatal error:", err);
  process.exit(1);
});

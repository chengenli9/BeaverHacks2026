"""Remotion renderer bridge for title/end-card blocks.

Calls the Node.js render-card script as a subprocess to produce
animated MP4 blocks via Remotion, then muxes in a silent audio
track so the output is compatible with the FFmpeg concat pipeline.

If the Remotion toolchain is not available (missing node/npx or
the render-card script), functions raise RemotionNotAvailableError
so the caller can fall back to Pillow+FFmpeg.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..manifests.models import RenderSettings, TextBlock

# Resolve paths relative to this file
_APP_DIR = Path(__file__).resolve().parents[1]  # backend/app/
_BACKEND_DIR = Path(__file__).resolve().parents[2]  # backend/
_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # BeaverHacks2026/
_REMOTION_DIR = _PROJECT_ROOT / "apps" / "remotion"
_RENDER_CARD_SCRIPT = _REMOTION_DIR / "scripts" / "render-card.ts"
_RENDER_GENERATED_SCENE_SCRIPT = _REMOTION_DIR / "scripts" / "render-generated-scene.ts"


class RemotionNotAvailableError(Exception):
    """Raised when the Remotion toolchain is not installed or not found."""


def is_remotion_available() -> bool:
    """Check whether the Remotion rendering pipeline is usable."""
    if not shutil.which("node"):
        return False
    if not _RENDER_CARD_SCRIPT.is_file():
        return False
    if not _RENDER_GENERATED_SCENE_SCRIPT.is_file():
        return False
    if not (_REMOTION_DIR / "node_modules").is_dir():
        return False
    if not (_REMOTION_DIR / "node_modules" / "tsx" / "dist" / "cli.mjs").is_file():
        return False
    return True


def render_generated_remotion_scene(
    project_path: str | Path,
    block: TextBlock,
    settings: RenderSettings,
) -> Path:
    if not block.motion_asset:
        raise RuntimeError(f"Text block {block.block_id} is missing motion_asset")
    if not is_remotion_available():
        raise RemotionNotAvailableError(
            "Remotion toolchain not available. "
            "Install Node.js and run `npm install` in apps/remotion/."
        )

    root = Path(project_path).resolve()
    output = root / block.rendered_path
    output.parent.mkdir(parents=True, exist_ok=True)
    remotion_raw = output.with_suffix(".remotion_raw.mp4")

    _run_generated_scene(
        project_path=root,
        block_id=block.block_id,
        scene_spec_path=root / block.motion_asset.scene_spec_path,
        decorator_module_path=root / block.motion_asset.decorator_module_path if block.motion_asset.decorator_module_path else None,
        output=remotion_raw,
        fps=settings.fps,
        width=settings.width,
        height=settings.height,
        video_codec=settings.video_codec,
        log_dir=root / "logs",
        mode="video",
    )
    _mux_silent_audio(
        input_video=remotion_raw,
        output_video=output,
        duration=block.duration,
        settings=settings,
        log_dir=root / "logs",
    )
    if remotion_raw.exists() and output.exists():
        remotion_raw.unlink()
    return output


def render_remotion_preview(
    project_path: str | Path,
    scene_spec_path: str | Path,
    decorator_module_path: str | Path | None,
    output_path: str | Path,
    settings,
) -> Path:
    project_root = Path(project_path).resolve()
    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    if not is_remotion_available():
        _write_preview_placeholder(scene_spec_path, output, settings)
        return output

    _run_generated_scene(
        project_path=project_root,
        block_id=Path(scene_spec_path).parent.name,
        scene_spec_path=Path(scene_spec_path).resolve(),
        decorator_module_path=Path(decorator_module_path).resolve() if decorator_module_path else None,
        output=output,
        fps=_setting_value(settings, "fps", 30),
        width=_setting_value(settings, "width", 1920),
        height=_setting_value(settings, "height", 1080),
        video_codec="libx264",
        log_dir=project_root / "logs",
        mode="still",
    )
    return output


def render_remotion_card(
    project_path: str | Path,
    block: TextBlock,
    settings: RenderSettings,
    *,
    composition: str | None = None,
) -> Path:
    """Render a title/end-card block via Remotion and return the output path.

    Produces an MP4 with both video and audio streams (silent audio muxed in)
    so it is directly compatible with the concat pipeline.

    Args:
        project_path: Root directory of the project (contains manifests/, renders/).
        block: The TextBlock (TitleBlock or EndCardBlock) to render.
        settings: Render settings (resolution, fps, codec, etc.).
        composition: Remotion composition ID. Defaults to "TitleCard" for title
                     blocks and "EndCard" for end_card blocks.

    Returns:
        Path to the rendered MP4 file.

    Raises:
        RemotionNotAvailableError: If the Remotion toolchain is not installed.
        RuntimeError: If the Remotion render or audio mux fails.
    """
    if not is_remotion_available():
        raise RemotionNotAvailableError(
            "Remotion toolchain not available. "
            "Install Node.js and run `npm install` in apps/remotion/."
        )

    root = Path(project_path).resolve()
    output = root / block.rendered_path
    output.parent.mkdir(parents=True, exist_ok=True)

    # Determine composition ID
    if composition is None:
        composition = "EndCard" if block.type == "end_card" else "TitleCard"

    # Build props dict matching the Remotion CardProps schema
    props: dict = {
        "text": block.text,
        "durationInSeconds": block.duration,
        "backgroundColor": block.background_color or "#111827",
        "backgroundMode": block.background_mode,
        "accentColor": block.accent_color or "#5B8CFF",
        "textColor": block.text_color or "#F9FAFB",
        "textAlignment": block.text_alignment,
        "layoutPreset": block.layout_preset,
        "animationPreset": block.animation_preset or "fade_slide_up",
    }

    # Resolve background image path (absolute) if present
    if block.background_asset:
        bg_path = root / block.background_asset
        if bg_path.exists():
            props["backgroundImageUrl"] = str(bg_path)

    # Step 1: Render animated video via Remotion (no audio)
    remotion_raw = output.with_suffix(".remotion_raw.mp4")
    _run_render_card(
        composition=composition,
        props=props,
        output=str(remotion_raw),
        fps=settings.fps,
        width=settings.width,
        height=settings.height,
        video_codec=settings.video_codec,
        log_dir=root / "logs",
    )

    # Step 2: Mux silent audio into the Remotion output so concat pipeline works
    _mux_silent_audio(
        input_video=remotion_raw,
        output_video=output,
        duration=block.duration,
        settings=settings,
        log_dir=root / "logs",
    )

    # Clean up intermediate file
    if remotion_raw.exists() and output.exists():
        remotion_raw.unlink()

    return output


def _run_render_card(
    *,
    composition: str,
    props: dict,
    output: str,
    fps: int,
    width: int,
    height: int,
    video_codec: str,
    log_dir: Path,
) -> None:
    """Invoke the Node.js render-card.ts script."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "remotion.log"

    command = [
        *_tsx_prefix(),
        str(_RENDER_CARD_SCRIPT),
        "--composition", composition,
        "--props", json.dumps(props),
        "--output", output,
        "--fps", str(fps),
        "--width", str(width),
        "--height", str(height),
        "--video-codec", video_codec,
    ]

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=str(_REMOTION_DIR),
    )

    with log_path.open("a", encoding="utf-8") as log:
        log.write("COMMAND: " + " ".join(command) + "\n")
        log.write(f"RETURN_CODE: {completed.returncode}\n")
        if completed.stdout:
            log.write("STDOUT:\n" + completed.stdout + "\n")
        if completed.stderr:
            log.write("STDERR:\n" + completed.stderr + "\n")

    if completed.returncode != 0:
        raise RuntimeError(
            f"Remotion render failed (exit {completed.returncode}); see {log_path}"
        )

    if not Path(output).exists():
        raise RuntimeError(f"Remotion render produced no output: {output}")


def _run_generated_scene(
    *,
    project_path: Path,
    block_id: str,
    scene_spec_path: Path,
    decorator_module_path: Path | None,
    output: Path,
    fps: int,
    width: int,
    height: int,
    video_codec: str,
    log_dir: Path,
    mode: str,
) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "remotion.log"

    command = [
        *_tsx_prefix(),
        str(_RENDER_GENERATED_SCENE_SCRIPT),
        "--project-path",
        str(project_path),
        "--block-id",
        block_id,
        "--scene-spec",
        str(scene_spec_path),
        "--output",
        str(output),
        "--fps",
        str(fps),
        "--width",
        str(width),
        "--height",
        str(height),
        "--video-codec",
        video_codec,
        "--mode",
        mode,
    ]
    if decorator_module_path:
        command.extend(["--decorator", str(decorator_module_path)])

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        cwd=str(_REMOTION_DIR),
    )

    with log_path.open("a", encoding="utf-8") as log:
        log.write("COMMAND (generated): " + " ".join(command) + "\n")
        log.write(f"RETURN_CODE: {completed.returncode}\n")
        if completed.stdout:
            log.write("STDOUT:\n" + completed.stdout + "\n")
        if completed.stderr:
            log.write("STDERR:\n" + completed.stderr + "\n")

    if completed.returncode != 0:
        raise RuntimeError(
            f"Generated Remotion render failed (exit {completed.returncode}); see {log_path}"
        )
    if not output.exists():
        raise RuntimeError(f"Generated Remotion render produced no output: {output}")


def _mux_silent_audio(
    *,
    input_video: Path,
    output_video: Path,
    duration: float,
    settings: RenderSettings,
    log_dir: Path,
) -> None:
    """Mux a silent audio track into a video file using FFmpeg."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "remotion.log"

    duration_str = f"{duration:.3f}".rstrip("0").rstrip(".")
    command = [
        "ffmpeg", "-y",
        "-i", str(input_video),
        "-f", "lavfi",
        "-t", duration_str,
        "-i", f"anullsrc=channel_layout=stereo:sample_rate={settings.sample_rate}",
        "-c:v", "copy",
        "-c:a", settings.audio_codec,
        "-ar", str(settings.sample_rate),
        "-shortest",
        str(output_video),
    ]

    completed = subprocess.run(command, capture_output=True, text=True)

    with log_path.open("a", encoding="utf-8") as log:
        log.write("COMMAND (mux): " + " ".join(command) + "\n")
        log.write(f"RETURN_CODE: {completed.returncode}\n")
        if completed.stderr:
            log.write("STDERR:\n" + completed.stderr + "\n")

    if completed.returncode != 0:
        raise RuntimeError(
            f"Audio mux failed (exit {completed.returncode}); see {log_path}"
        )


def _write_preview_placeholder(scene_spec_path: str | Path, output_path: Path, settings) -> None:
    from PIL import Image, ImageDraw

    payload = json.loads(Path(scene_spec_path).read_text(encoding="utf-8"))
    width = _setting_value(settings, "width", 1920)
    height = _setting_value(settings, "height", 1080)
    background = payload.get("background_color") or "#111827"
    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    draw.text((80, 80), str(payload.get("text") or "Preview"), fill=payload.get("text_color") or "#F9FAFB")
    image.save(output_path, "PNG")


def _setting_value(settings, key: str, default: int) -> int:
    if isinstance(settings, dict):
        return int(settings.get(key, default))
    return int(getattr(settings, key, default))


def _tsx_prefix() -> list[str]:
    tsx_cli = _REMOTION_DIR / "node_modules" / "tsx" / "dist" / "cli.mjs"
    return ["node", str(tsx_cli)]

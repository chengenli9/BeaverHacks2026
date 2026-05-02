from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from backend.app.manifests.models import Block, BlockManifest, SourceClipBlock, TextBlock
from backend.app.manifests.service import load_manifest, validate_project_assets
from backend.app.rendering.commands import (
    build_concat_command,
    build_source_clip_command,
    build_title_block_command,
)


ProgressCallback = Callable[[float, str], None]


def check_ffmpeg_available() -> None:
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        raise RuntimeError(f"Missing required media tools: {', '.join(missing)}")


def render_block(project_path: str | Path, block: Block, settings) -> Path:
    root = Path(project_path)
    output = root / block.rendered_path
    output.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(block, TextBlock):
        command = build_title_block_command(root, block, settings)
    elif isinstance(block, SourceClipBlock):
        command = build_source_clip_command(
            root,
            block,
            settings,
            source_has_audio=source_has_audio_stream(root / block.source),
        )
    else:
        raise ValueError(f"Unsupported block type: {block.type}")
    _run(command, root / "logs" / "ffmpeg.log")
    return output


def render_project(project_path: str | Path, progress_callback: ProgressCallback | None = None) -> Path:
    root = Path(project_path)
    check_ffmpeg_available()
    manifest = load_manifest(root)
    validate_project_assets(root, manifest)
    total = len(manifest.blocks)

    for index, block in enumerate(manifest.blocks, start=1):
        if progress_callback:
            progress_callback((index - 1) / total, f"Rendering block {index} of {total}")
        render_block(root, block, manifest.render_settings)

    write_concat_file(root, manifest)
    command = build_concat_command(root, manifest)
    _run(command, root / "logs" / "ffmpeg.log")
    final_render = root / "renders" / "final_render.mp4"
    probe_render(final_render)
    if progress_callback:
        progress_callback(1.0, "Render complete")
    return final_render


def write_concat_file(project_path: str | Path, manifest: BlockManifest) -> Path:
    root = Path(project_path)
    concat_path = root / "concat.txt"
    lines = [f"file '{block.rendered_path}'" for block in manifest.blocks]
    concat_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return concat_path


def probe_render(path: str | Path) -> dict:
    render_path = Path(path)
    if not render_path.is_file() or render_path.stat().st_size == 0:
        raise RuntimeError(f"Render is missing or empty: {render_path}")
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration,size",
        "-of",
        "json",
        str(render_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=True)
    return json.loads(completed.stdout)


def source_has_audio_stream(path: str | Path) -> bool:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a",
        "-show_entries",
        "stream=index",
        "-of",
        "json",
        str(path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=True)
    streams = json.loads(completed.stdout).get("streams", [])
    return len(streams) > 0


def _run(command: list[str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(command, capture_output=True, text=True)
    with log_path.open("a", encoding="utf-8") as log:
        log.write("COMMAND: " + " ".join(command) + "\n")
        if completed.stdout:
            log.write(completed.stdout + "\n")
        if completed.stderr:
            log.write(completed.stderr + "\n")
    if completed.returncode != 0:
        raise RuntimeError(f"FFmpeg command failed; see {log_path}")

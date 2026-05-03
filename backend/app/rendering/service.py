from __future__ import annotations

import hashlib
import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from ..manifests.models import Block, BlockManifest, ImageCardBlock, SourceClipBlock, TextBlock
from ..manifests.service import load_manifest, validate_project_assets
from .commands import (
    build_concat_command,
    build_image_card_command,
    build_source_clip_command,
    build_title_block_command,
)
from .remotion_bridge import (
    RemotionNotAvailableError,
    render_generated_remotion_scene,
)

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[float, str], None]


# ---------------------------------------------------------------------------
# NVENC auto-detection (cached for the process lifetime)
# ---------------------------------------------------------------------------

_nvenc_checked: bool | None = None


def _nvenc_available() -> bool:
    global _nvenc_checked
    if _nvenc_checked is not None:
        return _nvenc_checked
    try:
        probe = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=5,
        )
        if "h264_nvenc" not in probe.stdout:
            _nvenc_checked = False
            return False
        gpu = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        _nvenc_checked = gpu.returncode == 0 and bool(gpu.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        _nvenc_checked = False
    return _nvenc_checked


def _effective_codec(requested: str) -> str:
    """Return *h264_nvenc* when an NVIDIA GPU is present; otherwise the
    requested codec (typically *libx264*).  Falls back silently."""
    if requested == "libx264" and _nvenc_available():
        logger.info("h264_nvenc available — using GPU-accelerated encoding")
        return "h264_nvenc"
    return requested


# ---------------------------------------------------------------------------
# Content-addressed render cache
# ---------------------------------------------------------------------------
# Blocks whose content hash + settings are unchanged between renders are
# restored from cache (a simple file copy) instead of being re-encoded.

_CACHE_DIR = "cache/renders"


def _block_content_hash(block: Block, settings) -> str:
    data = block.model_dump(mode="json", exclude={"rendered_path"})
    data["_settings"] = {
        "video_codec": settings.video_codec,
        "width": settings.width,
        "height": settings.height,
        "fps": settings.fps,
        "pixel_format": settings.pixel_format,
    }
    raw = json.dumps(data, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _cache_path(root: Path, content_hash: str) -> Path:
    return root / _CACHE_DIR / f"{content_hash}.mp4"


def _try_restore_from_cache(root: Path, block: Block, settings) -> bool:
    content_hash = _block_content_hash(block, settings)
    cached = _cache_path(root, content_hash)
    if not cached.exists():
        return False
    output = root / block.rendered_path
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cached, output)
    logger.debug("Cache hit for %s (hash=%s)", block.block_id, content_hash)
    return True


def _save_to_cache(root: Path, block: Block, settings) -> None:
    content_hash = _block_content_hash(block, settings)
    cached = _cache_path(root, content_hash)
    cached.parent.mkdir(parents=True, exist_ok=True)
    source = root / block.rendered_path
    if source.exists() and not cached.exists():
        shutil.copy2(source, cached)


# ---------------------------------------------------------------------------
# Core rendering helpers
# ---------------------------------------------------------------------------

def check_ffmpeg_available() -> None:
    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        raise RuntimeError(f"Missing required media tools: {', '.join(missing)}")


def render_block(project_path: str | Path, block: Block, settings) -> Path:
    root = Path(project_path)
    output = root / block.rendered_path
    output.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(block, TextBlock):
        if block.motion_asset:
            try:
                return render_generated_remotion_scene(root, block, settings)
            except Exception as exc:
                logger.warning(
                    "Generated Remotion render failed, falling back to Pillow+FFmpeg: %s", exc
                )
        # Fallback: static Pillow + FFmpeg
        command = build_title_block_command(root, block, settings)
    elif isinstance(block, ImageCardBlock):
        command = build_image_card_command(root, block, settings)
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

    # A) Override video codec to NVENC if GPU is available
    effective_codec = _effective_codec(manifest.render_settings.video_codec)
    if effective_codec != manifest.render_settings.video_codec:
        manifest = manifest.model_copy(
            update={"render_settings": manifest.render_settings.model_copy(update={"video_codec": effective_codec})}
        )

    # B) Render each block (skipping cached blocks)
    total = len(manifest.blocks)
    cached_count = 0

    for index, block in enumerate(manifest.blocks, start=1):
        if progress_callback:
            progress_callback((index - 1) / total, f"Rendering block {index} of {total}")
        if _try_restore_from_cache(root, block, manifest.render_settings):
            cached_count += 1
            continue
        try:
            render_block(root, block, manifest.render_settings)
            _save_to_cache(root, block, manifest.render_settings)
        except Exception as exc:
            raise RuntimeError(f"Failed to render block {block.block_id}: {exc}") from exc

    if cached_count and logger.isEnabledFor(logging.INFO):
        logger.info("Restored %d/%d blocks from render cache", cached_count, total)

    # C) Stream-copy concat (no re-encode)
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
    lines = [f"file '{_safe_concat_path(block.rendered_path)}'" for block in manifest.blocks]
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
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(render_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=True)
    raw_probe = json.loads(completed.stdout)
    streams = raw_probe.get("streams", [])
    has_video = any(stream.get("codec_type") == "video" for stream in streams)
    has_audio = any(stream.get("codec_type") == "audio" for stream in streams)
    if not has_video:
        raise RuntimeError(f"Render is missing a video stream: {render_path}")
    if not has_audio:
        raise RuntimeError(f"Render is missing an audio stream: {render_path}")

    format_info = raw_probe.get("format", {})
    duration = float(format_info.get("duration", 0))
    size_bytes = int(format_info.get("size", render_path.stat().st_size))
    if duration <= 0:
        raise RuntimeError(f"Render has non-positive duration: {render_path}")
    if size_bytes <= 0:
        raise RuntimeError(f"Render has non-positive size: {render_path}")

    return {
        "duration": duration,
        "size_bytes": size_bytes,
        "has_video": has_video,
        "has_audio": has_audio,
        "streams": streams,
    }


def summarize_render(project_id: str, path: str | Path) -> dict:
    render_path = Path(path)
    probe = probe_render(render_path)
    return {
        "project_id": project_id,
        "render_path": str(render_path),
        "duration": probe["duration"],
        "bytes": probe["size_bytes"],
        "has_video": probe["has_video"],
        "has_audio": probe["has_audio"],
    }


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
    import os
    import sys
    import tempfile

    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    # Fix fontconfig on Windows: drawtext crashes without a fonts.conf
    if sys.platform == "win32" or "win" in sys.platform.lower():
        _fc_dir = Path(tempfile.gettempdir()) / "directorloop-fontconfig"
        _fc_dir.mkdir(exist_ok=True)
        _fc_file = _fc_dir / "fonts.conf"
        _fc_file.write_text(
            '<?xml version="1.0"?>\n'
            '<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n'
            '<fontconfig>\n'
            f'  <dir>{os.environ.get("WINDIR", r"C:\\Windows")}\\Fonts</dir>\n'
            '</fontconfig>\n',
            encoding="utf-8",
        )
        env["FONTCONFIG_FILE"] = str(_fc_file)
    completed = subprocess.run(command, capture_output=True, text=True, env=env)
    with log_path.open("a", encoding="utf-8") as log:
        log.write("COMMAND: " + " ".join(command) + "\n")
        log.write(f"RETURN_CODE: {completed.returncode}\n")
        if completed.stdout:
            log.write("STDOUT:\n" + completed.stdout + "\n")
        if completed.stderr:
            log.write("STDERR:\n" + completed.stderr + "\n")
        if not completed.stdout and not completed.stderr:
            log.write("(no output captured)\n")
    if completed.returncode != 0:
        raise RuntimeError(f"FFmpeg command failed; see {log_path}")


def _safe_concat_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith("/") or ":" in normalized or ".." in Path(normalized).parts or "'" in normalized:
        raise ValueError(f"Unsafe concat path: {path}")
    return normalized

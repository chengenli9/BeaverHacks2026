from __future__ import annotations

from pathlib import Path

from ..manifests.models import BlockManifest, RenderSettings, SourceClipBlock, TextBlock


def build_title_block_command(project_path: str | Path, block: TextBlock, settings: RenderSettings) -> list[str]:
    root = Path(project_path)
    output = root / block.rendered_path
    # Pre-render text onto the background using Pillow to avoid FFmpeg drawtext/fontconfig crashes.
    composited = _render_text_overlay(root, block, settings)
    video_filter = (
        f"scale={settings.width}:{settings.height}:force_original_aspect_ratio=increase,"
        f"crop={settings.width}:{settings.height},"
        f"fps={settings.fps},format={settings.pixel_format}"
    )
    return [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-t",
        _seconds(block.duration),
        "-i",
        str(composited),
        "-f",
        "lavfi",
        "-t",
        _seconds(block.duration),
        "-i",
        f"anullsrc=channel_layout=stereo:sample_rate={settings.sample_rate}",
        "-vf",
        video_filter,
        "-r",
        str(settings.fps),
        "-c:v",
        settings.video_codec,
        "-c:a",
        settings.audio_codec,
        "-pix_fmt",
        settings.pixel_format,
        "-shortest",
        str(output),
    ]


def build_source_clip_command(
    project_path: str | Path,
    block: SourceClipBlock,
    settings: RenderSettings,
    *,
    source_has_audio: bool = True,
) -> list[str]:
    root = Path(project_path)
    output = root / block.rendered_path
    command = [
        "ffmpeg",
        "-y",
        "-ss",
        _seconds(block.source_start),
        "-to",
        _seconds(block.source_end),
        "-i",
        str(root / block.source),
    ]
    source_audio_input_index = 0

    if block.tts_asset:
        if not source_has_audio:
            command.extend(
                [
                    "-f",
                    "lavfi",
                    "-t",
                    _seconds(block.video_duration),
                    "-i",
                    f"anullsrc=channel_layout=stereo:sample_rate={settings.sample_rate}",
                ]
            )
            source_audio_input_index = 1
        command.extend(["-i", str(root / block.tts_asset)])
        tts_input_index = source_audio_input_index + 1
        filter_complex = (
            f"[0:v]scale={settings.width}:{settings.height}:force_original_aspect_ratio=increase,"
            f"crop={settings.width}:{settings.height},fps={settings.fps},format={settings.pixel_format}[v];"
            f"[{source_audio_input_index}:a]volume={block.source_audio_volume}[srca];"
            f"[{tts_input_index}:a]afade=t=in:st=0:d={block.tts_fade_seconds},"
            f"afade=t=out:st={max((block.tts_duration or 0) - block.tts_fade_seconds, 0)}:"
            f"d={block.tts_fade_seconds}[ttsa];"
            "[srca][ttsa]amix=inputs=2:duration=longest[a]"
        )
        command.extend(["-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]"])
    else:
        video_filter = (
            f"scale={settings.width}:{settings.height}:force_original_aspect_ratio=increase,"
            f"crop={settings.width}:{settings.height},fps={settings.fps},format={settings.pixel_format}"
        )
        if source_has_audio:
            command.extend(["-vf", video_filter, "-af", f"volume={block.source_audio_volume}"])
        else:
            command.extend(
                [
                    "-f",
                    "lavfi",
                    "-t",
                    _seconds(block.video_duration),
                    "-i",
                    f"anullsrc=channel_layout=stereo:sample_rate={settings.sample_rate}",
                    "-filter_complex",
                    f"[0:v]{video_filter}[v];[1:a]volume={block.source_audio_volume}[a]",
                    "-map",
                    "[v]",
                    "-map",
                    "[a]",
                ]
            )

    command.extend(
        [
            "-r",
            str(settings.fps),
            "-ar",
            str(settings.sample_rate),
            "-c:v",
            settings.video_codec,
            "-c:a",
            settings.audio_codec,
            "-pix_fmt",
            settings.pixel_format,
            str(output),
        ]
    )
    return command


def build_concat_command(project_path: str | Path, manifest: BlockManifest) -> list[str]:
    root = Path(project_path)
    return [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(root / "concat.txt"),
        "-c",
        "copy",
        str(root / "renders" / "final_render.mp4"),
    ]


def _render_text_overlay(root: Path, block: TextBlock, settings: RenderSettings) -> Path:
    """Render text onto the background image using Pillow, return composited path."""
    from PIL import Image, ImageDraw, ImageFont

    bg_path = root / block.background_asset
    font_path = root / block.fontfile

    # Load or create background
    if bg_path.exists():
        img = Image.open(bg_path).convert("RGBA")
    else:
        img = Image.new("RGBA", (settings.width, settings.height), (30, 30, 46, 255))

    # Resize to target if needed
    if img.size != (settings.width, settings.height):
        img = img.resize((settings.width, settings.height), Image.LANCZOS)

    # Load font
    font_size = 96
    if font_path.exists():
        font = ImageFont.truetype(str(font_path), font_size)
    else:
        font = ImageFont.load_default()

    draw = ImageDraw.Draw(img)

    # Calculate text position (centered)
    bbox = draw.textbbox((0, 0), block.text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (settings.width - text_w) // 2
    y = (settings.height - text_h) // 2

    # Draw white text with subtle shadow for readability
    draw.text((x + 2, y + 2), block.text, fill=(0, 0, 0, 180), font=font)
    draw.text((x, y), block.text, fill=(255, 255, 255, 255), font=font)

    # Save composited image in cache dir
    cache_dir = root / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    out_path = cache_dir / f"{block.block_id}_composited.png"
    img.save(str(out_path), "PNG")
    return out_path


def _seconds(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _ffmpeg_path(path: Path) -> str:
    normalized = str(path).replace("\\", "/")
    return normalized.replace(":", "\\:")

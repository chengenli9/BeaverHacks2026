from __future__ import annotations

from pathlib import Path

from backend.app.manifests.models import BlockManifest, RenderSettings, SourceClipBlock, TextBlock


def build_title_block_command(project_path: str | Path, block: TextBlock, settings: RenderSettings) -> list[str]:
    root = Path(project_path)
    output = root / block.rendered_path
    video_filter = (
        f"scale={settings.width}:{settings.height}:force_original_aspect_ratio=increase,"
        f"crop={settings.width}:{settings.height},"
        f"fps={settings.fps},format={settings.pixel_format},"
        f"drawtext=fontfile='{_ffmpeg_path(root / block.fontfile)}':"
        f"text='{_escape_drawtext(block.text)}':"
        "fontcolor=white:fontsize=96:x=(w-text_w)/2:y=(h-text_h)/2"
    )
    return [
        "ffmpeg",
        "-y",
        "-loop",
        "1",
        "-t",
        _seconds(block.duration),
        "-i",
        str(root / block.background_asset),
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

    if block.tts_asset:
        command.extend(["-i", str(root / block.tts_asset)])
        filter_complex = (
            f"[0:v]scale={settings.width}:{settings.height}:force_original_aspect_ratio=increase,"
            f"crop={settings.width}:{settings.height},fps={settings.fps},format={settings.pixel_format}[v];"
            f"[0:a]volume={block.source_audio_volume}[srca];"
            f"[1:a]afade=t=in:st=0:d={block.tts_fade_seconds},"
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
        command.extend(["-vf", video_filter, "-af", f"volume={block.source_audio_volume}"])

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


def _seconds(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _escape_drawtext(value: str) -> str:
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _ffmpeg_path(path: Path) -> str:
    normalized = str(path).replace("\\", "/")
    return normalized.replace(":", "\\:")

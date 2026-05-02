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


def _seconds(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _escape_drawtext(value: str) -> str:
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _ffmpeg_path(path: Path) -> str:
    normalized = str(path).replace("\\", "/")
    return normalized.replace(":", "\\:")

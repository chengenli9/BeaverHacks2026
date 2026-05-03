from __future__ import annotations

import os
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
            "[srca][ttsa]amix=inputs=2:duration=longest:normalize=0[a]"
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
    s = manifest.render_settings
    return [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(root / "concat.txt"),
        "-c:v",
        s.video_codec,
        "-c:a",
        s.audio_codec,
        "-ar",
        str(s.sample_rate),
        "-pix_fmt",
        s.pixel_format,
        str(root / "renders" / "final_render.mp4"),
    ]


def _render_text_overlay(root: Path, block: TextBlock, settings: RenderSettings) -> Path:
    """Render a styled title/end-card composite with Pillow and return the image path."""
    from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont

    img = _build_background_image(root, block, settings)
    draw = ImageDraw.Draw(img)
    text_box = _text_box_for_layout(block.layout_preset, settings.width, settings.height)
    font, lines = _fit_text(
        draw,
        text=block.text,
        font_paths=_font_candidates(root, block),
        max_width=text_box[2] - text_box[0],
        max_height=text_box[3] - text_box[1],
    )

    panel = Image.new("RGBA", img.size, (0, 0, 0, 0))
    panel_draw = ImageDraw.Draw(panel)
    accent_rgb = ImageColor.getrgb(block.accent_color or "#5B8CFF")
    panel_bounds = _panel_bounds(block.layout_preset, text_box)
    panel_draw.rounded_rectangle(panel_bounds, radius=40, fill=(7, 10, 18, 122))
    if block.layout_preset in {"hero-left", "hero-right"}:
        bar_x = panel_bounds[0] + 20 if block.layout_preset == "hero-left" else panel_bounds[2] - 32
        panel_draw.rounded_rectangle((bar_x, panel_bounds[1] + 28, bar_x + 12, panel_bounds[3] - 28), radius=6, fill=accent_rgb + (255,))
    else:
        panel_draw.rounded_rectangle((panel_bounds[0] + 24, panel_bounds[1] + 20, panel_bounds[0] + 220, panel_bounds[1] + 34), radius=7, fill=accent_rgb + (255,))
    panel = panel.filter(ImageFilter.GaussianBlur(1))
    img = Image.alpha_composite(img, panel)

    draw = ImageDraw.Draw(img)
    line_spacing = max(int(font.size * 0.18), 10)
    line_metrics = [draw.textbbox((0, 0), line, font=font) for line in lines]
    total_height = sum((bbox[3] - bbox[1]) for bbox in line_metrics) + line_spacing * max(len(lines) - 1, 0)
    current_y = text_box[1] + ((text_box[3] - text_box[1]) - total_height) / 2

    text_fill = ImageColor.getrgb(block.text_color or "#F9FAFB") + (255,)
    shadow_fill = (0, 0, 0, 168)
    for line, bbox in zip(lines, line_metrics, strict=False):
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]
        if block.text_alignment == "left":
            x = text_box[0]
        elif block.text_alignment == "right":
            x = text_box[2] - line_width
        else:
            x = text_box[0] + ((text_box[2] - text_box[0]) - line_width) / 2
        draw.text((x + 4, current_y + 4), line, fill=shadow_fill, font=font)
        draw.text((x, current_y), line, fill=text_fill, font=font)
        current_y += line_height + line_spacing

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


def _build_background_image(root: Path, block: TextBlock, settings: RenderSettings):
    from PIL import Image, ImageColor, ImageDraw, ImageFilter

    width, height = settings.width, settings.height
    background_color = ImageColor.getrgb(block.background_color or "#111827")
    accent_color = ImageColor.getrgb(block.accent_color or "#5B8CFF")
    background_path = root / block.background_asset if block.background_asset else None

    if background_path and background_path.exists():
        image = Image.open(background_path).convert("RGBA")
        if image.size != (width, height):
            image = image.resize((width, height), Image.LANCZOS)
    else:
        image = Image.new("RGBA", (width, height), background_color + (255,))

    if block.background_mode in {"gradient", "color"} or not (background_path and background_path.exists()):
        base = Image.new("RGBA", (width, height), background_color + (255,))
        if block.background_mode != "color":
            gradient = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            gradient_draw = ImageDraw.Draw(gradient)
            for y in range(height):
                ratio = y / max(height - 1, 1)
                color = tuple(int(background_color[i] + (accent_color[i] - background_color[i]) * min(ratio * 0.65, 1.0)) for i in range(3))
                gradient_draw.line((0, y, width, y), fill=color + (255,))
            base = gradient
        image = base

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.ellipse((width * 0.5, height * 0.08, width * 1.05, height * 0.82), fill=accent_color + (92,))
    overlay_draw.rectangle((width * 0.05, height * 0.72, width * 0.4, height * 0.92), fill=accent_color + (38,))
    overlay = overlay.filter(ImageFilter.GaussianBlur(92))
    image = Image.alpha_composite(image, overlay)

    if block.background_mode == "image_tint":
        tint = Image.new("RGBA", (width, height), background_color + (72,))
        tint_overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        tint_draw = ImageDraw.Draw(tint_overlay)
        for y in range(height):
            ratio = y / max(height - 1, 1)
            alpha = int(46 + 90 * ratio)
            tint_draw.line((0, y, width, y), fill=accent_color + (alpha,))
        image = Image.alpha_composite(image, tint)
        image = Image.alpha_composite(image, tint_overlay)

    return image


def _font_candidates(root: Path, block: TextBlock) -> list[Path]:
    repo_font = Path(__file__).resolve().parents[2] / "assets" / "fonts" / "Inter-Bold.ttf"
    project_font = root / block.fontfile
    windows_fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    curated = {
        "clean-sans": ["Inter-Bold.ttf", "bahnschrift.ttf", "arialbd.ttf", "segoeuib.ttf"],
        "display-sans": ["impact.ttf", "bahnschrift.ttf", "arialbd.ttf"],
        "display-serif": ["georgiab.ttf", "timesbd.ttf", "cambria.ttc"],
        "mono-tech": ["consolab.ttf", "lucon.ttf", "courbd.ttf"],
        "editorial": ["georgiab.ttf", "GARA.TTF", "cambria.ttc"],
    }

    candidates: list[Path] = []
    if project_font.suffix.lower() in {".ttf", ".otf", ".ttc"}:
        candidates.append(project_font)

    family = (block.font_family or "clean-sans").lower()
    if "." in family:
        candidates.append(root / "assets" / "fonts" / family)
    for name in curated.get(family, curated["clean-sans"]):
        if name.lower() == "inter-bold.ttf":
            candidates.append(repo_font)
        else:
            candidates.append(windows_fonts / name)
    candidates.append(repo_font)
    return candidates


def _fit_text(draw, *, text: str, font_paths: list[Path], max_width: float, max_height: float):
    from PIL import ImageFont

    for font_size in range(144, 39, -6):
        font = _load_font(font_paths, font_size)
        lines = _wrap_text(draw, text, font, max_width)
        if not lines:
            continue
        boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
        line_spacing = max(int(font.size * 0.18), 10)
        height = sum((box[3] - box[1]) for box in boxes) + line_spacing * max(len(lines) - 1, 0)
        width = max((box[2] - box[0]) for box in boxes)
        if width <= max_width and height <= max_height:
            return font, lines
    fallback = ImageFont.load_default()
    return fallback, _wrap_text(draw, text, fallback, max_width) or [text]


def _load_font(font_paths: list[Path], font_size: int):
    from PIL import ImageFont

    for font_path in font_paths:
        if font_path.exists():
            try:
                return ImageFont.truetype(str(font_path), font_size)
            except OSError:
                continue
    return ImageFont.load_default()


def _wrap_text(draw, text: str, font, max_width: float) -> list[str]:
    paragraphs = [part.strip() for part in text.splitlines()] or [text]
    lines: list[str] = []
    for paragraph in paragraphs:
        if not paragraph:
            lines.append("")
            continue
        words = paragraph.split()
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            bbox = draw.textbbox((0, 0), candidate, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def _text_box_for_layout(layout_preset: str, width: int, height: int) -> tuple[float, float, float, float]:
    boxes = {
        "centered": (width * 0.16, height * 0.22, width * 0.84, height * 0.78),
        "hero-left": (width * 0.1, height * 0.18, width * 0.54, height * 0.82),
        "hero-right": (width * 0.46, height * 0.18, width * 0.9, height * 0.82),
        "stacked": (width * 0.14, height * 0.18, width * 0.86, height * 0.68),
    }
    return boxes.get(layout_preset, boxes["centered"])


def _panel_bounds(layout_preset: str, text_box: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    left, top, right, bottom = text_box
    if layout_preset == "stacked":
        return (left - 28, top - 24, right + 28, bottom + 42)
    return (left - 34, top - 30, right + 34, bottom + 30)

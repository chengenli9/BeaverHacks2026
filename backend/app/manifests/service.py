from __future__ import annotations

import json
import math
from pathlib import Path

import struct

from pydantic import TypeAdapter

from .models import (
    ApplyPatchesRequest,
    Block,
    BlockManifest,
    CriticSuggestions,
    EndCardBlock,
    Plan,
    SceneIndex,
    SourceClipBlock,
    TextBlock,
)


def load_scene_index(project_path: str | Path) -> SceneIndex:
    return SceneIndex.from_file(Path(project_path) / "cache" / "scene_index.json")


def load_plan(project_path: str | Path) -> Plan:
    return Plan.from_file(Path(project_path) / "manifests" / "plan.json")


def load_manifest(project_path: str | Path) -> BlockManifest:
    return BlockManifest.from_file(Path(project_path) / "manifests" / "block_manifest.json")


def write_manifest(project_path: str | Path, manifest: BlockManifest) -> Path:
    manifest_path = Path(project_path) / "manifests" / "block_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def build_manifest(project_path: str | Path) -> BlockManifest:
    scene_index = load_scene_index(project_path)
    plan = load_plan(project_path)
    plan.validate_against_scene_index(scene_index)
    manifest = build_manifest_from_plan(project_path)
    # build_manifest_from_plan already reconciles and validates
    write_manifest(project_path, manifest)
    return manifest


def build_manifest_from_plan(
    project_path: str | Path,
    *,
    tts_durations: dict[str, float] | None = None,
) -> BlockManifest:
    scene_index = load_scene_index(project_path)
    plan = load_plan(project_path)
    plan.validate_against_scene_index(scene_index)
    tts_durations = tts_durations or {}
    blocks: list[dict] = []

    for index, beat in enumerate(plan.beats, start=1):
        ordinal = f"{index:03d}"
        style = beat.style.model_dump(mode="json", exclude_none=True) if getattr(beat, "style", None) else {}
        if beat.type == "title":
            blocks.append(
                {
                    "block_id": f"{ordinal}_title",
                    "type": "title",
                    "background_asset": f"assets/backgrounds/bg_{ordinal}.png",
                    "text": beat.onscreen_text or plan.title,
                    "duration": beat.duration,
                    "fontfile": "assets/fonts/Inter-Bold.ttf",
                    **style,
                    "rendered_path": f"blocks/{ordinal}_title.mp4",
                }
            )
        elif beat.type == "end_card":
            blocks.append(
                {
                    "block_id": f"{ordinal}_end",
                    "type": "end_card",
                    "background_asset": f"assets/backgrounds/bg_{ordinal}.png",
                    "text": beat.onscreen_text or plan.title,
                    "duration": beat.duration,
                    "fontfile": "assets/fonts/Inter-Bold.ttf",
                    **style,
                    "rendered_path": f"blocks/{ordinal}_end.mp4",
                }
            )
        elif beat.type == "source_clip":
            scene = scene_index.scene_by_id(beat.scene_id or "")
            source_start = scene.start
            requested_end = source_start + _snap_duration_seconds(beat.duration)
            source_end = min(requested_end, scene.end, scene_index.source_duration)
            source_end = _quantize_source_end(source_start, source_end)
            video_duration = source_end - source_start
            tts_duration = tts_durations.get(beat.beat_id)
            tts_asset = _tts_asset_for_beat(beat.beat_id) if beat.narration and tts_duration is not None else None
            blocks.append(
                {
                    "block_id": f"{ordinal}_{beat.beat_id}",
                    "type": "source_clip",
                    "source": scene_index.source,
                    "source_start": source_start,
                    "source_end": source_end,
                    "video_duration": video_duration,
                    "tts_asset": tts_asset,
                    "tts_duration": tts_duration if tts_asset else None,
                    "source_audio_volume": 0.15,
                    "tts_fade_seconds": 0.5,
                    "rendered_path": f"blocks/{ordinal}_{beat.beat_id}.mp4",
                }
            )

    manifest = BlockManifest.model_validate(
        {
            "project_id": plan.project_id,
            "version": 1,
            "render_settings": {},
            "blocks": blocks,
        }
    )
    reconciled = reconcile_durations(manifest, max_source_end=scene_index.source_duration)
    validate_manifest_source_bounds(reconciled, scene_index)
    return reconciled


def reconcile_durations(
    manifest: BlockManifest,
    *,
    max_source_end: float | None = None,
) -> BlockManifest:
    updated_blocks: list[Block] = []
    adapter = TypeAdapter(Block)
    for block in manifest.blocks:
        if isinstance(block, SourceClipBlock):
            block_data = block.model_dump()
            video_duration = block.source_end - block.source_start
            tts_duration = block.tts_duration or 0
            if tts_duration > video_duration:
                desired_end = block.source_start + tts_duration
                block_data["source_end"] = min(desired_end, max_source_end) if max_source_end else desired_end
                block_data["video_duration"] = block_data["source_end"] - block.source_start
            else:
                block_data["video_duration"] = video_duration
            updated_blocks.append(adapter.validate_python(block_data))
        else:
            updated_blocks.append(block)
    return manifest.model_copy(update={"blocks": updated_blocks})


def validate_project_assets(
    project_path: str | Path,
    manifest: BlockManifest,
    *,
    require_media: bool = True,
) -> None:
    root = Path(project_path)
    for block in manifest.blocks:
        if isinstance(block, TextBlock):
            _require_file(root, block.fontfile)
            if require_media:
                _require_file(root, block.background_asset)
        if isinstance(block, SourceClipBlock) and require_media:
            _require_file(root, block.source)
            if block.tts_asset:
                _require_file(root, block.tts_asset)


def validate_manifest_source_bounds(manifest: BlockManifest, scene_index: SceneIndex) -> None:
    for block in manifest.blocks:
        if not isinstance(block, SourceClipBlock):
            continue
        if block.source != scene_index.source:
            raise ValueError(
                f"source_clip block {block.block_id} source {block.source} "
                f"does not match scene index source {scene_index.source}"
            )
        if block.source_end > scene_index.source_duration:
            raise ValueError(
                f"source_clip block {block.block_id} exceeds source_duration "
                f"{scene_index.source_duration}"
            )


def validate_critic_suggestions(manifest: BlockManifest, suggestions: CriticSuggestions) -> None:
    for suggestion in suggestions.suggestions:
        block = manifest.block_by_id(suggestion.block_id)
        if suggestion.action == "trim_end":
            if isinstance(block, SourceClipBlock) and suggestion.amount_seconds >= block.video_duration:
                raise ValueError("trim amount must leave a positive source clip duration")
        if suggestion.action == "reorder_after":
            manifest.block_by_id(suggestion.target_block_id or "")


def apply_suggestions_to_manifest(
    manifest: BlockManifest,
    suggestions: CriticSuggestions,
    request: ApplyPatchesRequest,
) -> BlockManifest:
    approved_ids = set(request.approved_suggestion_ids)
    known_ids = {suggestion.suggestion_id for suggestion in suggestions.suggestions}
    unknown_approved_ids = approved_ids - known_ids
    if unknown_approved_ids:
        raise KeyError(f"Unknown approved suggestion_id values: {sorted(unknown_approved_ids)}")

    updated_blocks: list[Block] = list(manifest.blocks)
    adapter = TypeAdapter(Block)

    for suggestion in suggestions.suggestions:
        if suggestion.suggestion_id not in approved_ids:
            continue

        index = _block_index(updated_blocks, suggestion.block_id)
        block = updated_blocks[index]
        if not _suggestion_is_actionable(manifest, suggestion):
            continue
        block_data = block.model_dump()

        if suggestion.action == "trim_end":
            block_data["source_end"] = _quantize_source_end(
                block.source_start,
                block.source_end - _snap_duration_seconds(suggestion.amount_seconds),
            )
            block_data["video_duration"] = block_data["source_end"] - block.source_start
        elif suggestion.action == "extend_end":
            block_data["source_end"] = _quantize_source_end(
                block.source_start,
                block.source_end + _snap_duration_seconds(suggestion.amount_seconds),
            )
            block_data["video_duration"] = block_data["source_end"] - block.source_start
        elif suggestion.action == "replace_text":
            block_data["text"] = suggestion.replacement_text
        elif suggestion.action == "lower_source_audio":
            block_data["source_audio_volume"] = suggestion.source_audio_volume
        elif suggestion.action == "reorder_after":
            target_index = _block_index(updated_blocks, suggestion.target_block_id or "")
            moving_block = updated_blocks.pop(index)
            if target_index > index:
                target_index -= 1
            updated_blocks.insert(target_index + 1, moving_block)
            continue

        updated_blocks[index] = adapter.validate_python(block_data)

    return reconcile_durations(manifest.model_copy(update={"blocks": updated_blocks}))


def apply_approved_patches(project_path: str | Path, request: ApplyPatchesRequest) -> BlockManifest:
    root = Path(project_path)
    manifest = load_manifest(root)
    suggestions = CriticSuggestions.from_file(root / "manifests" / "critic_suggestions.json")
    patched = apply_suggestions_to_manifest(manifest, suggestions, request)
    write_manifest(root, patched)
    return patched


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _require_file(project_root: Path, relative_path: str) -> None:
    path = project_root / relative_path
    if path.is_file():
        return
    if relative_path.startswith("assets/fonts/") and Path(relative_path).suffix.lower() in {".ttf", ".otf"}:
        return
    # Auto-generate a placeholder solid-color PNG for missing backgrounds
    if relative_path.startswith("assets/backgrounds/") and relative_path.endswith(".png"):
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_placeholder_png(path)
        return
    raise FileNotFoundError(f"Missing required project asset: {relative_path}")


def _write_placeholder_png(path: Path) -> None:
    """Write a 1920x1080 dark grey PNG. Uses Pillow if available, falls back to raw PNG."""
    w, h = 1920, 1080
    try:
        from PIL import Image
        img = Image.new("RGB", (w, h), (30, 30, 46))
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(path), "PNG")
    except ImportError:
        import zlib
        # Raw filter byte (0) + RGB pixels per row, no trailing byte
        row = bytes([0]) + bytes([30, 30, 46]) * w
        raw = row * h
        def _chunk(ctype, data):
            c = ctype + data
            return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
        compressed = zlib.compress(raw)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", compressed) + _chunk(b"IEND", b""))


def _block_duration(block: Block) -> float:
    if isinstance(block, SourceClipBlock):
        return block.video_duration
    return block.duration


def _suggestion_is_actionable(manifest: BlockManifest, suggestion) -> bool:
    block = manifest.block_by_id(suggestion.block_id)

    if suggestion.action in {"trim_end", "extend_end", "lower_source_audio"} and not isinstance(block, SourceClipBlock):
        return False
    if suggestion.action == "replace_text" and not isinstance(block, TextBlock):
        return False
    if suggestion.action == "replace_text" and not suggestion.replacement_text:
        return False
    if suggestion.action == "lower_source_audio" and suggestion.source_audio_volume is None:
        return False
    if suggestion.action == "reorder_after":
        try:
            manifest.block_by_id(suggestion.target_block_id or "")
        except KeyError:
            return False
    if suggestion.action == "trim_end":
        if isinstance(block, SourceClipBlock) and suggestion.amount_seconds >= block.video_duration:
            return False
    return True


def _block_index(blocks: list[Block], block_id: str) -> int:
    for index, block in enumerate(blocks):
        if block.block_id == block_id:
            return index
    raise KeyError(f"Unknown block_id: {block_id}")


def _tts_asset_for_beat(beat_id: str) -> str:
    return f"assets/tts/tts_{beat_id}.wav"


def _snap_duration_seconds(value: float) -> float:
    if value <= 0:
        return value
    if value < 1:
        return round(value, 3)
    snapped = math.floor(value)
    return float(snapped if snapped > 0 else 1)


def _quantize_source_end(source_start: float, source_end: float) -> float:
    duration = max(source_end - source_start, 0.0)
    snapped_duration = _snap_duration_seconds(duration)
    if snapped_duration <= 0:
        return source_end
    return round(source_start + snapped_duration, 3)

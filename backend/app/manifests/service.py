from __future__ import annotations

import json
import math
from pathlib import Path

import struct

from pydantic import TypeAdapter

from .models import (
    BeatStyle,
    ApplyPatchesRequest,
    Block,
    BlockManifest,
    CreateBeatRequest,
    CriticSuggestions,
    EndCardBlock,
    Plan,
    PlanBeat,
    PlanEditPromptRequest,
    PlanReorderRequest,
    SceneCardBlock,
    SceneIndex,
    SourceClipBlock,
    TextBlock,
)


def load_scene_index(project_path: str | Path) -> SceneIndex:
    return SceneIndex.from_file(Path(project_path) / "cache" / "scene_index.json")


def load_plan(project_path: str | Path) -> Plan:
    return Plan.from_file(Path(project_path) / "manifests" / "plan.json")


def write_plan(project_path: str | Path, plan: Plan) -> Path:
    plan_path = Path(project_path) / "manifests" / "plan.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        json.dumps(plan.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return plan_path


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


def reorder_plan_beats(
    project_path: str | Path,
    request: PlanReorderRequest,
    *,
    progress_callback=None,
) -> Plan:
    root = Path(project_path)
    plan = load_plan(root)
    order = request.beat_order
    existing_ids = [beat.beat_id for beat in plan.beats]
    if set(order) != set(existing_ids) or len(order) != len(existing_ids):
        raise ValueError("beat_order must include every existing beat exactly once")
    beat_map = {beat.beat_id: beat for beat in plan.beats}
    reordered = [beat_map[beat_id].model_dump(mode="json") for beat_id in order]
    updated = plan.model_copy(update={"beats": _renumber_plan_beats(reordered)})
    updated = Plan.model_validate(updated.model_dump(mode="json"))
    write_plan(root, updated)
    _rebuild_manifest_only(root, progress_callback=progress_callback)
    return updated


def delete_plan_beat(
    project_path: str | Path,
    beat_id: str,
    *,
    progress_callback=None,
) -> Plan:
    root = Path(project_path)
    plan = load_plan(root)
    remaining = [beat.model_dump(mode="json") for beat in plan.beats if beat.beat_id != beat_id]
    if len(remaining) == len(plan.beats):
        raise KeyError(f"Unknown beat_id: {beat_id}")
    if not remaining:
        raise ValueError("plan must contain at least one beat")
    updated = plan.model_copy(update={"beats": _renumber_plan_beats(remaining)})
    updated = Plan.model_validate(updated.model_dump(mode="json"))
    write_plan(root, updated)
    _rebuild_manifest_only(root, progress_callback=progress_callback)
    return updated


def insert_plan_beat(
    project_path: str | Path,
    request: CreateBeatRequest,
    *,
    progress_callback=None,
) -> Plan:
    root = Path(project_path)
    plan = load_plan(root)
    new_beat = _build_plan_beat_for_insert(request)
    beats = [beat.model_dump(mode="json") for beat in plan.beats]
    insert_index = len(beats)
    if request.insert_after is not None:
        for index, beat in enumerate(plan.beats):
            if beat.beat_id == request.insert_after:
                insert_index = index + 1
                break
        else:
            raise KeyError(f"Unknown beat_id: {request.insert_after}")
    beats.insert(insert_index, new_beat)
    updated = plan.model_copy(update={"beats": _renumber_plan_beats(beats)})
    updated = Plan.model_validate(updated.model_dump(mode="json"))
    write_plan(root, updated)
    _rebuild_manifest_only(root, progress_callback=progress_callback)
    return updated


def update_plan_beat(
    project_path: str | Path,
    beat_id: str,
    updates: dict,
    *,
    progress_callback=None,
) -> Plan:
    root = Path(project_path)
    plan = load_plan(root)
    beat_index = next((i for i, b in enumerate(plan.beats) if b.beat_id == beat_id), None)
    if beat_index is None:
        raise KeyError(f"Unknown beat_id: {beat_id}")
    beats = [b.model_dump(mode="json") for b in plan.beats]
    beats[beat_index].update(updates)
    updated = plan.model_copy(update={"beats": _renumber_plan_beats(beats)})
    updated = Plan.model_validate(updated.model_dump(mode="json"))
    write_plan(root, updated)
    _rebuild_manifest_only(root, progress_callback=progress_callback)
    return updated


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
            motion_block_id = f"{ordinal}_title"
        elif beat.type == "end_card":
            motion_block_id = f"{ordinal}_end"
        elif beat.type == "scene_card":
            motion_block_id = f"{ordinal}_{beat.beat_id}"
        else:
            motion_block_id = None
        motion_asset = _motion_asset_for_block(project_path, motion_block_id) if motion_block_id else None
        if beat.type == "title":
            blocks.append(
                {
                    "block_id": f"{ordinal}_title",
                    "type": "title",
                    "background_asset": f"assets/backgrounds/bg_{ordinal}.png",
                    "text": beat.onscreen_text or plan.title,
                    "duration": beat.duration,
                    "fontfile": "assets/fonts/Inter-Bold.ttf",
                    "motion_asset": motion_asset,
                    **style,
                    "rendered_path": f"blocks/{ordinal}_title.mp4",
                }
            )
        elif beat.type == "scene_card":
            blocks.append(
                {
                    "block_id": f"{ordinal}_{beat.beat_id}",
                    "type": "scene_card",
                    "background_asset": f"assets/backgrounds/bg_{ordinal}.png",
                    "text": beat.onscreen_text or beat.goal,
                    "duration": beat.duration,
                    "fontfile": "assets/fonts/Inter-Bold.ttf",
                    "motion_asset": motion_asset,
                    **style,
                    "rendered_path": f"blocks/{ordinal}_{beat.beat_id}.mp4",
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
                    "motion_asset": motion_asset,
                    **style,
                    "rendered_path": f"blocks/{ordinal}_end.mp4",
                }
            )
        elif beat.type == "image_card":
            blocks.append(
                {
                    "block_id": f"{ordinal}_{beat.beat_id}",
                    "type": "image_card",
                    "image_prompt": beat.image_prompt,
                    "image_asset": _image_asset_for_prompt(beat.image_prompt or ""),
                    "duration": beat.duration,
                    "ken_burns": beat.ken_burns,
                    "rendered_path": f"blocks/{ordinal}_{beat.beat_id}.mp4",
                }
            )
        elif beat.type == "source_clip":
            scene = scene_index.scene_by_id(beat.scene_id or "")
            source_meta = scene_index.source_by_path(scene.source)
            source_start = round(scene.start - source_meta.start_offset_seconds, 3)
            scene_local_end = round(scene.end - source_meta.start_offset_seconds, 3)
            requested_end = source_start + _snap_duration_seconds(beat.duration)
            source_end = min(requested_end, scene_local_end, source_meta.duration_seconds)
            source_end = _quantize_source_end(source_start, source_end)
            video_duration = source_end - source_start
            tts_duration = tts_durations.get(beat.beat_id)
            tts_asset = _tts_asset_for_beat(beat.beat_id) if beat.narration and tts_duration is not None else None
            blocks.append(
                {
                    "block_id": f"{ordinal}_{beat.beat_id}",
                    "type": "source_clip",
                    "source": scene.source,
                    "source_start": source_start,
                    "source_end": source_end,
                    "video_duration": video_duration,
                    "tts_asset": tts_asset,
                    "tts_duration": tts_duration if tts_asset else None,
                    "source_audio_volume": 1.0,
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
            "audio_tracks": [t.model_dump(mode="json") for t in plan.audio_tracks],
        }
    )
    reconciled = reconcile_durations(manifest, source_duration_by_path=scene_index.source_duration_map())
    validate_manifest_source_bounds(reconciled, scene_index)
    return reconciled


def reconcile_durations(
    manifest: BlockManifest,
    *,
    source_duration_by_path: dict[str, float] | None = None,
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
                max_source_end = source_duration_by_path.get(block.source) if source_duration_by_path else None
                block_data["source_end"] = min(desired_end, max_source_end) if max_source_end is not None else desired_end
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
            if require_media and block.background_asset:
                _require_file(root, block.background_asset)
        if getattr(block, "type", None) == "image_card" and require_media:
            _require_file(root, block.image_asset)
        if isinstance(block, SourceClipBlock) and require_media:
            _require_file(root, block.source)
            if block.tts_asset:
                _require_file(root, block.tts_asset)


def validate_manifest_source_bounds(manifest: BlockManifest, scene_index: SceneIndex) -> None:
    for block in manifest.blocks:
        if not isinstance(block, SourceClipBlock):
            continue
        try:
            source_meta = scene_index.source_by_path(block.source)
        except KeyError as exc:
            raise ValueError(f"source_clip block {block.block_id} references unknown source {block.source}") from exc
        if block.source_end > source_meta.duration_seconds:
            raise ValueError(
                f"source_clip block {block.block_id} exceeds source_duration "
                f"{source_meta.duration_seconds}"
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
    scene_index = load_scene_index(root)
    suggestions = CriticSuggestions.from_file(root / "manifests" / "critic_suggestions.json")
    patched = apply_suggestions_to_manifest(manifest, suggestions, request)
    validate_manifest_source_bounds(patched, scene_index)
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


def _motion_asset_for_block(project_path: str | Path, block_id: str) -> dict | None:
    root = Path(project_path)
    scene_spec = root / "assets" / "remotion" / block_id / "scene.json"
    if not scene_spec.exists():
        return None
    decorator = root / "assets" / "remotion" / block_id / "decorator.tsx"
    preview = root / "assets" / "remotion" / block_id / "preview.png"
    return {
        "kind": "remotion_scene",
        "runtime_template": _runtime_template_for_scene(scene_spec),
        "scene_spec_path": _relative_project_path(root, scene_spec),
        "decorator_module_path": _relative_project_path(root, decorator) if decorator.exists() else None,
        "preview_frame_path": _relative_project_path(root, preview) if preview.exists() else None,
    }


def _runtime_template_for_scene(scene_spec_path: Path) -> str:
    try:
        payload = json.loads(scene_spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "hero-reveal"
    return str(payload.get("runtime_template") or "hero-reveal")


def _relative_project_path(project_root: Path, path: Path) -> str:
    return path.relative_to(project_root).as_posix()


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


def _renumber_plan_beats(beats: list[dict]) -> list[dict]:
    renumbered: list[dict] = []
    for index, beat in enumerate(beats, start=1):
        item = dict(beat)
        item["beat_id"] = f"beat_{index:03d}"
        renumbered.append(item)
    return renumbered


def _build_plan_beat_for_insert(request: CreateBeatRequest) -> dict:
    if request.type == "scene_card":
        return {
            "beat_id": "beat_pending",
            "type": "scene_card",
            "goal": request.text,
            "scene_id": None,
            "duration": request.duration,
            "narration": None,
            "onscreen_text": request.text,
            "style": request.style.model_dump(mode="json") if request.style else None,
            "image_prompt": None,
            "ken_burns": False,
        }
    return {
        "beat_id": "beat_pending",
        "type": "image_card",
        "goal": request.text or "Generated image beat",
        "scene_id": None,
        "duration": request.duration,
        "narration": None,
        "onscreen_text": request.text,
        "style": None,
        "image_prompt": request.image_prompt,
        "ken_burns": request.ken_burns,
    }


def _regenerate_after_plan_mutation(project_path: Path, *, progress_callback=None) -> None:
    """Full pipeline: Gemini asset gen + manifest rebuild + render.
    Used for insert/edit where new content needs AI generation."""
    from ..integrations.gemini.service import generate_background_assets
    from ..rendering.service import render_project

    if progress_callback:
        progress_callback(0.15, "Refreshing generated assets")
    generate_background_assets(project_path)
    if progress_callback:
        progress_callback(0.5, "Rebuilding manifest")
    build_manifest(project_path)
    if progress_callback:
        progress_callback(0.7, "Rendering updated cut")
    render_project(project_path, progress_callback=None if progress_callback is None else _nested_progress(progress_callback, 0.7, 1.0))


def _rebuild_manifest_only(project_path: Path, *, progress_callback=None) -> None:
    """Plan-only path: refresh manifest ordering/data without regenerating media."""
    (project_path / "manifests" / "proposed_plan.json").unlink(missing_ok=True)
    if progress_callback:
        progress_callback(0.35, "Rebuilding manifest")
    build_manifest(project_path)
    if progress_callback:
        progress_callback(1.0, "Plan updated")


def _rebuild_manifest_and_render(project_path: Path, *, progress_callback=None) -> None:
    """Lightweight path: deterministic manifest rebuild + render only.
    Used for reorder/delete where no new assets are needed."""
    from ..rendering.service import render_project

    if progress_callback:
        progress_callback(0.3, "Rebuilding manifest")
    build_manifest(project_path)
    if progress_callback:
        progress_callback(0.6, "Rendering updated cut")
    render_project(project_path, progress_callback=None if progress_callback is None else _nested_progress(progress_callback, 0.6, 1.0))


def _nested_progress(progress_callback, start: float, end: float):
    span = max(end - start, 0)

    def callback(progress: float, message: str):
        progress_callback(start + span * progress, message)

    return callback


def _image_asset_for_prompt(image_prompt: str) -> str:
    import hashlib

    digest = hashlib.sha1(image_prompt.encode("utf-8")).hexdigest()[:12]
    return f"assets/images/image_{digest}.png"

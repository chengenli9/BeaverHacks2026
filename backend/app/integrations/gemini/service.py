"""High-level Gemini service functions for DirectorLoop."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import client as _client
from .settings import GEMINI_IMAGE_MODEL
from ...manifests.models import BlockManifest, CriticSuggestions, Plan, SceneIndex
from ...manifests.service import _suggestion_is_actionable
from ...media.models import MediaProbe, RenderQa, ShotIndex
from ...media.service import _extract_frame, build_render_qa, detect_shots, find_primary_video, inspect_source_media
from ...remotion.models import GeneratedTextSceneBundle, GeneratedTextSceneSpec
from ...rendering.remotion_bridge import render_remotion_preview


_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def analyze_scenes(project_path: Path, progress_callback=None) -> dict:
    project_path = Path(project_path)
    project_id = project_path.name
    video_file = find_primary_video(project_path)

    if video_file:
        if progress_callback:
            progress_callback(0.1, "Inspecting source media")
        media_probe = inspect_source_media(project_path)

        if progress_callback:
            progress_callback(0.35, "Detecting shots and sampling frames")
        shot_index = detect_shots(project_path, media_probe)
    else:
        media_probe = _fallback_media_probe(project_path)
        shot_index = _fallback_shot_index(project_path, media_probe)

    system_prompt = _load_prompt("scene_analysis")
    user_prompt = (
        f"Project ID: {project_id}\n\n"
        "Source media probe:\n"
        f"{media_probe.model_dump_json(indent=2)}\n\n"
        "Detected shots:\n"
        f"{shot_index.model_dump_json(indent=2)}\n\n"
        "Label the footage into a scene_index response. Reuse the measured shot boundaries unless there is a very strong reason not to. "
        "Do not invent file paths or durations beyond the measured source duration."
    )

    if progress_callback:
        progress_callback(0.65, "Generating scene index")

    if video_file:
        result, usage = _client.complete_json_with_file(
            user_prompt,
            video_file,
            mime_type="video/mp4",
            system=system_prompt,
            schema=SceneIndex.model_json_schema(),
        )
    else:
        result, usage = _client.complete_json(
            user_prompt,
            system=system_prompt,
            schema=SceneIndex.model_json_schema(),
        )

    result["project_id"] = project_id
    result["source"] = media_probe.source
    result["source_duration"] = media_probe.duration_seconds
    result = _normalize_scene_index_result(result, media_probe.duration_seconds)
    scene_index = SceneIndex.model_validate(result)

    out_path = project_path / "cache" / "scene_index.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(scene_index.model_dump_json(indent=2), encoding="utf-8")

    if video_file:
        frames_dir = project_path / "cache" / "frames"
        frames_dir.mkdir(parents=True, exist_ok=True)
        for scene in scene_index.scenes:
            mid = (scene.start + scene.end) / 2
            frame_out = frames_dir / f"{scene.scene_id}_mid.jpg"
            try:
                _extract_frame(video_file, mid, frame_out)
            except Exception:
                pass

    _log_call(
        project_path=project_path,
        project_id=project_id,
        stage="scene_analysis",
        model=usage["model"],
        elapsed_ms=usage["elapsed_ms"],
        input_tokens=usage["input_token_count"],
        output_tokens=usage["output_token_count"],
        artifact_path=str(out_path.relative_to(project_path)),
    )

    if progress_callback:
        progress_callback(1.0, "Scene analysis complete")
    return scene_index.model_dump(mode="json")


def generate_plan(project_path: Path) -> dict:
    project_path = Path(project_path)
    project_id = project_path.name
    scene_index = SceneIndex.from_file(project_path / "cache" / "scene_index.json")
    shot_index = _maybe_load(ShotIndex, project_path / "cache" / "shot_index.json")
    media_probe = _maybe_load(MediaProbe, project_path / "cache" / "media_probe.json")

    system_prompt = _load_prompt("plan_generation")
    user_prompt = (
        f"Project ID: {project_id}\n\n"
        "Scene index:\n"
        f"{scene_index.model_dump_json(indent=2)}\n\n"
        "Shot index:\n"
        f"{shot_index.model_dump_json(indent=2) if shot_index else '{}'}\n\n"
        "Media probe:\n"
        f"{media_probe.model_dump_json(indent=2) if media_probe else '{}'}\n\n"
        "Generate a plan response matching the API contract. "
        "For title, scene_card, and end_card beats, provide a style object when it helps the demo feel more distinctive. "
        "Narration should stay concise, but TTS precision is not the priority for this demo."
    )

    result, usage = _client.complete_json(
        user_prompt,
        system=system_prompt,
        schema=Plan.model_json_schema(),
    )
    result["project_id"] = project_id

    type_map = {"lower_third": "title", "title_card": "title"}
    for beat in result.get("beats", []):
        if beat.get("type") in type_map:
            beat["type"] = type_map[beat["type"]]
        if beat.get("type") != "source_clip" and beat.get("scene_id"):
            beat["scene_id"] = None

    plan = Plan.model_validate(result)
    out_path = project_path / "manifests" / "plan.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")

    _log_call(
        project_path=project_path,
        project_id=project_id,
        stage="plan_generation",
        model=usage["model"],
        elapsed_ms=usage["elapsed_ms"],
        input_tokens=usage["input_token_count"],
        output_tokens=usage["output_token_count"],
        artifact_path=str(out_path.relative_to(project_path)),
    )
    return plan.model_dump(mode="json")


def generate_tts_assets(project_path: Path) -> list[dict]:
    project_path = Path(project_path)
    plan = json.loads((project_path / "manifests" / "plan.json").read_text(encoding="utf-8"))
    tts_dir = project_path / "assets" / "tts"
    tts_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for beat in plan.get("beats", []):
        narration = beat.get("narration")
        if not narration:
            continue
        wav_bytes, usage = _client.generate_audio(narration)
        wav_filename = f"tts_{beat['beat_id']}.wav"
        wav_path = tts_dir / wav_filename
        wav_path.write_bytes(wav_bytes)
        tts_duration = _client.measure_wav_duration(wav_path)
        relative_asset = f"assets/tts/{wav_filename}"
        results.append(
            {
                "beat_id": beat["beat_id"],
                "tts_asset": relative_asset,
                "tts_duration": round(tts_duration, 3),
            }
        )
        _log_call(
            project_path=project_path,
            project_id=project_path.name,
            stage="tts_generation",
            model=usage["model"],
            elapsed_ms=usage["elapsed_ms"],
            input_tokens=usage["input_token_count"],
            output_tokens=usage["output_token_count"],
            artifact_path=relative_asset,
        )
    return results


def generate_background_assets(project_path: Path) -> list[dict]:
    project_path = Path(project_path)
    project_id = project_path.name
    plan = json.loads((project_path / "manifests" / "plan.json").read_text(encoding="utf-8"))
    scene_index = _maybe_load(SceneIndex, project_path / "cache" / "scene_index.json")
    shot_index = _maybe_load(ShotIndex, project_path / "cache" / "shot_index.json")

    bg_dir = project_path / "assets" / "backgrounds"
    bg_dir.mkdir(parents=True, exist_ok=True)
    remotion_dir = project_path / "assets" / "remotion"
    remotion_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for idx, beat in enumerate(plan.get("beats", []), start=1):
        if beat.get("type") not in ("title", "end_card", "scene_card"):
            continue
        btype = beat.get("type")
        block_id = f"{idx:03d}_end" if btype == "end_card" else f"{idx:03d}_{btype}"
        style = beat.get("style") or {}
        background_mode = style.get("background_mode") or "gradient"
        bg_filename = f"bg_{idx:03d}.png"
        bg_path = bg_dir / bg_filename
        model_name = "local-pillow-background"
        if background_mode in {"image", "image_tint"}:
            prompt = _build_background_prompt(goal=beat.get("goal", ""), text=beat.get("onscreen_text", ""), style=style)
            png_bytes, usage = _client.generate_image(prompt, model=GEMINI_IMAGE_MODEL)
            bg_path.write_bytes(png_bytes)
            model_name = usage.get("model", GEMINI_IMAGE_MODEL)
        else:
            _write_background_asset(
                bg_path,
                goal=beat.get("goal", ""),
                text=beat.get("onscreen_text", ""),
                style=style,
            )
        relative_asset = f"assets/backgrounds/{bg_filename}"
        bundle = _generate_text_scene_bundle(
            project_path=project_path,
            plan=plan,
            beat=beat,
            beat_index=idx - 1,
            block_id=block_id,
            scene_index=scene_index,
            shot_index=shot_index,
            background_asset=relative_asset,
        )
        scene_dir = remotion_dir / block_id
        scene_dir.mkdir(parents=True, exist_ok=True)
        scene_spec_path = scene_dir / "scene.json"
        scene_spec_path.write_text(bundle.scene_spec.model_dump_json(indent=2), encoding="utf-8")
        decorator_path = None
        if bundle.decorator_code:
            decorator_path = scene_dir / "decorator.tsx"
            decorator_path.write_text(bundle.decorator_code, encoding="utf-8")
        preview_path = scene_dir / "preview.png"
        try:
            render_remotion_preview(
                project_path,
                scene_spec_path,
                decorator_path,
                preview_path,
                _default_render_settings(),
            )
        except Exception:
            _write_preview_stub(preview_path, beat.get("onscreen_text") or beat.get("goal") or block_id)
        results.append(
            {
                "beat_id": beat["beat_id"],
                "background_asset": relative_asset,
                "scene_spec_path": f"assets/remotion/{block_id}/scene.json",
                "decorator_module_path": f"assets/remotion/{block_id}/decorator.tsx" if decorator_path else None,
                "preview_frame_path": f"assets/remotion/{block_id}/preview.png",
            }
        )

        _log_call(
            project_path=project_path,
            project_id=project_id,
            stage="background_generation",
            model=model_name,
            elapsed_ms=0,
            input_tokens=0,
            output_tokens=0,
            artifact_path=relative_asset,
        )
    return results


def precritique_manifest(project_path: Path) -> dict:
    project_path = Path(project_path)
    project_id = project_path.name
    empty = CriticSuggestions.model_validate(
        {"project_id": project_id, "critic_scope": "blind_manifest_only", "suggestions": []}
    )
    out_path = project_path / "manifests" / "critic_suggestions.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(empty.model_dump_json(indent=2), encoding="utf-8")
    return empty.model_dump(mode="json")


def review_render(project_path: Path, progress_callback=None) -> dict:
    project_path = Path(project_path)
    project_id = project_path.name

    if progress_callback:
        progress_callback(0.15, "Running deterministic render QA")
    render_qa = build_render_qa(project_path)
    media_probe = _maybe_load(MediaProbe, project_path / "cache" / "media_probe.json")
    shot_index = _maybe_load(ShotIndex, project_path / "cache" / "shot_index.json")
    render_path = project_path / "renders" / "final_render.mp4"
    manifest = json.loads((project_path / "manifests" / "block_manifest.json").read_text(encoding="utf-8"))
    block_manifest = BlockManifest.model_validate(manifest)

    if progress_callback:
        progress_callback(0.6, "Reviewing render with Gemini")
    system_prompt = _load_prompt("render_review_critic")
    user_prompt = (
        f"Project ID: {project_id}\n\n"
        "Block manifest:\n"
        f"{json.dumps(manifest, indent=2)}\n\n"
        "Media probe:\n"
        f"{media_probe.model_dump_json(indent=2) if media_probe else '{}'}\n\n"
        "Shot index:\n"
        f"{shot_index.model_dump_json(indent=2) if shot_index else '{}'}\n\n"
        "Render QA:\n"
        f"{render_qa.model_dump_json(indent=2)}\n\n"
        "Review the final rendered cut and produce actionable critique suggestions. "
        "Prefer whole-second source-clip edits when the recommendation is coarse pacing work."
    )

    result, usage = _client.complete_json_with_file(
        user_prompt,
        render_path,
        mime_type="video/mp4",
        system=system_prompt,
        schema=CriticSuggestions.model_json_schema(),
    )
    result["project_id"] = project_id
    result["critic_scope"] = "render_review"
    for suggestion in result.get("suggestions", []):
        suggestion["requires_approval"] = True
        suggestion.setdefault("suggestion_id", f"s{uuid.uuid4().hex[:6]}")
        if suggestion.get("action") in {"trim_end", "extend_end"} and suggestion.get("amount_seconds", 0) > 0:
            suggestion["amount_seconds"] = max(1.0, float(int(round(suggestion["amount_seconds"]))))

    critique = CriticSuggestions.model_validate(result)
    critique = critique.model_copy(
        update={
            "suggestions": [
                suggestion
                for suggestion in critique.suggestions
                if _suggestion_is_actionable(block_manifest, suggestion)
            ]
        }
    )
    out_path = project_path / "manifests" / "critic_suggestions.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(critique.model_dump_json(indent=2), encoding="utf-8")

    _log_call(
        project_path=project_path,
        project_id=project_id,
        stage="render_review",
        model=usage["model"],
        elapsed_ms=usage["elapsed_ms"],
        input_tokens=usage["input_token_count"],
        output_tokens=usage["output_token_count"],
        artifact_path=str(out_path.relative_to(project_path)),
    )

    if progress_callback:
        progress_callback(1.0, "Render review complete")
    return critique.model_dump(mode="json")


def _log_call(
    *,
    project_path: Path,
    project_id: str,
    stage: str,
    model: str,
    elapsed_ms: int,
    input_tokens: int,
    output_tokens: int,
    artifact_path: str = "",
    error: str | None = None,
) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project_id": project_id,
        "stage": stage,
        "model": model,
        "elapsed_ms": elapsed_ms,
        "input_token_count": input_tokens,
        "output_token_count": output_tokens,
        "artifact_path": artifact_path,
        "error": error,
    }
    log_dir = project_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / "gemini_calls.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def _maybe_load(model_type, path: Path):
    if not path.exists():
        return None
    return model_type.from_file(path)


def _fallback_media_probe(project_path: Path) -> MediaProbe:
    probe = MediaProbe.model_validate(
        {
            "project_id": project_path.name,
            "source": "source/placeholder.mp4",
            "duration_seconds": 30.0,
            "has_audio": False,
            "video_stream": {"codec": "unknown", "width": 1920, "height": 1080, "fps": 30.0},
            "audio_stream": None,
        }
    )
    out_path = project_path / "cache" / "media_probe.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(probe.model_dump_json(indent=2), encoding="utf-8")
    return probe


def _fallback_shot_index(project_path: Path, media_probe: MediaProbe) -> ShotIndex:
    shot_index = ShotIndex.model_validate(
        {
            "project_id": project_path.name,
            "source": media_probe.source,
            "shots": [
                {
                    "shot_id": "shot_001",
                    "start": 0.0,
                    "end": media_probe.duration_seconds,
                    "duration": media_probe.duration_seconds,
                    "start_frame_path": "cache/frames/placeholder_start.jpg",
                    "mid_frame_path": "cache/frames/placeholder_mid.jpg",
                    "end_frame_path": "cache/frames/placeholder_end.jpg",
                }
            ],
        }
    )
    out_path = project_path / "cache" / "shot_index.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(shot_index.model_dump_json(indent=2), encoding="utf-8")
    return shot_index


def _write_background_asset(path: Path, *, goal: str, text: str, style: dict) -> None:
    from PIL import Image, ImageDraw, ImageFilter

    width, height = 1920, 1080
    background_color = style.get("background_color") or _default_background_color(goal)
    accent_color = style.get("accent_color") or _default_accent_color(goal)
    background_mode = style.get("background_mode") or "gradient"

    image = Image.new("RGB", (width, height), _hex_to_rgb(background_color))
    draw = ImageDraw.Draw(image)

    if background_mode in {"gradient", "image_tint", "image"}:
        for y in range(height):
            ratio = y / max(height - 1, 1)
            color = _blend_color(_hex_to_rgb(background_color), _hex_to_rgb(accent_color), ratio * 0.55)
            draw.line((0, y, width, y), fill=color)

    # Add a few deterministic soft accent shapes so cards feel less flat.
    accent = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    accent_draw = ImageDraw.Draw(accent)
    accent_rgb = _hex_to_rgb(accent_color)
    accent_draw.ellipse((width * 0.58, height * 0.12, width * 1.05, height * 0.82), fill=accent_rgb + (110,))
    accent_draw.rectangle((width * 0.08, height * 0.68, width * 0.42, height * 0.9), fill=accent_rgb + (50,))
    accent = accent.filter(ImageFilter.GaussianBlur(80))
    image = Image.alpha_composite(image.convert("RGBA"), accent).convert("RGB")

    if len(text or "") > 22:
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((120, 120, 980, 940), radius=36, outline=(255, 255, 255, 28), width=2)

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG")


def _default_background_color(goal: str) -> str:
    goal_lower = goal.lower()
    if "result" in goal_lower or "launch" in goal_lower:
        return "#132238"
    if "problem" in goal_lower:
        return "#20141F"
    return "#111827"


def _default_accent_color(goal: str) -> str:
    goal_lower = goal.lower()
    if "result" in goal_lower or "launch" in goal_lower:
        return "#3CCB7F"
    if "problem" in goal_lower:
        return "#FF6B6B"
    return "#5B8CFF"


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    cleaned = value.lstrip("#")
    if len(cleaned) != 6:
        return (17, 24, 39)
    return tuple(int(cleaned[index:index + 2], 16) for index in (0, 2, 4))


def _blend_color(a: tuple[int, int, int], b: tuple[int, int, int], ratio: float) -> tuple[int, int, int]:
    clamped = max(0.0, min(1.0, ratio))
    return tuple(int(a[idx] + (b[idx] - a[idx]) * clamped) for idx in range(3))


def _build_background_prompt(*, goal: str, text: str, style: dict) -> str:
    accent = style.get("accent_color") or _default_accent_color(goal)
    background = style.get("background_color") or _default_background_color(goal)
    layout = style.get("layout_preset") or "centered"
    return (
        "Create a cinematic, text-free 16:9 background plate for a product demo video. "
        f"Goal: {goal or 'support the scene'}. "
        f"On-screen text theme: {text or 'none provided'}. "
        f"Use a composition that supports a {layout} text layout, with strong negative space. "
        f"Base palette around {background} with accent notes around {accent}. "
        "No words, no logos, no UI screenshots, no watermarks."
    )


def _normalize_scene_index_result(result: dict, source_duration: float) -> dict:
    normalized = dict(result)
    scenes = []
    for index, scene in enumerate(result.get("scenes", []), start=1):
        item = dict(scene)
        start = max(0.0, float(item.get("start", 0.0)))
        end = min(float(item.get("end", source_duration)), source_duration)
        if end <= start:
            end = min(source_duration, start + 0.05)
        if end <= start:
            continue
        item["scene_id"] = item.get("scene_id") or f"scene_{index:03d}"
        item["start"] = round(start, 4)
        item["end"] = round(end, 4)
        scenes.append(item)
    normalized["scenes"] = scenes
    return normalized


def _generate_text_scene_bundle(
    *,
    project_path: Path,
    plan: dict,
    beat: dict,
    beat_index: int,
    block_id: str,
    scene_index: SceneIndex | None,
    shot_index: ShotIndex | None,
    background_asset: str,
) -> GeneratedTextSceneBundle:
    system_prompt = _load_prompt("remotion_text_scene")
    user_prompt = _build_remotion_generation_prompt(
        project_id=project_path.name,
        plan=plan,
        beat=beat,
        beat_index=beat_index,
        block_id=block_id,
        scene_index=scene_index,
        shot_index=shot_index,
        background_asset=background_asset,
    )
    try:
        result, _usage = _client.complete_json(
            user_prompt,
            system=system_prompt,
            schema=GeneratedTextSceneBundle.model_json_schema(),
        )
        return GeneratedTextSceneBundle.model_validate(result)
    except Exception:
        return _fallback_text_scene_bundle(beat=beat, block_id=block_id, background_asset=background_asset)


def _build_remotion_generation_prompt(
    *,
    project_id: str,
    plan: dict,
    beat: dict,
    beat_index: int,
    block_id: str,
    scene_index: SceneIndex | None,
    shot_index: ShotIndex | None,
    background_asset: str,
) -> str:
    neighbors = []
    beats = plan.get("beats", [])
    if beat_index > 0:
        neighbors.append({"position": "previous", **_neighbor_summary(beats[beat_index - 1])})
    if beat_index + 1 < len(beats):
        neighbors.append({"position": "next", **_neighbor_summary(beats[beat_index + 1])})
    nearby_scenes = scene_index.model_dump(mode="json")["scenes"][:3] if scene_index else []
    nearby_shots = shot_index.model_dump(mode="json")["shots"][:4] if shot_index else []
    payload = {
        "project_id": project_id,
        "project_title": plan.get("title"),
        "block_id": block_id,
        "block_type": beat.get("type"),
        "duration_seconds": beat.get("duration"),
        "goal": beat.get("goal"),
        "onscreen_text": beat.get("onscreen_text") or plan.get("title"),
        "style": beat.get("style") or {},
        "background_asset": background_asset,
        "neighboring_beats": neighbors,
        "nearby_scenes": nearby_scenes,
        "nearby_shots": nearby_shots,
        "remotion_rules": [
            "Use useCurrentFrame(), interpolate(), and Sequence for timing.",
            "Do not use CSS transitions or CSS animations.",
            "Keep rendering deterministic and local-asset friendly.",
            "Stay within a readable 16:9 title-card composition.",
            "Return only the approved structured JSON contract.",
            "Reuse the same accent_color and background_color across all title and end_card blocks in a project for brand consistency.",
            "Never use filler text like 'Initializing Project' or 'Setting Up'. Use the project title or a compelling hook.",
        ],
    }
    return (
        f"Project title: {plan.get('title')}\n"
        f"Current block ID: {block_id}\n"
        "Neighboring beats:\n"
        f"{json.dumps(neighbors, indent=2)}\n\n"
        "Generation context:\n"
        f"{json.dumps(payload, indent=2)}"
    )


def _neighbor_summary(beat: dict) -> dict:
    return {
        "beat_id": beat.get("beat_id"),
        "type": beat.get("type"),
        "goal": beat.get("goal"),
        "duration": beat.get("duration"),
        "onscreen_text": beat.get("onscreen_text"),
    }


def _fallback_text_scene_bundle(*, beat: dict, block_id: str, background_asset: str) -> GeneratedTextSceneBundle:
    style = beat.get("style") or {}
    background_mode = style.get("background_mode") or "gradient"
    runtime_template = _runtime_template_from_style(style)
    scene_spec = GeneratedTextSceneSpec.model_validate(
        {
            "version": 1,
            "block_type": beat.get("type"),
            "text": beat.get("onscreen_text") or beat.get("goal") or block_id,
            "duration_seconds": beat.get("duration") or 3.0,
            "runtime_template": runtime_template,
            "layout_preset": style.get("layout_preset") or "centered",
            "text_alignment": style.get("text_alignment") or "center",
            "font_family": style.get("font_family") or "display-sans",
            "font_variant": style.get("font_variant") or "bold",
            "text_color": style.get("text_color") or "#F9FAFB",
            "accent_color": style.get("accent_color") or _default_accent_color(beat.get("goal", "")),
            "background_mode": background_mode,
            "background_color": style.get("background_color") or _default_background_color(beat.get("goal", "")),
            "background_image_path": background_asset if background_mode in {"image", "image_tint"} else None,
            "animation_preset": "fade-in",
            "show_glass_panel": True,
            "show_accent_bar": True,
        }
    )
    decorator_code = _fallback_decorator_code(runtime_template)
    return GeneratedTextSceneBundle.model_validate(
        {
            "runtime_template": runtime_template,
            "scene_spec": scene_spec.model_dump(mode="json"),
            "decorator_code": decorator_code,
            "background_requirements": {"mode": "generated_image" if background_mode in {"image", "image_tint"} else "local", "prompt": None},
        }
    )


def _runtime_template_from_style(style: dict) -> str:
    layout = style.get("layout_preset") or "centered"
    if layout in {"hero-left", "hero-right"}:
        return "split-panel"
    if layout == "stacked":
        return "stacked-pulse"
    return "hero-reveal"


def _fallback_decorator_code(runtime_template: str) -> str:
    if runtime_template == "split-panel":
        return (
            "import React from 'react';\n"
            "export default function Decorator() {\n"
            "  return <div style={{position:'absolute', inset:0, border:'1px solid rgba(255,255,255,0.06)'}} />;\n"
            "}\n"
        )
    if runtime_template == "stacked-pulse":
        return (
            "import React from 'react';\n"
            "export default function Decorator() {\n"
            "  return <div style={{position:'absolute', inset:32, borderRadius:28, boxShadow:'0 0 120px rgba(91,140,255,0.12) inset'}} />;\n"
            "}\n"
        )
    return (
        "import React from 'react';\n"
        "export default function Decorator() {\n"
        "  return <div style={{position:'absolute', inset:0, pointerEvents:'none'}} />;\n"
        "}\n"
    )


def _default_render_settings() -> dict:
    return {"fps": 30, "width": 1920, "height": 1080}


def _write_preview_stub(path: Path, label: str) -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (1280, 720), "#111827")
    draw = ImageDraw.Draw(image)
    draw.text((64, 64), label, fill="#F9FAFB")
    image.save(path, "PNG")

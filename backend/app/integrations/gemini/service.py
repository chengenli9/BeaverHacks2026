"""High-level Gemini service functions for DirectorLoop.

Each public function operates on a *project_path* (a Path to a directory with
the standard project layout) and writes its output artifact(s) to the correct
sub-directory within that project.  The renderer never needs to import this
module; it only reads the files that are written here.

Output artifacts
----------------
cache/scene_index.json         — analyze_scenes()
manifests/plan.json            — generate_plan()
assets/tts/tts_<N>.wav         — generate_tts_assets()
assets/backgrounds/bg_<N>.png  — generate_background_assets()
manifests/critic_suggestions.json — precritique_manifest()
logs/gemini_calls.jsonl        — appended by every function above
"""

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import client as _client
from .settings import GEMINI_IMAGE_MODEL, GEMINI_TEXT_MODEL, GEMINI_TTS_MODEL

# ---------------------------------------------------------------------------
# Prompt file loader
# ---------------------------------------------------------------------------

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


def _load_prompt(name: str) -> str:
    """Load a prompt from backend/app/prompts/<name>.md."""
    path = _PROMPTS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyze_scenes(project_path: Path) -> dict:
    """Analyse source footage with Gemini and write cache/scene_index.json.

    If a source video file is found it is uploaded to the Files API.  If no
    video is found the prompt is sent without a file attachment so development
    can proceed without real footage.

    Returns the parsed scene_index dict.
    """
    project_path = Path(project_path)
    project_id = project_path.name

    source_dir = project_path / "source"
    video_file = _find_video(source_dir)

    system_prompt = _load_prompt("scene_analysis")
    user_prompt = (
        f"Project ID: {project_id}\n"
        "Analyse the footage and return a scene_index JSON object matching the "
        "API contract exactly.  Respond with JSON only."
    )

    if video_file:
        result, usage = _client.complete_json_with_file(
            user_prompt,
            video_file,
            mime_type="video/mp4",
            system=system_prompt,
        )
    else:
        result, usage = _client.complete_json(
            user_prompt,
            system=system_prompt,
        )

    # Ensure the project_id field is set correctly
    result["project_id"] = project_id

    out_path = project_path / "cache" / "scene_index.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

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
    return result


def generate_plan(project_path: Path) -> dict:
    """Generate an edit plan from the scene index and write manifests/plan.json.

    Returns the parsed plan dict.
    """
    project_path = Path(project_path)
    project_id = project_path.name

    scene_index_path = project_path / "cache" / "scene_index.json"
    scene_index = json.loads(scene_index_path.read_text(encoding="utf-8"))

    system_prompt = _load_prompt("plan_generation")
    user_prompt = (
        f"Project ID: {project_id}\n\n"
        "Scene index:\n"
        f"{json.dumps(scene_index, indent=2)}\n\n"
        "Generate a plan.json matching the API contract.  "
        "Narration must not exceed 2 words per second of allocated clip duration.  "
        "Respond with JSON only."
    )

    result, usage = _client.complete_json(user_prompt, system=system_prompt)
    result["project_id"] = project_id

    # Normalize beat types: Gemini may return stale types from old prompts
    _TYPE_MAP = {"lower_third": "title", "title_card": "title"}
    for beat in result.get("beats", []):
        if beat.get("type") in _TYPE_MAP:
            beat["type"] = _TYPE_MAP[beat["type"]]
        # Non-source beats must not carry a scene_id
        if beat.get("type") != "source_clip" and beat.get("scene_id"):
            beat["scene_id"] = None

    out_path = project_path / "manifests" / "plan.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

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
    return result


def generate_tts_assets(project_path: Path) -> list[dict]:
    """Generate TTS WAV files for every beat that has narration.

    Reads manifests/plan.json.  Writes assets/tts/tts_<beat_id>.wav.

    Returns a list of metadata dicts:
        [{"beat_id": ..., "tts_asset": ..., "tts_duration": ...}, ...]
    """
    project_path = Path(project_path)
    project_id = project_path.name

    plan_path = project_path / "manifests" / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    tts_dir = project_path / "assets" / "tts"
    tts_dir.mkdir(parents=True, exist_ok=True)

    narration_prompt_template = _load_prompt("narration")
    results = []

    for beat in plan.get("beats", []):
        narration = beat.get("narration")
        if not narration:
            continue

        beat_id = beat["beat_id"]
        duration = beat.get("duration", 0.0)

        # Optionally refine narration through the narration prompt
        if narration_prompt_template:
            refined_text = _refine_narration(narration, duration, narration_prompt_template)
        else:
            refined_text = narration

        wav_bytes, usage = _client.generate_audio(refined_text)

        wav_filename = f"tts_{beat_id}.wav"
        wav_path = tts_dir / wav_filename
        wav_path.write_bytes(wav_bytes)

        tts_duration = _client.measure_wav_duration(wav_path)

        relative_asset = f"assets/tts/{wav_filename}"
        results.append(
            {
                "beat_id": beat_id,
                "tts_asset": relative_asset,
                "tts_duration": round(tts_duration, 3),
            }
        )

        _log_call(
            project_path=project_path,
            project_id=project_id,
            stage="tts_generation",
            model=usage["model"],
            elapsed_ms=usage["elapsed_ms"],
            input_tokens=usage["input_token_count"],
            output_tokens=usage["output_token_count"],
            artifact_path=relative_asset,
        )

    return results


def generate_background_assets(project_path: Path) -> list[dict]:
    """Generate textless background PNG images for every block that needs one.

    Reads manifests/plan.json.  Writes assets/backgrounds/bg_<N>.png.

    Returns a list of metadata dicts:
        [{"beat_id": ..., "background_asset": ...}, ...]
    """
    project_path = Path(project_path)
    project_id = project_path.name

    plan_path = project_path / "manifests" / "plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    bg_dir = project_path / "assets" / "backgrounds"
    bg_dir.mkdir(parents=True, exist_ok=True)

    bg_prompt_template = _load_prompt("background_plate")
    results = []

    for idx, beat in enumerate(plan.get("beats", []), start=1):
        beat_id = beat["beat_id"]
        beat_type = beat.get("type", "")

        # Generate backgrounds for title and end_card beats
        if beat_type not in ("title", "end_card"):
            continue

        goal = beat.get("goal", "professional presentation background")
        text = beat.get("onscreen_text", "")
        image_prompt = bg_prompt_template.replace("{{goal}}", goal).replace(
            "{{onscreen_text}}", text or "(none)"
        )

        png_bytes, usage = _client.generate_image(image_prompt)

        bg_filename = f"bg_{idx:03d}.png"
        bg_path = bg_dir / bg_filename
        bg_path.write_bytes(png_bytes)

        relative_asset = f"assets/backgrounds/{bg_filename}"
        results.append({"beat_id": beat_id, "background_asset": relative_asset})

        _log_call(
            project_path=project_path,
            project_id=project_id,
            stage="background_generation",
            model=usage.get("model", GEMINI_IMAGE_MODEL),
            elapsed_ms=usage["elapsed_ms"],
            input_tokens=usage["input_token_count"],
            output_tokens=usage["output_token_count"],
            artifact_path=relative_asset,
            error=usage.get("error"),
        )

    return results


def precritique_manifest(project_path: Path) -> dict:
    """Run the blind manifest critic and write manifests/critic_suggestions.json.

    Inputs:
        cache/scene_index.json
        manifests/block_manifest.json

    Returns the parsed critic_suggestions dict.
    """
    project_path = Path(project_path)
    project_id = project_path.name

    scene_index = json.loads(
        (project_path / "cache" / "scene_index.json").read_text(encoding="utf-8")
    )
    block_manifest = json.loads(
        (project_path / "manifests" / "block_manifest.json").read_text(encoding="utf-8")
    )

    system_prompt = _load_prompt("blind_manifest_critic")
    user_prompt = (
        f"Project ID: {project_id}\n\n"
        "Scene index:\n"
        f"{json.dumps(scene_index, indent=2)}\n\n"
        "Block manifest:\n"
        f"{json.dumps(block_manifest, indent=2)}\n\n"
        "Return a critic_suggestions JSON object matching the API contract.  "
        "Respond with JSON only."
    )

    result, usage = _client.complete_json(user_prompt, system=system_prompt)
    result["project_id"] = project_id
    result.setdefault("critic_scope", "blind_manifest_only")

    # Enforce: all suggestions must have requires_approval = true
    for s in result.get("suggestions", []):
        s["requires_approval"] = True
        # Auto-assign IDs if missing
        if not s.get("suggestion_id"):
            s["suggestion_id"] = f"s{uuid.uuid4().hex[:6]}"

    out_path = project_path / "manifests" / "critic_suggestions.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    _log_call(
        project_path=project_path,
        project_id=project_id,
        stage="blind_manifest_critic",
        model=usage["model"],
        elapsed_ms=usage["elapsed_ms"],
        input_tokens=usage["input_token_count"],
        output_tokens=usage["output_token_count"],
        artifact_path=str(out_path.relative_to(project_path)),
    )
    return result


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


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
    """Append a sanitised metadata record to logs/gemini_calls.jsonl.

    The API key is never written.
    """
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
    log_path = log_dir / "gemini_calls.jsonl"

    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _find_video(source_dir: Path) -> Path | None:
    """Return the first video file found in source_dir, or None."""
    if not source_dir.exists():
        return None
    for ext in ("*.mp4", "*.mov", "*.avi", "*.mkv"):
        matches = list(source_dir.glob(ext))
        if matches:
            return matches[0]
    return None


def _refine_narration(narration: str, duration: float, prompt_template: str) -> str:
    """Use the narration prompt to optionally tighten narration to the duration.

    If Gemini cannot be reached or returns something unexpected, return the
    original narration unchanged.
    """
    if duration <= 0:
        return narration

    max_words = int(duration * 2)
    user_prompt = (
        prompt_template
        + f"\n\nOriginal narration: {narration}\n"
        f"Target clip duration: {duration} seconds (max {max_words} words).\n"
        "Return a JSON object with a single key 'narration' containing the refined text."
    )
    try:
        result, _ = _client.complete_json(user_prompt)
        return result.get("narration", narration)
    except Exception:  # noqa: BLE001
        return narration

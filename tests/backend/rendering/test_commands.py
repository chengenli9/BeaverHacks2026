from pathlib import Path

from backend.app.manifests.models import BlockManifest
from backend.app.rendering.commands import (
    build_concat_command,
    build_source_clip_command,
    build_title_block_command,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_PROJECT = PROJECT_ROOT / "samples" / "demo_project"


def test_title_command_includes_explicit_fontfile():
    manifest = BlockManifest.from_file(SAMPLE_PROJECT / "manifests" / "block_manifest.json")
    block = manifest.block_by_id("001_title")

    command = build_title_block_command(SAMPLE_PROJECT, block, manifest.render_settings)
    joined = " ".join(command)

    assert "drawtext" in joined
    assert "fontfile=" in joined
    assert "assets/fonts/Inter-Bold.ttf" in joined
    assert "C\\:" in joined


def test_source_command_includes_tts_input_when_present():
    manifest = BlockManifest.from_file(SAMPLE_PROJECT / "manifests" / "block_manifest.json")
    block = manifest.block_by_id("002_problem")

    command = build_source_clip_command(SAMPLE_PROJECT, block, manifest.render_settings)

    assert str(SAMPLE_PROJECT / "assets" / "tts" / "tts_002.wav") in command
    assert "-filter_complex" in command


def test_concat_command_targets_final_render():
    manifest = BlockManifest.from_file(SAMPLE_PROJECT / "manifests" / "block_manifest.json")

    command = build_concat_command(SAMPLE_PROJECT, manifest)

    assert command[:4] == ["ffmpeg", "-y", "-f", "concat"]
    assert str(SAMPLE_PROJECT / "renders" / "final_render.mp4") == command[-1]

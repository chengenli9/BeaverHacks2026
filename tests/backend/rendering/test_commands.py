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
    assert command[:4] == ["ffmpeg", "-y", "-loop", "1"]
    assert str(SAMPLE_PROJECT / "cache" / "001_title_composited.png") in command
    assert str(SAMPLE_PROJECT / "blocks" / "001_title.mp4") == command[-1]


def test_source_command_includes_tts_input_when_present():
    manifest = BlockManifest.model_validate(
        {
            "project_id": "demo_project",
            "version": 1,
            "render_settings": {},
            "blocks": [
                {
                    "block_id": "002_beat_002",
                    "type": "source_clip",
                    "source": "source/demo_footage.mp4",
                    "source_start": 0.0,
                    "source_end": 3.0,
                    "video_duration": 3.0,
                    "tts_asset": "assets/tts/tts_beat_002.wav",
                    "tts_duration": 2.2,
                    "source_audio_volume": 1.0,
                    "tts_fade_seconds": 0.5,
                    "rendered_path": "blocks/002_beat_002.mp4",
                }
            ],
        }
    )
    block = manifest.block_by_id("002_beat_002")

    command = build_source_clip_command(
        SAMPLE_PROJECT,
        block,
        manifest.render_settings,
        source_has_audio=True,
    )

    assert str(SAMPLE_PROJECT / "assets" / "tts" / "tts_beat_002.wav") in command
    assert "-filter_complex" in command


def test_source_command_uses_silent_audio_when_source_has_no_audio():
    manifest = BlockManifest.model_validate(
        {
            "project_id": "demo_project",
            "version": 1,
            "render_settings": {},
            "blocks": [
                {
                    "block_id": "002_beat_002",
                    "type": "source_clip",
                    "source": "source/demo_footage.mp4",
                    "source_start": 0.0,
                    "source_end": 3.0,
                    "video_duration": 3.0,
                    "tts_asset": "assets/tts/tts_beat_002.wav",
                    "tts_duration": 2.2,
                    "source_audio_volume": 1.0,
                    "tts_fade_seconds": 0.5,
                    "rendered_path": "blocks/002_beat_002.mp4",
                }
            ],
        }
    )
    block = manifest.block_by_id("002_beat_002")

    command = build_source_clip_command(
        SAMPLE_PROJECT,
        block,
        manifest.render_settings,
        source_has_audio=False,
    )
    joined = " ".join(command)

    assert "anullsrc=channel_layout=stereo:sample_rate=48000" in command
    assert "[2:a]afade" in joined
    assert "[srca][ttsa]amix=inputs=2:duration=longest:normalize=0[a]" in joined


def test_source_command_without_tts_still_outputs_audio_when_source_has_no_audio():
    manifest = BlockManifest.model_validate(
        {
            "project_id": "demo_project",
            "version": 1,
            "render_settings": {},
            "blocks": [
                {
                    "block_id": "001_no_tts",
                    "type": "source_clip",
                    "source": "source/demo_footage.mp4",
                    "source_start": 0.0,
                    "source_end": 1.0,
                    "video_duration": 1.0,
                    "tts_asset": None,
                    "tts_duration": None,
                    "source_audio_volume": 1.0,
                    "tts_fade_seconds": 0.5,
                    "rendered_path": "blocks/001_no_tts.mp4",
                }
            ],
        }
    )
    block = manifest.block_by_id("001_no_tts")

    command = build_source_clip_command(
        SAMPLE_PROJECT,
        block,
        manifest.render_settings,
        source_has_audio=False,
    )
    joined = " ".join(command)

    assert "anullsrc=channel_layout=stereo:sample_rate=48000" in command
    assert "-filter_complex" in command
    assert "-map [a]" in joined


def test_concat_command_targets_final_render():
    manifest = BlockManifest.from_file(SAMPLE_PROJECT / "manifests" / "block_manifest.json")

    command = build_concat_command(SAMPLE_PROJECT, manifest)

    assert command[:4] == ["ffmpeg", "-y", "-f", "concat"]
    assert str(SAMPLE_PROJECT / "renders" / "final_render.mp4") == command[-1]

import shutil
from pathlib import Path

import pytest

from backend.app.manifests.models import BlockManifest
from backend.app.manifests.service import build_manifest_from_plan, write_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_PROJECT = PROJECT_ROOT / "samples" / "demo_project"


def test_build_manifest_from_plan_creates_deterministic_blocks(tmp_path):
    project = tmp_path
    (project / "cache").mkdir()
    (project / "manifests").mkdir()
    (project / "assets" / "remotion" / "001_title").mkdir(parents=True)
    (project / "assets" / "remotion" / "001_title" / "scene.json").write_text("{}", encoding="utf-8")
    (project / "assets" / "remotion" / "001_title" / "preview.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (project / "assets" / "remotion" / "005_end").mkdir(parents=True)
    (project / "assets" / "remotion" / "005_end" / "scene.json").write_text("{}", encoding="utf-8")
    (project / "cache" / "scene_index.json").write_text(
        """
        {
          "project_id": "demo_project",
          "source": "source/demo_footage.mp4",
          "source_duration": 30.0,
          "scenes": [
            {"scene_id": "scene_001", "start": 0.0, "end": 10.0, "summary": "Open", "visual_tags": [], "audio_notes": "", "demo_relevance": 0.8},
            {"scene_id": "scene_002", "start": 8.0, "end": 20.0, "summary": "Middle", "visual_tags": [], "audio_notes": "", "demo_relevance": 0.8},
            {"scene_id": "scene_004", "start": 19.0, "end": 28.0, "summary": "Close", "visual_tags": [], "audio_notes": "", "demo_relevance": 0.8}
          ]
        }
        """.strip(),
        encoding="utf-8",
    )
    (project / "manifests" / "plan.json").write_text(
        """
        {
          "project_id": "demo_project",
          "title": "DirectorLoop Demo Cut",
          "target_duration": 20.0,
          "story_arc": ["Hook", "Proof", "Wrap"],
          "beats": [
            {"beat_id": "beat_001", "type": "title", "goal": "Hook", "scene_id": null, "duration": 3.0, "narration": null, "onscreen_text": "DirectorLoop"},
            {"beat_id": "beat_002", "type": "source_clip", "goal": "Show opening proof", "scene_id": "scene_001", "duration": 3.0, "narration": "Watch this.", "onscreen_text": null},
            {"beat_id": "beat_003", "type": "source_clip", "goal": "Show interaction", "scene_id": "scene_002", "duration": 3.0, "narration": "New obstacle appears.", "onscreen_text": null},
            {"beat_id": "beat_004", "type": "source_clip", "goal": "Show outcome", "scene_id": "scene_004", "duration": 7.0, "narration": "Colorful interaction.", "onscreen_text": null},
            {"beat_id": "beat_005", "type": "end_card", "goal": "Wrap", "scene_id": null, "duration": 3.0, "narration": null, "onscreen_text": "Gemini plans. FFmpeg renders."}
          ]
        }
        """.strip(),
        encoding="utf-8",
    )

    manifest = build_manifest_from_plan(
        project,
        tts_durations={
            "beat_002": 6.1,
            "beat_003": 8.4,
            "beat_004": 6.6,
        },
    )

    assert [block.block_id for block in manifest.blocks] == [
        "001_title",
        "002_beat_002",
        "003_beat_003",
        "004_beat_004",
        "005_end",
    ]
    assert manifest.block_by_id("001_title").background_asset == "assets/backgrounds/bg_001.png"
    assert manifest.block_by_id("001_title").fontfile == "assets/fonts/Inter-Bold.ttf"
    assert manifest.block_by_id("001_title").motion_asset.kind == "remotion_scene"
    assert manifest.block_by_id("001_title").motion_asset.scene_spec_path == "assets/remotion/001_title/scene.json"
    assert manifest.block_by_id("001_title").motion_asset.preview_frame_path == "assets/remotion/001_title/preview.png"

    beat_002 = manifest.block_by_id("002_beat_002")
    assert beat_002.source == "source/demo_footage.mp4"
    assert beat_002.source_start == 0.0
    assert beat_002.source_end == 6.1
    assert beat_002.tts_asset == "assets/tts/tts_beat_002.wav"
    assert beat_002.tts_duration == 6.1

    beat_003 = manifest.block_by_id("003_beat_003")
    assert beat_003.source_start == 8.0
    assert beat_003.source_end == 16.4
    assert beat_003.video_duration == pytest.approx(8.4)
    assert beat_003.video_duration == pytest.approx(beat_003.tts_duration)

    end = manifest.block_by_id("005_end")
    assert end.type == "end_card"
    assert end.text == "Gemini plans. FFmpeg renders."
    assert end.motion_asset.kind == "remotion_scene"
    assert end.motion_asset.scene_spec_path == "assets/remotion/005_end/scene.json"


def test_build_manifest_writes_block_manifest_json(tmp_path):
    project = tmp_path
    shutil.copytree(SAMPLE_PROJECT / "cache", project / "cache")
    (project / "manifests").mkdir()
    (project / "manifests" / "plan.json").write_text(
        """
        {
          "project_id": "demo_project",
          "title": "DirectorLoop Demo Cut",
          "target_duration": 12.0,
          "story_arc": ["Hook", "Wrap"],
          "beats": [
            {"beat_id": "beat_001", "type": "title", "goal": "Hook", "scene_id": null, "duration": 3.0, "narration": null, "onscreen_text": "DirectorLoop"},
            {"beat_id": "beat_003", "type": "source_clip", "goal": "Show interaction", "scene_id": "scene_003", "duration": 3.0, "narration": null, "onscreen_text": null},
            {"beat_id": "beat_005", "type": "end_card", "goal": "Wrap", "scene_id": null, "duration": 3.0, "narration": null, "onscreen_text": "Done"}
          ]
        }
        """.strip(),
        encoding="utf-8",
    )

    manifest = build_manifest_from_plan(project)
    path = write_manifest(project, manifest)
    loaded = BlockManifest.from_file(path)

    assert path == project / "manifests" / "block_manifest.json"
    assert loaded.block_by_id("002_beat_003").tts_asset is None

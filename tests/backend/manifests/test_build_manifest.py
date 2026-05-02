from pathlib import Path
import shutil

from backend.app.manifests.models import BlockManifest
from backend.app.manifests.service import build_manifest_from_plan, write_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_PROJECT = PROJECT_ROOT / "samples" / "demo_project"


def test_build_manifest_from_plan_creates_deterministic_blocks(tmp_path):
    project = tmp_path
    shutil.copytree(SAMPLE_PROJECT / "cache", project / "cache")
    shutil.copytree(SAMPLE_PROJECT / "manifests", project / "manifests")

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

    beat_002 = manifest.block_by_id("002_beat_002")
    assert beat_002.source == "source/demo_footage.mp4"
    assert beat_002.source_start == 0.0
    assert beat_002.source_end == 6.5
    assert beat_002.tts_asset == "assets/tts/tts_002.wav"
    assert beat_002.tts_duration == 6.1

    beat_003 = manifest.block_by_id("003_beat_003")
    assert beat_003.source_start == 8.0
    assert beat_003.source_end == 16.4
    assert beat_003.video_duration == 8.4
    assert beat_003.video_duration >= beat_003.tts_duration

    end = manifest.block_by_id("005_end")
    assert end.type == "end_card"
    assert end.text == "Gemini plans. FFmpeg renders."


def test_build_manifest_writes_block_manifest_json(tmp_path):
    project = tmp_path
    shutil.copytree(SAMPLE_PROJECT / "cache", project / "cache")
    shutil.copytree(SAMPLE_PROJECT / "manifests", project / "manifests")

    manifest = build_manifest_from_plan(project)
    path = write_manifest(project, manifest)
    loaded = BlockManifest.from_file(path)

    assert path == project / "manifests" / "block_manifest.json"
    assert loaded.block_by_id("003_beat_003").tts_asset is None

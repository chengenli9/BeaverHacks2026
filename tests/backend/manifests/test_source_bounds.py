from pathlib import Path

import pytest

from backend.app.manifests.models import BlockManifest, SceneIndex
from backend.app.manifests.service import validate_manifest_source_bounds


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_PROJECT = PROJECT_ROOT / "samples" / "demo_project"


def test_sample_manifest_source_bounds_fit_scene_index_duration():
    scene_index = SceneIndex.from_file(SAMPLE_PROJECT / "cache" / "scene_index.json")
    manifest = BlockManifest.from_file(SAMPLE_PROJECT / "manifests" / "block_manifest.json")

    validate_manifest_source_bounds(manifest, scene_index)


def test_manifest_source_bounds_reject_clip_past_source_duration():
    scene_index = SceneIndex.from_file(SAMPLE_PROJECT / "cache" / "scene_index.json")
    manifest = BlockManifest.model_validate(
        {
            "project_id": "demo_project",
            "version": 1,
            "render_settings": {},
            "blocks": [
                {
                    "block_id": "001_bad",
                    "type": "source_clip",
                    "source": "source/demo_footage.mp4",
                    "source_start": 40.0,
                    "source_end": 45.0,
                    "video_duration": 5.0,
                    "tts_asset": None,
                    "tts_duration": None,
                    "source_audio_volume": 0.15,
                    "tts_fade_seconds": 0.5,
                    "rendered_path": "blocks/001_bad.mp4",
                }
            ],
        }
    )

    with pytest.raises(ValueError, match="exceeds source_duration"):
        validate_manifest_source_bounds(manifest, scene_index)


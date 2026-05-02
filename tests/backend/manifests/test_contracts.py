from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.manifests.models import BlockManifest
from backend.app.manifests.service import validate_project_assets


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_PROJECT = PROJECT_ROOT / "samples" / "demo_project"


def test_sample_manifest_fixture_validates():
    manifest = BlockManifest.from_file(SAMPLE_PROJECT / "manifests" / "block_manifest.json")

    assert manifest.project_id == "demo_project"
    assert len(manifest.blocks) == 5
    assert manifest.blocks[0].block_id == "001_title"


def test_duplicate_block_ids_fail_validation():
    data = {
        "project_id": "demo_project",
        "version": 1,
        "render_settings": {},
        "blocks": [
            {
                "block_id": "001_title",
                "type": "title",
                "background_asset": "assets/backgrounds/bg_001.png",
                "text": "DirectorLoop",
                "duration": 3.0,
                "fontfile": "assets/fonts/Inter-Bold.ttf",
                "rendered_path": "blocks/001_title.mp4",
            },
            {
                "block_id": "001_title",
                "type": "end_card",
                "background_asset": "assets/backgrounds/bg_005.png",
                "text": "Done",
                "duration": 3.0,
                "fontfile": "assets/fonts/Inter-Bold.ttf",
                "rendered_path": "blocks/001_title_again.mp4",
            },
        ],
    }

    with pytest.raises(ValidationError, match="block_id values must be unique"):
        BlockManifest.model_validate(data)


def test_validate_project_assets_reports_missing_font_before_render():
    manifest = BlockManifest.from_file(SAMPLE_PROJECT / "manifests" / "block_manifest.json")

    with pytest.raises(FileNotFoundError, match="assets/fonts/Inter-Bold.ttf"):
        validate_project_assets(SAMPLE_PROJECT, manifest, require_media=False)


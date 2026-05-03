from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.manifests.models import BlockManifest, CriticSuggestions
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


def test_validate_project_assets_allows_font_fallback_before_render():
    manifest = BlockManifest.from_file(SAMPLE_PROJECT / "manifests" / "block_manifest.json")

    validate_project_assets(SAMPLE_PROJECT, manifest, require_media=False)


def test_title_block_accepts_style_fields():
    manifest = BlockManifest.model_validate(
        {
            "project_id": "styled_project",
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
                    "font_family": "display-sans",
                    "font_variant": "bold",
                    "text_color": "#FFF4D6",
                    "accent_color": "#FF6B2C",
                    "background_mode": "gradient",
                    "background_color": "#111827",
                    "text_alignment": "left",
                    "layout_preset": "hero-left",
                    "rendered_path": "blocks/001_title.mp4",
                }
            ],
        }
    )

    block = manifest.blocks[0]
    assert block.font_family == "display-sans"
    assert block.background_mode == "gradient"
    assert block.layout_preset == "hero-left"


def test_critic_suggestion_accepts_review_metadata():
    suggestions = CriticSuggestions.model_validate(
        {
            "project_id": "demo_project",
            "critic_scope": "render_review",
            "suggestions": [
                {
                    "suggestion_id": "s001",
                    "block_id": "002_demo",
                    "action": "trim_end",
                    "amount_seconds": 0.5,
                    "max_allowed_trim_seconds": 1.0,
                    "reason": "Tighten pacing.",
                    "requires_approval": True,
                    "category": "pacing",
                    "severity": "medium",
                    "confidence": 0.74,
                    "viewer_problem": "The beat lingers after the key point lands.",
                    "evidence": ["render_qa: no issue", "shot_index: repeated adjacent frames"],
                    "before_summary": "3.0s source clip",
                    "after_summary": "2.5s source clip",
                }
            ],
        }
    )

    suggestion = suggestions.suggestions[0]
    assert suggestion.category == "pacing"
    assert suggestion.severity == "medium"
    assert suggestion.confidence == pytest.approx(0.74)


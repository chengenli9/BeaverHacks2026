from pathlib import Path

import pytest

from backend.app.manifests.models import ApplyPatchesRequest, BlockManifest, CriticSuggestions
from backend.app.manifests.service import apply_suggestions_to_manifest, validate_critic_suggestions


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_PROJECT = PROJECT_ROOT / "samples" / "demo_project"


def test_critic_trim_above_thirty_percent_fails():
    manifest = BlockManifest.from_file(SAMPLE_PROJECT / "manifests" / "block_manifest.json")
    suggestions = CriticSuggestions.model_validate(
        {
            "project_id": "demo_project",
            "critic_scope": "blind_manifest_only",
            "suggestions": [
                {
                    "suggestion_id": "s_bad",
                    "block_id": "003_pipeline",
                    "action": "trim_end",
                    "amount_seconds": 3.0,
                    "max_allowed_trim_seconds": 2.4,
                    "reason": "Too long.",
                    "requires_approval": True,
                }
            ],
        }
    )

    with pytest.raises(ValueError, match="cannot trim more than 30%"):
        validate_critic_suggestions(manifest, suggestions)


def test_approved_patch_applies_and_rejected_patch_is_ignored():
    manifest = BlockManifest.from_file(SAMPLE_PROJECT / "manifests" / "block_manifest.json")
    suggestions = CriticSuggestions.from_file(SAMPLE_PROJECT / "manifests" / "critic_suggestions.json")
    request = ApplyPatchesRequest.model_validate(
        {
            "project_id": "demo_project",
            "approved_suggestion_ids": ["s001"],
            "rejected_suggestion_ids": ["s002"],
        }
    )

    patched = apply_suggestions_to_manifest(manifest, suggestions, request)

    pipeline = patched.block_by_id("003_pipeline")
    end = patched.block_by_id("005_end")
    assert pipeline.source_end == 15.4
    assert pipeline.video_duration == 7.4
    assert pipeline.video_duration >= pipeline.tts_duration
    assert end.text == "Gemini plans. FFmpeg renders."

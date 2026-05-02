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


def test_extend_end_patch_updates_source_duration():
    manifest = BlockManifest.from_file(SAMPLE_PROJECT / "manifests" / "block_manifest.json")
    suggestions = CriticSuggestions.model_validate(
        {
            "project_id": "demo_project",
            "critic_scope": "blind_manifest_only",
            "suggestions": [
                {
                    "suggestion_id": "s_extend",
                    "block_id": "004_approval",
                    "action": "extend_end",
                    "amount_seconds": 1.25,
                    "reason": "Give the approval step a little more room.",
                    "requires_approval": True,
                }
            ],
        }
    )
    request = ApplyPatchesRequest.model_validate(
        {"project_id": "demo_project", "approved_suggestion_ids": ["s_extend"]}
    )

    patched = apply_suggestions_to_manifest(manifest, suggestions, request)
    approval = patched.block_by_id("004_approval")

    assert approval.source_end == 27.25
    assert approval.video_duration == 8.25


def test_replace_text_patch_updates_text_block():
    manifest = BlockManifest.from_file(SAMPLE_PROJECT / "manifests" / "block_manifest.json")
    suggestions = CriticSuggestions.model_validate(
        {
            "project_id": "demo_project",
            "critic_scope": "blind_manifest_only",
            "suggestions": [
                {
                    "suggestion_id": "s_text",
                    "block_id": "005_end",
                    "action": "replace_text",
                    "amount_seconds": 0.0,
                    "reason": "Make the human approval loop explicit.",
                    "replacement_text": "Gemini plans. Humans approve. FFmpeg renders.",
                    "requires_approval": True,
                }
            ],
        }
    )
    request = ApplyPatchesRequest.model_validate(
        {"project_id": "demo_project", "approved_suggestion_ids": ["s_text"]}
    )

    patched = apply_suggestions_to_manifest(manifest, suggestions, request)

    assert patched.block_by_id("005_end").text == "Gemini plans. Humans approve. FFmpeg renders."


def test_lower_source_audio_patch_updates_volume():
    manifest = BlockManifest.from_file(SAMPLE_PROJECT / "manifests" / "block_manifest.json")
    suggestions = CriticSuggestions.model_validate(
        {
            "project_id": "demo_project",
            "critic_scope": "blind_manifest_only",
            "suggestions": [
                {
                    "suggestion_id": "s_audio",
                    "block_id": "002_problem",
                    "action": "lower_source_audio",
                    "amount_seconds": 0.0,
                    "reason": "Make narration easier to hear.",
                    "source_audio_volume": 0.05,
                    "requires_approval": True,
                }
            ],
        }
    )
    request = ApplyPatchesRequest.model_validate(
        {"project_id": "demo_project", "approved_suggestion_ids": ["s_audio"]}
    )

    patched = apply_suggestions_to_manifest(manifest, suggestions, request)

    assert patched.block_by_id("002_problem").source_audio_volume == 0.05


def test_unknown_approved_suggestion_id_fails():
    manifest = BlockManifest.from_file(SAMPLE_PROJECT / "manifests" / "block_manifest.json")
    suggestions = CriticSuggestions.from_file(SAMPLE_PROJECT / "manifests" / "critic_suggestions.json")
    request = ApplyPatchesRequest.model_validate(
        {"project_id": "demo_project", "approved_suggestion_ids": ["s_missing"]}
    )

    with pytest.raises(KeyError, match="Unknown approved suggestion_id"):
        apply_suggestions_to_manifest(manifest, suggestions, request)

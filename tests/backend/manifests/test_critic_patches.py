from pathlib import Path

import pytest

from backend.app.manifests.models import ApplyPatchesRequest, BlockManifest, CriticSuggestions
from backend.app.manifests.service import apply_suggestions_to_manifest, validate_critic_suggestions


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_PROJECT = PROJECT_ROOT / "samples" / "demo_project"


def test_critic_trim_that_consumes_entire_clip_fails():
    manifest = BlockManifest.from_file(SAMPLE_PROJECT / "manifests" / "block_manifest.json")
    suggestions = CriticSuggestions.model_validate(
        {
            "project_id": "demo_project",
            "critic_scope": "blind_manifest_only",
            "suggestions": [
                {
                    "suggestion_id": "s_bad",
                    "block_id": "003_beat_003",
                    "action": "trim_end",
                    "amount_seconds": 3.0,
                    "max_allowed_trim_seconds": 0.0,
                    "reason": "Trim it all away.",
                    "requires_approval": True,
                }
            ],
        }
    )

    with pytest.raises(ValueError, match="must leave a positive source clip duration"):
        validate_critic_suggestions(manifest, suggestions)


def test_large_human_approved_trim_is_allowed():
    manifest = BlockManifest.from_file(SAMPLE_PROJECT / "manifests" / "block_manifest.json")
    suggestions = CriticSuggestions.model_validate(
        {
            "project_id": "demo_project",
            "critic_scope": "render_review",
            "suggestions": [
                {
                    "suggestion_id": "s_trim",
                    "block_id": "004_beat_004",
                    "action": "trim_end",
                    "amount_seconds": 2.0,
                    "max_allowed_trim_seconds": 0.0,
                    "reason": "Tighten the beat a lot.",
                    "requires_approval": True,
                }
            ],
        }
    )
    request = ApplyPatchesRequest.model_validate(
        {"project_id": "demo_project", "approved_suggestion_ids": ["s_trim"]}
    )

    patched = apply_suggestions_to_manifest(manifest, suggestions, request)

    assert patched.block_by_id("004_beat_004").video_duration == 5.0


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

    pipeline = patched.block_by_id("002_beat_002")
    end = patched.block_by_id("005_end")
    assert pipeline.source_end == 3.0
    assert pipeline.video_duration == 3.0
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
                    "block_id": "004_beat_004",
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
    approval = patched.block_by_id("004_beat_004")

    assert approval.source_end == 27.0
    assert approval.video_duration == 8.0


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
                    "block_id": "002_beat_002",
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

    assert patched.block_by_id("002_beat_002").source_audio_volume == 0.05


def test_unknown_approved_suggestion_id_fails():
    manifest = BlockManifest.from_file(SAMPLE_PROJECT / "manifests" / "block_manifest.json")
    suggestions = CriticSuggestions.from_file(SAMPLE_PROJECT / "manifests" / "critic_suggestions.json")
    request = ApplyPatchesRequest.model_validate(
        {"project_id": "demo_project", "approved_suggestion_ids": ["s_missing"]}
    )

    with pytest.raises(KeyError, match="Unknown approved suggestion_id"):
        apply_suggestions_to_manifest(manifest, suggestions, request)


def test_reorder_after_moves_block_after_target():
    manifest = BlockManifest.model_validate(
        {
            "project_id": "demo_project",
            "version": 1,
            "render_settings": {},
            "blocks": [
                {
                    "block_id": "001_title",
                    "type": "title",
                    "background_asset": "assets/backgrounds/bg_001.png",
                    "text": "Title",
                    "duration": 2.0,
                    "fontfile": "assets/fonts/Inter-Bold.ttf",
                    "rendered_path": "blocks/001_title.mp4",
                },
                {
                    "block_id": "002_demo",
                    "type": "source_clip",
                    "source": "source/demo.mp4",
                    "source_start": 0.0,
                    "source_end": 3.0,
                    "video_duration": 3.0,
                    "rendered_path": "blocks/002_demo.mp4",
                },
                {
                    "block_id": "003_wrap",
                    "type": "end_card",
                    "background_asset": "assets/backgrounds/bg_003.png",
                    "text": "Wrap",
                    "duration": 2.0,
                    "fontfile": "assets/fonts/Inter-Bold.ttf",
                    "rendered_path": "blocks/003_wrap.mp4",
                },
            ],
        }
    )
    suggestions = CriticSuggestions.model_validate(
        {
            "project_id": "demo_project",
            "critic_scope": "render_review",
            "suggestions": [
                {
                    "suggestion_id": "s_reorder",
                    "block_id": "001_title",
                    "target_block_id": "002_demo",
                    "action": "reorder_after",
                    "amount_seconds": 0.0,
                    "max_allowed_trim_seconds": 0.0,
                    "reason": "Open on the product moment first.",
                    "requires_approval": True,
                    "category": "ordering",
                    "severity": "medium",
                    "confidence": 0.68,
                    "viewer_problem": "The intro text delays the strongest visual hook.",
                    "evidence": ["shot_index: high motion begins in 002_demo"],
                    "before_summary": "Title first",
                    "after_summary": "Title after demo hook",
                }
            ],
        }
    )
    request = ApplyPatchesRequest.model_validate(
        {"project_id": "demo_project", "approved_suggestion_ids": ["s_reorder"]}
    )

    patched = apply_suggestions_to_manifest(manifest, suggestions, request)

    assert [block.block_id for block in patched.blocks] == ["002_demo", "001_title", "003_wrap"]


def test_invalid_approved_suggestion_is_skipped_while_valid_one_applies():
    manifest = BlockManifest.model_validate(
        {
            "project_id": "demo_project",
            "version": 1,
            "render_settings": {},
            "blocks": [
                {
                    "block_id": "001_title",
                    "type": "title",
                    "background_asset": "assets/backgrounds/bg_001.png",
                    "text": "Title",
                    "duration": 3.0,
                    "fontfile": "assets/fonts/Inter-Bold.ttf",
                    "rendered_path": "blocks/001_title.mp4",
                },
                {
                    "block_id": "002_demo",
                    "type": "source_clip",
                    "source": "source/demo.mp4",
                    "source_start": 0.0,
                    "source_end": 3.0,
                    "video_duration": 3.0,
                    "source_audio_volume": 1.0,
                    "tts_fade_seconds": 0.5,
                    "rendered_path": "blocks/002_demo.mp4",
                },
            ],
        }
    )
    suggestions = CriticSuggestions.model_validate(
        {
            "project_id": "demo_project",
            "critic_scope": "render_review",
            "suggestions": [
                {
                    "suggestion_id": "s_bad",
                    "block_id": "001_title",
                    "action": "trim_end",
                    "amount_seconds": 1.0,
                    "max_allowed_trim_seconds": 0.9,
                    "reason": "This is invalid on title blocks.",
                    "requires_approval": True,
                },
                {
                    "suggestion_id": "s_good",
                    "block_id": "002_demo",
                    "action": "lower_source_audio",
                    "amount_seconds": 0.0,
                    "reason": "Make dialogue clearer.",
                    "source_audio_volume": 0.05,
                    "requires_approval": True,
                },
            ],
        }
    )
    request = ApplyPatchesRequest.model_validate(
        {"project_id": "demo_project", "approved_suggestion_ids": ["s_bad", "s_good"]}
    )

    patched = apply_suggestions_to_manifest(manifest, suggestions, request)

    assert patched.block_by_id("001_title").duration == 3.0
    assert patched.block_by_id("002_demo").source_audio_volume == 0.05

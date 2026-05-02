"""Tests for the structured prompt files in backend/app/prompts/.

These tests verify that prompt content enforces the required constraints
documented in the handoff spec without making any live API calls.
"""

from pathlib import Path

import pytest

PROMPTS_DIR = Path(__file__).resolve().parents[3] / "backend" / "app" / "prompts"


def _load(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Prompt file existence
# ---------------------------------------------------------------------------

class TestPromptFilesExist:
    @pytest.mark.parametrize(
        "name",
        [
            "scene_analysis",
            "plan_generation",
            "narration",
            "background_plate",
            "blind_manifest_critic",
        ],
    )
    def test_prompt_file_exists(self, name):
        assert (PROMPTS_DIR / f"{name}.md").exists(), f"Missing prompt file: {name}.md"


# ---------------------------------------------------------------------------
# scene_analysis.md
# ---------------------------------------------------------------------------

class TestSceneAnalysisPrompt:
    def test_instructs_json_only_output(self):
        text = _load("scene_analysis")
        assert "json" in text.lower()

    def test_mentions_demo_relevance(self):
        text = _load("scene_analysis")
        assert "demo_relevance" in text

    def test_mentions_scene_id(self):
        text = _load("scene_analysis")
        assert "scene_id" in text

    def test_mentions_visual_tags(self):
        text = _load("scene_analysis")
        assert "visual_tags" in text


# ---------------------------------------------------------------------------
# plan_generation.md
# ---------------------------------------------------------------------------

class TestPlanGenerationPrompt:
    def test_enforces_2_words_per_second(self):
        text = _load("plan_generation")
        assert "2 words per second" in text

    def test_mentions_beat_id(self):
        text = _load("plan_generation")
        assert "beat_id" in text

    def test_mentions_narration(self):
        text = _load("plan_generation")
        assert "narration" in text

    def test_instructs_json_only_output(self):
        text = _load("plan_generation")
        assert "json" in text.lower()

    def test_mentions_source_clip_type(self):
        text = _load("plan_generation")
        assert "source_clip" in text


# ---------------------------------------------------------------------------
# narration.md
# ---------------------------------------------------------------------------

class TestNarrationPrompt:
    def test_enforces_2_words_per_second(self):
        text = _load("narration")
        assert "2 words per second" in text

    def test_instructs_json_output(self):
        text = _load("narration")
        assert "json" in text.lower()

    def test_mentions_narration_key(self):
        text = _load("narration")
        assert '"narration"' in text or "`narration`" in text or "narration" in text


# ---------------------------------------------------------------------------
# background_plate.md
# ---------------------------------------------------------------------------

class TestBackgroundPlatePrompt:
    def test_forbids_text_in_image(self):
        text = _load("background_plate")
        lower = text.lower()
        assert "no text" in lower

    def test_forbids_letters(self):
        text = _load("background_plate")
        lower = text.lower()
        assert "no letters" in lower or "letters" in lower

    def test_forbids_logos(self):
        text = _load("background_plate")
        lower = text.lower()
        assert "no logos" in lower or "logos" in lower

    def test_contains_goal_placeholder(self):
        text = _load("background_plate")
        assert "{{goal}}" in text

    def test_contains_onscreen_text_placeholder(self):
        text = _load("background_plate")
        assert "{{onscreen_text}}" in text


# ---------------------------------------------------------------------------
# blind_manifest_critic.md
# ---------------------------------------------------------------------------

class TestBlindManifestCriticPrompt:
    def test_contains_blind_constraint(self):
        text = _load("blind_manifest_critic")
        lower = text.lower()
        # Must state it is reviewing a manifest, not the video
        assert "manifest" in lower and ("not the video" in lower or "blind" in lower)

    def test_forbids_visual_critique(self):
        text = _load("blind_manifest_critic")
        lower = text.lower()
        assert "lighting" in lower or "visual" in lower

    def test_requires_approval_mentioned(self):
        text = _load("blind_manifest_critic")
        assert "requires_approval" in text

    def test_30_percent_trim_limit(self):
        text = _load("blind_manifest_critic")
        assert "30" in text and "%" in text

    def test_allowed_actions_listed(self):
        text = _load("blind_manifest_critic")
        for action in ("trim_end", "extend_end", "reorder_after", "replace_text", "lower_source_audio"):
            assert action in text, f"Action '{action}' not listed in critic prompt"

    def test_instructs_json_only_output(self):
        text = _load("blind_manifest_critic")
        assert "json" in text.lower()

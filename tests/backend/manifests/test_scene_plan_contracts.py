from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.manifests.models import Plan, SceneIndex


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_PROJECT = PROJECT_ROOT / "samples" / "demo_project"


def test_sample_scene_index_fixture_validates():
    scene_index = SceneIndex.from_file(SAMPLE_PROJECT / "cache" / "scene_index.json")

    assert scene_index.project_id == "demo_project"
    assert scene_index.source_duration == pytest.approx(41.872)
    assert scene_index.scene_by_id("scene_002").start == 3.0


def test_scene_index_rejects_scene_outside_source_duration():
    with pytest.raises(ValidationError, match="within source_duration"):
        SceneIndex.model_validate(
            {
                "project_id": "demo_project",
                "source": "source/demo_footage.mp4",
                "source_duration": 10.0,
                "scenes": [
                    {
                        "scene_id": "scene_bad",
                        "start": 8.0,
                        "end": 12.0,
                        "summary": "Too long.",
                        "visual_tags": [],
                        "audio_notes": "None.",
                        "demo_relevance": 0.5,
                    }
                ],
            }
        )


def test_sample_plan_fixture_validates_against_scene_index():
    scene_index = SceneIndex.from_file(SAMPLE_PROJECT / "cache" / "scene_index.json")
    plan = Plan.model_validate(
        {
            "project_id": "demo_project",
            "title": "DirectorLoop Demo Cut",
            "target_duration": 12.0,
            "story_arc": ["Hook", "Proof", "Wrap"],
            "beats": [
                {
                    "beat_id": "beat_001",
                    "type": "title",
                    "goal": "Open strong.",
                    "scene_id": None,
                    "duration": 3.0,
                    "narration": None,
                    "onscreen_text": "DirectorLoop",
                },
                {
                    "beat_id": "beat_003",
                    "type": "source_clip",
                    "goal": "Show the interaction.",
                    "scene_id": "scene_003",
                    "duration": 3.0,
                    "narration": None,
                    "onscreen_text": None,
                },
            ],
        }
    )

    plan.validate_against_scene_index(scene_index)

    assert plan.title == "DirectorLoop Demo Cut"
    assert plan.beat_by_id("beat_003").scene_id == "scene_003"


def test_plan_rejects_unknown_source_scene_reference():
    scene_index = SceneIndex.from_file(SAMPLE_PROJECT / "cache" / "scene_index.json")
    plan = Plan.model_validate(
        {
            "project_id": "demo_project",
            "title": "Bad Plan",
            "target_duration": 5.0,
            "story_arc": ["Show a bad reference."],
            "beats": [
                {
                    "beat_id": "beat_bad",
                    "type": "source_clip",
                    "goal": "Reference a missing scene.",
                    "scene_id": "scene_missing",
                    "duration": 3.0,
                    "narration": "This scene does not exist.",
                    "onscreen_text": None,
                }
            ],
        }
    )

    with pytest.raises(ValueError, match="Unknown scene_id"):
        plan.validate_against_scene_index(scene_index)


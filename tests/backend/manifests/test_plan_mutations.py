from pathlib import Path

from backend.app.manifests.models import BeatStyle, CreateBeatRequest, Plan, PlanReorderRequest
from backend.app.manifests.service import delete_plan_beat, insert_plan_beat, reorder_plan_beats, write_plan


def _seed_project(tmp_path: Path) -> Path:
    project = tmp_path
    (project / "cache").mkdir()
    (project / "manifests").mkdir()
    (project / "source").mkdir()
    (project / "cache" / "scene_index.json").write_text(
        """
        {
          "project_id": "demo_project",
          "total_duration_seconds": 12.0,
          "sources": [
            {
              "path": "source/demo.mp4",
              "duration_seconds": 12.0,
              "start_offset_seconds": 0.0,
              "end_offset_seconds": 12.0
            }
          ],
          "scenes": [
            {
              "scene_id": "scene_001",
              "source": "source/demo.mp4",
              "start": 0.0,
              "end": 4.0,
              "summary": "Intro",
              "visual_tags": [],
              "audio_notes": "",
              "demo_relevance": 0.8
            },
            {
              "scene_id": "scene_002",
              "source": "source/demo.mp4",
              "start": 4.0,
              "end": 8.0,
              "summary": "Middle",
              "visual_tags": [],
              "audio_notes": "",
              "demo_relevance": 0.9
            }
          ]
        }
        """.strip(),
        encoding="utf-8",
    )
    plan = Plan.model_validate(
        {
          "project_id": "demo_project",
          "title": "DirectorLoop Demo Cut",
          "target_duration": 10.0,
          "story_arc": ["Hook", "Proof", "Close"],
          "beats": [
            {"beat_id": "beat_001", "type": "title", "goal": "Hook", "scene_id": None, "duration": 2.0, "narration": None, "onscreen_text": "DirectorLoop"},
            {"beat_id": "beat_002", "type": "source_clip", "goal": "Show intro", "scene_id": "scene_001", "duration": 3.0, "narration": None, "onscreen_text": None},
            {"beat_id": "beat_003", "type": "source_clip", "goal": "Show proof", "scene_id": "scene_002", "duration": 3.0, "narration": None, "onscreen_text": None}
          ]
        }
    )
    write_plan(project, plan)
    return project


def test_reorder_plan_beats_updates_sequence_and_renumbers(tmp_path, monkeypatch):
    project = _seed_project(tmp_path)
    monkeypatch.setattr("backend.app.manifests.service._rebuild_manifest_and_render", lambda *args, **kwargs: None)

    updated = reorder_plan_beats(project, PlanReorderRequest.model_validate({"beat_order": ["beat_003", "beat_001", "beat_002"]}))

    assert [beat.goal for beat in updated.beats] == ["Show proof", "Hook", "Show intro"]
    assert [beat.beat_id for beat in updated.beats] == ["beat_001", "beat_002", "beat_003"]


def test_delete_plan_beat_removes_target_and_renumbers(tmp_path, monkeypatch):
    project = _seed_project(tmp_path)
    monkeypatch.setattr("backend.app.manifests.service._rebuild_manifest_and_render", lambda *args, **kwargs: None)

    updated = delete_plan_beat(project, "beat_002")

    assert [beat.goal for beat in updated.beats] == ["Hook", "Show proof"]
    assert [beat.beat_id for beat in updated.beats] == ["beat_001", "beat_002"]


def test_insert_plan_beat_adds_scene_card_after_requested_beat(tmp_path, monkeypatch):
    project = _seed_project(tmp_path)
    monkeypatch.setattr("backend.app.manifests.service._regenerate_after_plan_mutation", lambda *args, **kwargs: None)

    updated = insert_plan_beat(
        project,
        CreateBeatRequest.model_validate(
            {
                "type": "scene_card",
                "text": "Results",
                "duration": 3.0,
                "insert_after": "beat_002",
                "style": BeatStyle.model_validate({"layout_preset": "stacked", "background_color": "#111827"}),
            }
        ),
    )

    assert [beat.type for beat in updated.beats] == ["title", "source_clip", "scene_card", "source_clip"]
    assert updated.beats[2].onscreen_text == "Results"


def test_insert_plan_beat_adds_image_card(tmp_path, monkeypatch):
    project = _seed_project(tmp_path)
    monkeypatch.setattr("backend.app.manifests.service._regenerate_after_plan_mutation", lambda *args, **kwargs: None)

    updated = insert_plan_beat(
        project,
        CreateBeatRequest.model_validate(
            {
                "type": "image_card",
                "text": "Launch visual",
                "duration": 4.0,
                "image_prompt": "A cinematic launch visual with polished reflections",
                "ken_burns": True,
            }
        ),
    )

    assert updated.beats[-1].type == "image_card"
    assert updated.beats[-1].image_prompt == "A cinematic launch visual with polished reflections"
    assert updated.beats[-1].ken_burns is True


def test_reorder_does_not_call_gemini(tmp_path, monkeypatch):
    """Reorder is purely structural -- must never trigger Gemini asset generation."""
    project = _seed_project(tmp_path)

    gemini_called = False

    def _trap_generate(*args, **kwargs):
        nonlocal gemini_called
        gemini_called = True

    monkeypatch.setattr(
        "backend.app.manifests.service._regenerate_after_plan_mutation",
        _trap_generate,
    )
    monkeypatch.setattr(
        "backend.app.manifests.service._rebuild_manifest_and_render",
        lambda *args, **kwargs: None,
    )

    reorder_plan_beats(project, PlanReorderRequest.model_validate({"beat_order": ["beat_002", "beat_001", "beat_003"]}))

    assert not gemini_called, "reorder_plan_beats must NOT call the full Gemini regeneration path"


def test_delete_does_not_call_gemini(tmp_path, monkeypatch):
    """Delete is purely structural -- must never trigger Gemini asset generation."""
    project = _seed_project(tmp_path)

    gemini_called = False

    def _trap_generate(*args, **kwargs):
        nonlocal gemini_called
        gemini_called = True

    monkeypatch.setattr(
        "backend.app.manifests.service._regenerate_after_plan_mutation",
        _trap_generate,
    )
    monkeypatch.setattr(
        "backend.app.manifests.service._rebuild_manifest_and_render",
        lambda *args, **kwargs: None,
    )

    delete_plan_beat(project, "beat_002")

    assert not gemini_called, "delete_plan_beat must NOT call the full Gemini regeneration path"

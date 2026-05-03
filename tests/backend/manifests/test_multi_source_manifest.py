import json

from backend.app.manifests.service import build_manifest_from_plan


def test_build_manifest_uses_scene_source_and_source_local_offsets(tmp_path):
    project = tmp_path
    (project / "cache").mkdir()
    (project / "manifests").mkdir()
    (project / "cache" / "scene_index.json").write_text(
        json.dumps(
            {
                "project_id": "demo_project",
                "total_duration_seconds": 13.0,
                "sources": [
                    {
                        "path": "source/a.mp4",
                        "duration_seconds": 5.0,
                        "start_offset_seconds": 0.0,
                        "end_offset_seconds": 5.0,
                    },
                    {
                        "path": "source/b.mp4",
                        "duration_seconds": 8.0,
                        "start_offset_seconds": 5.0,
                        "end_offset_seconds": 13.0,
                    },
                ],
                "scenes": [
                    {
                        "scene_id": "scene_001",
                        "source": "source/a.mp4",
                        "start": 1.0,
                        "end": 5.0,
                        "summary": "Clip A ending scene",
                        "visual_tags": [],
                        "audio_notes": "",
                        "demo_relevance": 0.8,
                    },
                    {
                        "scene_id": "scene_002",
                        "source": "source/b.mp4",
                        "start": 5.0,
                        "end": 11.0,
                        "summary": "Clip B opening scene",
                        "visual_tags": [],
                        "audio_notes": "",
                        "demo_relevance": 0.8,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (project / "manifests" / "plan.json").write_text(
        json.dumps(
            {
                "project_id": "demo_project",
                "title": "Scenerio Demo Cut",
                "target_duration": 8.0,
                "story_arc": ["Hook", "Proof"],
                "beats": [
                    {
                        "beat_id": "beat_001",
                        "type": "source_clip",
                        "goal": "Use scene from second source",
                        "scene_id": "scene_002",
                        "duration": 6.0,
                        "narration": None,
                        "onscreen_text": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    manifest = build_manifest_from_plan(project)
    block = manifest.block_by_id("001_beat_001")

    assert block.source == "source/b.mp4"
    assert block.source_start == 0.0
    assert block.source_end == 6.0

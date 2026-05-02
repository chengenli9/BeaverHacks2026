from pathlib import Path

BASE = Path("samples/demo_project")


def get_project_path(project_id: str):
    return BASE


def open_demo_project():
    return {
        "project_id": "demo_project",
        "name": "Demo Project",
        "artifacts": {
            "scene_index": (BASE / "cache/scene_index.json").exists(),
            "plan": (BASE / "manifests/plan.json").exists(),
            "manifest": (BASE / "manifests/block_manifest.json").exists(),
            "critic": (BASE / "manifests/critic_suggestions.json").exists(),
            "render": (BASE / "renders/final_render.mp4").exists(),
        },
    }

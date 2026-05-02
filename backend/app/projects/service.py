from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BASE = REPO_ROOT / "samples" / "demo_project"
DEMO_PROJECT_ID = "demo_project"
REQUIRED_FOLDERS = ("source", "cache", "assets", "blocks", "renders", "manifests")


class ProjectNotFoundError(FileNotFoundError):
    pass


def get_project_path(project_id: str):
    if project_id != DEMO_PROJECT_ID:
        raise ProjectNotFoundError(f"Unknown project: {project_id}")
    _validate_project_layout(BASE)
    return BASE


def open_demo_project():
    _validate_project_layout(BASE)
    return {
        "project_id": DEMO_PROJECT_ID,
        "display_name": "Demo Project",
        "artifacts": {
            "scene_index": (BASE / "cache/scene_index.json").exists(),
            "plan": (BASE / "manifests/plan.json").exists(),
            "manifest": (BASE / "manifests/block_manifest.json").exists(),
            "critic": (BASE / "manifests/critic_suggestions.json").exists(),
            "render": (BASE / "renders/final_render.mp4").exists(),
        },
    }


def _validate_project_layout(project_path: Path) -> None:
    if not project_path.is_dir():
        raise ProjectNotFoundError(f"Project folder is missing: {project_path}")
    missing = [folder for folder in REQUIRED_FOLDERS if not (project_path / folder).is_dir()]
    if missing:
        raise ProjectNotFoundError(
            f"Project {project_path.name} is missing required folders: {', '.join(missing)}"
        )

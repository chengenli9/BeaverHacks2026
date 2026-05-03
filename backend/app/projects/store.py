from pathlib import Path
import json

BASE_DIR = Path("projects")
PROJECT_FOLDERS = ("source", "cache", "assets", "blocks", "renders", "manifests", "logs")


def get_project_path(project_id: str) -> Path:
    return BASE_DIR / project_id


def create_project(project_id: str, display_name: str | None = None):
    path = get_project_path(project_id)
    path.mkdir(parents=True, exist_ok=True)

    for sub in PROJECT_FOLDERS:
        (path / sub).mkdir(exist_ok=True)

    save_project(
        project_id,
        {
            "project_id": project_id,
            "name": display_name or project_id,
            "display_name": display_name or project_id,
        },
    )


def load_project(project_id: str) -> dict:
    path = get_project_path(project_id) / "project.json"
    if not path.is_file():
        raise FileNotFoundError(f"Project not found: {project_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_project(project_id: str, data: dict):
    path = get_project_path(project_id) / "project.json"
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

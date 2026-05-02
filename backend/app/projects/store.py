from pathlib import Path
import json

BASE_DIR = Path("projects")


def get_project_path(project_id: str) -> Path:
    return BASE_DIR / project_id


def create_project(project_id: str):
    path = get_project_path(project_id)
    path.mkdir(parents=True, exist_ok=True)

    for sub in ["source", "cache", "assets", "blocks", "renders"]:
        (path / sub).mkdir(exist_ok=True)

    save_project(project_id, {"project_id": project_id})


def load_project(project_id: str) -> dict:
    path = get_project_path(project_id) / "project.json"
    return json.loads(path.read_text())


def save_project(project_id: str, data: dict):
    path = get_project_path(project_id) / "project.json"
    path.write_text(json.dumps(data, indent=2))

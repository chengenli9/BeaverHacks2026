from pathlib import Path
import re
import shutil

from . import store

REPO_ROOT = Path(__file__).resolve().parents[3]
BASE = REPO_ROOT / "samples" / "demo_project"
DEMO_PROJECT_ID = "demo_project"
REQUIRED_FOLDERS = ("source", "cache", "assets", "blocks", "renders", "manifests")
MEDIA_FOLDERS = (*REQUIRED_FOLDERS, "logs")
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}


class ProjectNotFoundError(FileNotFoundError):
    pass


def get_project_path(project_id: str):
    if project_id == DEMO_PROJECT_ID:
        _validate_project_layout(BASE)
        return BASE

    try:
        project = store.load_project(project_id)
    except FileNotFoundError as exc:
        raise ProjectNotFoundError(f"Unknown project: {project_id}") from exc
    project_path = store.get_project_path(project["project_id"])
    _validate_project_layout(project_path)
    return project_path


def open_demo_project():
    _validate_project_layout(BASE)
    return {
        "project_id": DEMO_PROJECT_ID,
        "name": "Demo Project",
        "display_name": "Demo Project",
        "source_path": str(BASE / "source"),
        "artifacts": {
            "media_probe": (BASE / "cache/media_probe.json").exists(),
            "shot_index": (BASE / "cache/shot_index.json").exists(),
            "scene_index": (BASE / "cache/scene_index.json").exists(),
            "plan": (BASE / "manifests/plan.json").exists(),
            "manifest": (BASE / "manifests/block_manifest.json").exists(),
            "critic": (BASE / "manifests/critic_suggestions.json").exists(),
            "render_qa": (BASE / "cache/render_qa.json").exists(),
            "render": (BASE / "renders/final_render.mp4").exists(),
        },
    }


def create_local_project(name: str) -> dict:
    display_name = name.strip() or "New Project"
    base_slug = _slugify(display_name)
    project_id = base_slug
    suffix = 2
    while (store.BASE_DIR / project_id / "project.json").exists():
        project_id = f"{base_slug}-{suffix}"
        suffix += 1

    store.create_project(project_id, display_name)
    return _project_summary(project_id)


def list_all_projects() -> list[dict]:
    raw_projects = store.list_projects()
    summaries = []
    
    # Always include the demo project
    summaries.append(open_demo_project())

    for p in raw_projects:
        try:
            summaries.append(_project_summary(p["project_id"]))
        except ProjectNotFoundError:
            continue

    # Sort: Starred first, then newest
    summaries.sort(key=lambda x: (not x.get("starred", False), x.get("updated_at", "")))
    return summaries


def update_project(project_id: str, updates: dict) -> dict:
    if project_id == DEMO_PROJECT_ID:
        raise ProjectNotFoundError("Cannot edit the demo project.")
    
    try:
        project = store.load_project(project_id)
    except FileNotFoundError as exc:
        raise ProjectNotFoundError(f"Unknown project: {project_id}") from exc

    new_project_id = project_id

    if "name" in updates:
        new_name = updates["name"]
        project["name"] = new_name
        project["display_name"] = new_name

        # Rename directory to match new name
        slug = _slugify(new_name)
        if slug != project_id:
            new_id = slug
            suffix = 2
            while store.get_project_path(new_id).exists() and new_id != project_id:
                new_id = f"{slug}-{suffix}"
                suffix += 1
            
            if new_id != project_id:
                old_path = store.get_project_path(project_id)
                new_path = store.get_project_path(new_id)
                if old_path.exists():
                    import shutil
                    shutil.move(str(old_path), str(new_path))
                project["project_id"] = new_id
                new_project_id = new_id

    if "description" in updates:
        project["description"] = updates["description"]
    if "starred" in updates:
        project["starred"] = updates["starred"]
        
    from datetime import datetime, timezone
    project["updated_at"] = datetime.now(timezone.utc).isoformat()
        
    store.save_project(new_project_id, project)
    return _project_summary(new_project_id)


def delete_local_project(project_id: str):
    if project_id == DEMO_PROJECT_ID:
        raise ProjectNotFoundError("Cannot delete the demo project.")
        
    try:
        store.load_project(project_id)
    except FileNotFoundError as exc:
        raise ProjectNotFoundError(f"Unknown project: {project_id}") from exc
        
    store.delete_project(project_id)
    return {"status": "deleted"}


def list_project_media(project_id: str) -> dict:
    project_path = get_project_path(project_id)
    return {
        "project_id": project_id,
        "files": [_media_node(project_path, project_path / folder) for folder in MEDIA_FOLDERS if (project_path / folder).exists()],
    }


def import_project_media(project_id: str, files) -> dict:
    project_path = get_project_path(project_id)
    source_dir = project_path / "source"
    source_dir.mkdir(exist_ok=True)
    uploaded = []

    for upload in files:
        target = source_dir / _safe_filename(upload.filename or "media")
        target = _dedupe_path(target)
        with target.open("wb") as destination:
            shutil.copyfileobj(upload.file, destination)
        uploaded.append(_media_node(project_path, target))

    return {"project_id": project_id, "files": uploaded}


def resolve_project_file(project_id: str, relative_path: str) -> Path:
    project_path = get_project_path(project_id).resolve()
    requested = (project_path / relative_path).resolve()
    try:
        requested.relative_to(project_path)
    except ValueError as exc:
        raise ProjectNotFoundError("Unsafe project file path") from exc
    if not requested.is_file():
        raise ProjectNotFoundError(f"Project file not found: {relative_path}")
    return requested


def _validate_project_layout(project_path: Path) -> None:
    if not project_path.is_dir():
        raise ProjectNotFoundError(f"Project folder is missing: {project_path}")
    missing = [folder for folder in REQUIRED_FOLDERS if not (project_path / folder).is_dir()]
    if missing:
        raise ProjectNotFoundError(
            f"Project {project_path.name} is missing required folders: {', '.join(missing)}"
        )


def _project_summary(project_id: str) -> dict:
    project_path = get_project_path(project_id)
    try:
        metadata = store.load_project(project_id)
    except FileNotFoundError:
        metadata = {"project_id": project_id, "display_name": project_id, "name": project_id}
        
    has_manifest = (project_path / "manifests/block_manifest.json").exists()
    has_render = (project_path / "renders/final_render.mp4").exists()
    
    status = metadata.get("status", "empty")
    if status == "empty" and has_manifest:
        status = "active"
        
    thumbnail_type = metadata.get("thumbnail_type", "empty")
    if thumbnail_type == "empty" and has_render:
        thumbnail_type = "timeline"

    return {
        "project_id": project_id,
        "name": metadata.get("name") or metadata.get("display_name") or project_id,
        "display_name": metadata.get("display_name") or metadata.get("name") or project_id,
        "description": metadata.get("description", ""),
        "status": status,
        "progress": metadata.get("progress", 0),
        "thumbnail_type": thumbnail_type,
        "starred": metadata.get("starred", False),
        "updated_at": metadata.get("updated_at", ""),
        "source_path": str(project_path / "source"),
        "artifacts": {
            "media_probe": (project_path / "cache/media_probe.json").exists(),
            "shot_index": (project_path / "cache/shot_index.json").exists(),
            "scene_index": (project_path / "cache/scene_index.json").exists(),
            "plan": (project_path / "manifests/plan.json").exists(),
            "manifest": has_manifest,
            "critic": (project_path / "manifests/critic_suggestions.json").exists(),
            "render_qa": (project_path / "cache/render_qa.json").exists(),
            "render": has_render,
        },
    }


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "new-project"


def _safe_filename(filename: str) -> str:
    cleaned = Path(filename).name
    cleaned = re.sub(r"[^A-Za-z0-9._ -]+", "_", cleaned).strip(" .")
    return cleaned or "media"


def _dedupe_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 2
    while True:
        candidate = parent / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def _media_node(project_path: Path, path: Path) -> dict:
    relative_path = path.relative_to(project_path).as_posix()
    if path.is_dir():
        children = [_media_node(project_path, child) for child in sorted(path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())) if _is_safe_child(project_path, child)]
        return {"name": path.name, "path": relative_path, "type": "folder", "children": children}

    stat = path.stat()
    return {
        "name": path.name,
        "path": relative_path,
        "type": _file_type(path),
        "size": stat.st_size,
    }


def _file_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in AUDIO_EXTENSIONS:
        return "audio"
    if suffix == ".json":
        return "json"
    return "file"


def _is_safe_child(project_path: Path, child: Path) -> bool:
    try:
        child.resolve().relative_to(project_path.resolve())
    except ValueError:
        return False
    return True

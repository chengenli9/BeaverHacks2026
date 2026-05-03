from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.projects import service as project_service
from app.projects import store


client = TestClient(app)


def _paths(nodes):
    result = set()
    for node in nodes:
        result.add(node["path"])
        result.update(_paths(node.get("children", [])))
    return result


def _patch_project_roots(tmp_path, monkeypatch):
    projects_root = tmp_path / "projects"
    demo_root = tmp_path / "demo_project"
    monkeypatch.setattr(store, "BASE_DIR", projects_root)
    monkeypatch.setattr(project_service, "BASE", demo_root)
    return projects_root, demo_root


def test_create_project_creates_required_folders(tmp_path, monkeypatch):
    projects_root, _ = _patch_project_roots(tmp_path, monkeypatch)

    response = client.post("/projects", json={"name": "My Test Project"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "my-test-project"
    assert payload["display_name"] == "My Test Project"
    for folder in ("source", "cache", "assets", "blocks", "renders", "manifests", "logs"):
        assert (projects_root / "my-test-project" / folder).is_dir()


def test_media_listing_returns_real_demo_files(tmp_path, monkeypatch):
    _, demo_root = _patch_project_roots(tmp_path, monkeypatch)
    for folder in ("source", "cache", "assets", "blocks", "renders", "manifests"):
        (demo_root / folder).mkdir(parents=True)
    (demo_root / "source" / "demo_footage.mp4").write_bytes(b"video")
    (demo_root / "manifests" / "plan.json").write_text("{}", encoding="utf-8")

    response = client.get("/projects/demo_project/media")

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "demo_project"
    paths = _paths(payload["files"])
    assert "source/demo_footage.mp4" in paths
    assert "manifests/plan.json" in paths


def test_import_media_writes_uploaded_files_to_source(tmp_path, monkeypatch):
    projects_root, _ = _patch_project_roots(tmp_path, monkeypatch)
    project_root = projects_root / "upload-test"
    store.create_project("upload-test", "Upload Test")

    response = client.post(
        "/projects/upload-test/media/import",
        files={"files": ("clip.mp4", b"fake mp4", "video/mp4")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "upload-test"
    assert payload["files"][0]["path"] == "source/clip.mp4"
    assert (project_root / "source" / "clip.mp4").read_bytes() == b"fake mp4"


def test_media_file_streams_valid_file_and_rejects_traversal(tmp_path, monkeypatch):
    projects_root, _ = _patch_project_roots(tmp_path, monkeypatch)
    store.create_project("stream-test", "Stream Test")
    source_path = projects_root / "stream-test" / "source" / "clip.mp4"
    source_path.write_bytes(b"fake mp4")

    valid = client.get("/projects/stream-test/media/file", params={"path": "source/clip.mp4"})
    traversal = client.get("/projects/stream-test/media/file", params={"path": "../secret.txt"})

    assert valid.status_code == 200
    assert valid.content == b"fake mp4"
    assert traversal.status_code == 400

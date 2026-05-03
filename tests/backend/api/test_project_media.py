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


def test_artifact_routes_serve_media_probe_shot_index_and_render_qa(tmp_path, monkeypatch):
    projects_root, _ = _patch_project_roots(tmp_path, monkeypatch)
    store.create_project("artifact-test", "Artifact Test")
    project_root = projects_root / "artifact-test"

    (project_root / "cache" / "media_probe.json").write_text('{"project_id":"artifact-test","source":"source/demo.mp4","duration_seconds":12.0,"has_audio":true,"video_stream":{"codec":"h264","width":1920,"height":1080,"fps":30.0},"audio_stream":{"codec":"aac","sample_rate":48000}}', encoding="utf-8")
    (project_root / "cache" / "shot_index.json").write_text('{"project_id":"artifact-test","source":"source/demo.mp4","shots":[{"shot_id":"shot_001","start":0.0,"end":4.0,"duration":4.0,"start_frame_path":"cache/frames/shot_001_start.jpg","mid_frame_path":"cache/frames/shot_001_mid.jpg","end_frame_path":"cache/frames/shot_001_end.jpg"}]}', encoding="utf-8")
    (project_root / "cache" / "render_qa.json").write_text('{"project_id":"artifact-test","render_path":"renders/final_render.mp4","summary":{"has_video":true,"has_audio":true,"duration_seconds":12.0},"frame_checks":[],"audio_checks":[],"issues":[]}', encoding="utf-8")

    media_probe = client.get("/projects/artifact-test/media-probe")
    shot_index = client.get("/projects/artifact-test/shot-index")
    render_qa = client.get("/projects/artifact-test/render-qa")

    assert media_probe.status_code == 200
    assert media_probe.json()["video_stream"]["width"] == 1920
    assert shot_index.status_code == 200
    assert shot_index.json()["shots"][0]["shot_id"] == "shot_001"
    assert render_qa.status_code == 200
    assert render_qa.json()["summary"]["has_audio"] is True

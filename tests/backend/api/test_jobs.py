from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/health").status_code == 200


def test_required_backend_routes_are_registered():
    registered = {(route.path, ",".join(sorted(route.methods))) for route in app.routes}

    for path, method in (
        ("/projects/open-demo", "POST"),
        ("/jobs/analyze-scenes", "POST"),
        ("/jobs/generate-plan", "POST"),
        ("/jobs/generate-tts", "POST"),
        ("/jobs/generate-assets", "POST"),
        ("/jobs/build-manifest", "POST"),
        ("/jobs/precritique", "POST"),
        ("/jobs/apply-approved-patches", "POST"),
        ("/jobs/render", "POST"),
        ("/jobs/{job_id}", "GET"),
        ("/projects/{project_id}/scene-index", "GET"),
        ("/projects/{project_id}/plan", "GET"),
        ("/projects/{project_id}/manifest", "GET"),
        ("/projects/{project_id}/critic-suggestions", "GET"),
        ("/projects/{project_id}/render", "GET"),
    ):
        assert any(route_path == path and method in methods for route_path, methods in registered)


def test_open_demo():
    res = client.post("/projects/open-demo")
    assert res.status_code == 200
    assert "project_id" in res.json()


def test_unknown_job():
    res = client.get("/jobs/does-not-exist")
    assert res.status_code == 404


def test_job_creation_returns_immediately(monkeypatch):
    from app.jobs import tasks

    monkeypatch.setattr(tasks, "analyze_scenes", lambda project_path: None)

    res = client.post("/jobs/analyze-scenes", params={"project_id": "demo_project"})
    assert res.status_code == 200
    assert "job_id" in res.json()


def test_all_job_endpoints_enqueue_without_running_inline_work(monkeypatch):
    from app.jobs import tasks

    monkeypatch.setattr(tasks, "analyze_scenes", lambda project_path: None)
    monkeypatch.setattr(tasks, "generate_plan", lambda project_path: None)
    monkeypatch.setattr(tasks, "generate_tts", lambda project_path: None)
    monkeypatch.setattr(tasks, "generate_background_assets", lambda project_path: None)
    monkeypatch.setattr(tasks, "build_manifest", lambda project_path: None)
    monkeypatch.setattr(tasks, "precritique_manifest", lambda project_path: None)
    monkeypatch.setattr(tasks, "render_project", lambda project_path, progress_callback=None: None)

    for path in (
        "/jobs/analyze-scenes",
        "/jobs/generate-plan",
        "/jobs/generate-tts",
        "/jobs/generate-assets",
        "/jobs/build-manifest",
        "/jobs/precritique",
        "/jobs/render",
    ):
        res = client.post(path, params={"project_id": "demo_project"})
        assert res.status_code == 200
        assert res.json()["status"] == "queued"
        assert res.json()["job_id"].startswith("job_")


def test_apply_patches_accepts_documented_request_body(monkeypatch):
    from app.jobs import tasks

    monkeypatch.setattr(tasks, "apply_approved_patches", lambda project_path, request: None)

    res = client.post(
        "/jobs/apply-approved-patches",
        json={
            "project_id": "demo_project",
            "approved_suggestion_ids": ["s001"],
            "rejected_suggestion_ids": ["s002"],
        },
    )

    assert res.status_code == 200
    assert res.json()["status"] == "queued"
    assert res.json()["job_id"].startswith("job_")


def test_unknown_project_artifact_returns_404():
    res = client.get("/projects/not-demo/scene-index")

    assert res.status_code == 404


def test_committed_demo_json_artifacts_are_served():
    for path in (
        "/projects/demo_project/scene-index",
        "/projects/demo_project/plan",
        "/projects/demo_project/manifest",
        "/projects/demo_project/critic-suggestions",
    ):
        res = client.get(path)
        assert res.status_code == 200
        assert res.json()["project_id"] == "demo_project"


def test_demo_render_returns_loadable_metadata():
    res = client.get("/projects/demo_project/render")

    assert res.status_code == 200
    assert res.json()["project_id"] == "demo_project"
    assert res.json()["render_path"] == "renders/final_render.mp4"


def test_render_endpoint_returns_loadable_metadata_when_render_exists(tmp_path, monkeypatch):
    from app.api import routes
    from app.projects import service as project_service

    project_root = tmp_path / "demo_project"
    for folder in ("source", "cache", "assets", "blocks", "renders", "manifests"):
        (project_root / folder).mkdir(parents=True)
    render_path = project_root / "renders" / "final_render.mp4"
    render_path.write_bytes(b"fake mp4 bytes")
    monkeypatch.setattr(project_service, "BASE", project_root)
    monkeypatch.setattr(
        routes,
        "summarize_render",
        lambda project_id, path: {"duration": 12.5, "bytes": len(b"fake mp4 bytes")},
        raising=False,
    )

    res = client.get("/projects/demo_project/render")

    assert res.status_code == 200
    payload = res.json()
    assert payload["project_id"] == "demo_project"
    assert payload["render_path"] == "renders/final_render.mp4"
    assert payload["url"] == "http://localhost:8000/projects/demo_project/render/file"
    assert payload["duration"] == 12.5
    assert payload["bytes"] == len(b"fake mp4 bytes")

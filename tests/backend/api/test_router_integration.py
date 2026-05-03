import os
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import backend, critique, generate, projects, render
from app.jobs import tasks
from app.projects import store


def _noop(*args, **kwargs):
    return None


def test_backend_app_imports_from_backend_working_directory():
    repo_root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [sys.executable, "-c", "from app.main import app; print(len(app.routes))"],
        cwd=repo_root / "backend",
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert int(result.stdout.strip()) > 0


def test_backend_app_imports_from_repo_root_package_name():
    repo_root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)

    result = subprocess.run(
        [sys.executable, "-c", "from backend.app.main import app; print(len(app.routes))"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert int(result.stdout.strip()) > 0


def test_legacy_job_routers_enqueue_current_task_functions(monkeypatch):
    for task_name in (
        "analyze_scenes",
        "generate_plan",
        "generate_background_assets",
        "build_manifest",
        "precritique_manifest",
        "review_render",
        "apply_approved_patches",
        "render_project",
    ):
        monkeypatch.setattr(tasks, task_name, _noop)

    app = FastAPI()
    app.include_router(generate.router, prefix="/generate")
    app.include_router(critique.router, prefix="/critique")
    app.include_router(backend.router, prefix="/backend")
    app.include_router(render.router, prefix="/render")
    client = TestClient(app)

    for path in (
        "/generate/scene-index",
        "/generate/plan",
        "/generate/assets",
        "/generate/block-manifest",
        "/critique/",
        "/backend/",
        "/render/blocks",
        "/render/final",
    ):
        response = client.post(path, params={"project_id": "demo_project"})
        assert response.status_code == 200
        assert response.json()["status"] == "queued"

    apply_body = {
        "project_id": "demo_project",
        "approved_suggestion_ids": ["s001"],
        "rejected_suggestion_ids": [],
    }
    for path in ("/critique/apply", "/backend/apply"):
        response = client.post(path, json=apply_body)
        assert response.status_code == 200
        assert response.json()["status"] == "queued"


def test_main_router_enqueues_review_render_job(monkeypatch):
    monkeypatch.setattr(tasks, "review_render", _noop)

    app = FastAPI()
    from app.api.routes import router

    app.include_router(router)
    client = TestClient(app)

    response = client.post("/jobs/review-render", params={"project_id": "demo_project"})

    assert response.status_code == 200
    assert response.json()["status"] == "queued"


def test_project_router_creates_full_layout_and_404s_missing_projects(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "BASE_DIR", tmp_path)

    app = FastAPI()
    app.include_router(projects.router, prefix="/projects")
    client = TestClient(app)

    missing = client.get("/projects/missing")
    assert missing.status_code == 404

    created = client.post("/projects/create")
    assert created.status_code == 200
    project_id = created.json()["project_id"]

    project_root = tmp_path / project_id
    for folder in ("source", "cache", "assets", "blocks", "renders", "manifests", "logs"):
        assert (project_root / folder).is_dir()

    loaded = client.get(f"/projects/{project_id}")
    assert loaded.status_code == 200
    assert loaded.json()["project_id"] == project_id

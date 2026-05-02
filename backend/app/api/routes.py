from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import json

from app.jobs.store import (
    create_job,
    mark_running,
    update_progress,
    mark_succeeded,
    mark_failed,
    get_job,
)
from app.jobs.runner import run_job
from app.projects.service import open_demo_project, get_project_path

# STUBS (replace later with real imports)
from app.jobs import tasks as svc

router = APIRouter()

# ------------------------
# PROJECT
# ------------------------

@router.post("/projects/open-demo")
def open_demo():
    return open_demo_project()


# ------------------------
# JOB ENDPOINTS
# ------------------------

def _enqueue(bg: BackgroundTasks, project_id: str, stage: str, fn, *args):
    job = create_job(project_id, stage, f"{stage} queued")
    bg.add_task(run_job, job["job_id"], fn, project_id, *args)
    return {"job_id": job["job_id"], "status": job["status"]}


@router.post("/jobs/analyze-scenes")
def analyze(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, project_id, "analyzing_scenes", svc.analyze_scenes)


@router.post("/jobs/generate-plan")
def plan(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, project_id, "generating_plan", svc.generate_plan)


@router.post("/jobs/generate-tts")
def tts(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, project_id, "generating_tts", svc.generate_tts)


@router.post("/jobs/generate-assets")
def assets(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, project_id, "generating_assets", svc.generate_background_assets)


@router.post("/jobs/build-manifest")
def manifest(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, project_id, "building_manifest", svc.build_manifest)


@router.post("/jobs/precritique")
def precritique(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, project_id, "precritique", svc.precritique_manifest)


@router.post("/jobs/apply-approved-patches")
def apply(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, project_id, "apply_patches", svc.apply_approved_patches)


@router.post("/jobs/render")
def render(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, project_id, "rendering", svc.render_project)


@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


# ------------------------
# ARTIFACTS
# ------------------------

def _json_or_404(path: Path):
    if not path.exists():
        raise HTTPException(404, "Artifact not found")
    return json.loads(path.read_text())


@router.get("/projects/{project_id}/scene-index")
def get_scene_index(project_id: str):
    return _json_or_404(get_project_path(project_id) / "cache/scene_index.json")


@router.get("/projects/{project_id}/plan")
def get_plan(project_id: str):
    return _json_or_404(get_project_path(project_id) / "manifests/plan.json")


@router.get("/projects/{project_id}/manifest")
def get_manifest(project_id: str):
    return _json_or_404(get_project_path(project_id) / "manifests/block_manifest.json")


@router.get("/projects/{project_id}/critic-suggestions")
def get_critic(project_id: str):
    return _json_or_404(get_project_path(project_id) / "manifests/critic_suggestions.json")


@router.get("/projects/{project_id}/render")
def get_render(project_id: str):
    path = get_project_path(project_id) / "renders/final_render.mp4"
    if not path.exists():
        raise HTTPException(404, "Render not available")
    return FileResponse(path)
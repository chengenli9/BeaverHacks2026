from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import json

from ..jobs.store import create_job, get_job
from ..jobs.runner import run_job
from ..manifests.models import ApplyPatchesRequest
from ..projects.service import ProjectNotFoundError, get_project_path, open_demo_project
from ..rendering.service import summarize_render

from ..jobs import tasks as svc

router = APIRouter()

# ------------------------
# PROJECT
# ------------------------

@router.post("/projects/open-demo")
def open_demo():
    try:
        return open_demo_project()
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ------------------------
# JOB ENDPOINTS
# ------------------------

def _enqueue(bg: BackgroundTasks, project_id: str, stage: str, fn, *args):
    try:
        get_project_path(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

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
def apply(request: ApplyPatchesRequest, bg: BackgroundTasks):
    return _enqueue(bg, request.project_id, "apply_patches", svc.apply_approved_patches, request)


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
    return json.loads(path.read_text(encoding="utf-8"))


def _project_path_or_404(project_id: str) -> Path:
    try:
        return get_project_path(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/projects/{project_id}/scene-index")
def get_scene_index(project_id: str):
    return _json_or_404(_project_path_or_404(project_id) / "cache/scene_index.json")


@router.get("/projects/{project_id}/plan")
def get_plan(project_id: str):
    return _json_or_404(_project_path_or_404(project_id) / "manifests/plan.json")


@router.get("/projects/{project_id}/manifest")
def get_manifest(project_id: str):
    return _json_or_404(_project_path_or_404(project_id) / "manifests/block_manifest.json")


@router.get("/projects/{project_id}/critic-suggestions")
def get_critic(project_id: str):
    return _json_or_404(_project_path_or_404(project_id) / "manifests/critic_suggestions.json")


@router.get("/projects/{project_id}/render")
def get_render(project_id: str):
    path = _project_path_or_404(project_id) / "renders/final_render.mp4"
    if not path.exists():
        raise HTTPException(404, "Render not available")
    try:
        summary = summarize_render(project_id, path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Render metadata unavailable: {exc}") from exc
    return {
        "project_id": project_id,
        "render_path": "renders/final_render.mp4",
        "url": f"http://localhost:8000/projects/{project_id}/render/file",
        "duration": summary["duration"],
        "bytes": summary["bytes"],
    }


@router.get("/projects/{project_id}/render/file")
def get_render_file(project_id: str):
    path = _project_path_or_404(project_id) / "renders/final_render.mp4"
    if not path.exists():
        raise HTTPException(404, "Render not available")
    return FileResponse(path)

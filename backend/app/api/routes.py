from fastapi import APIRouter, BackgroundTasks, Body, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pathlib import Path
import json
import re

from ..jobs.store import create_job, get_job
from ..jobs.runner import run_job
from ..manifests.models import ApplyPatchesRequest, CreateBeatRequest, PlanEditPromptRequest, PlanReorderRequest, UpdateBeatRequest
from ..projects.service import (
    ProjectNotFoundError,
    create_local_project,
    get_project_path,
    import_project_media,
    list_project_media,
    open_demo_project,
    resolve_project_file,
    list_all_projects,
    update_project,
    delete_local_project,
)
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


@router.get("/projects")
def get_projects():
    return list_all_projects()


@router.post("/projects")
def create_project(payload: dict = Body(...)):
    try:
        return create_local_project(str(payload.get("name") or "New Project"))
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/projects/{project_id}")
def update_project_endpoint(project_id: str, payload: dict = Body(...)):
    try:
        return update_project(project_id, payload)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/projects/{project_id}")
def delete_project_endpoint(project_id: str):
    try:
        return delete_local_project(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/projects/{project_id}/media")
def get_project_media(project_id: str):
    try:
        return list_project_media(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/projects/{project_id}/media/import")
def import_media(project_id: str, files: list[UploadFile] = File(...)):
    try:
        return import_project_media(project_id, files)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/projects/{project_id}/media/file")
def get_project_media_file(project_id: str, path: str = Query(...)):
    try:
        return FileResponse(resolve_project_file(project_id, path))
    except ProjectNotFoundError as exc:
        status_code = 400 if ".." in Path(path).parts or Path(path).is_absolute() else 404
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


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


@router.post("/jobs/review-render")
def review_render(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, project_id, "review_render", svc.review_render)


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


@router.get("/projects/{project_id}/media-probe")
def get_media_probe(project_id: str):
    return _json_or_404(_project_path_or_404(project_id) / "cache/media_probe.json")


@router.get("/projects/{project_id}/shot-index")
def get_shot_index(project_id: str):
    return _json_or_404(_project_path_or_404(project_id) / "cache/shot_index.json")


@router.get("/projects/{project_id}/plan")
def get_plan(project_id: str):
    return _json_or_404(_project_path_or_404(project_id) / "manifests/plan.json")


@router.put("/projects/{project_id}/plan/reorder")
def reorder_plan(project_id: str, request: PlanReorderRequest, bg: BackgroundTasks):
    return _enqueue(bg, project_id, "reordering_plan", svc.reorder_plan_beats, request)


@router.delete("/projects/{project_id}/plan/beats/{beat_id}")
def delete_plan_beat(project_id: str, beat_id: str, bg: BackgroundTasks):
    return _enqueue(bg, project_id, "deleting_plan_beat", svc.delete_plan_beat, beat_id)


@router.post("/projects/{project_id}/plan/edit-prompt")
def edit_plan_prompt(project_id: str, request: PlanEditPromptRequest, bg: BackgroundTasks):
    return _enqueue(bg, project_id, "editing_plan", svc.edit_plan_with_prompt, request.prompt, request.history)


@router.post("/projects/{project_id}/plan/beats")
def create_plan_beat(project_id: str, request: CreateBeatRequest, bg: BackgroundTasks):
    return _enqueue(bg, project_id, "creating_plan_beat", svc.insert_plan_beat, request)


@router.patch("/projects/{project_id}/plan/beats/{beat_id}")
def update_beat(project_id: str, beat_id: str, bg: BackgroundTasks, request: dict = Body(...)):
    return _enqueue(bg, project_id, "edit-plan", svc.update_plan_beat, beat_id, request)


@router.get("/projects/{project_id}/manifest")
def get_manifest(project_id: str):
    return _json_or_404(_project_path_or_404(project_id) / "manifests/block_manifest.json")


@router.get("/projects/{project_id}/critic-suggestions")
def get_critic(project_id: str):
    return _json_or_404(_project_path_or_404(project_id) / "manifests/critic_suggestions.json")


@router.get("/projects/{project_id}/render-qa")
def get_render_qa(project_id: str):
    return _json_or_404(_project_path_or_404(project_id) / "cache/render_qa.json")


@router.get("/music-library")
def get_music_library():
    """Return the global music library as a JSON array."""
    from ..audio.service import load_music_library
    return [track.model_dump() for track in load_music_library()]


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
        "cache_key": str(path.stat().st_mtime_ns),
    }


@router.get("/projects/{project_id}/render/file")
def get_render_file(project_id: str, request: Request):
    path = _project_path_or_404(project_id) / "renders/final_render.mp4"
    if not path.exists():
        raise HTTPException(404, "Render not available")
    file_size = path.stat().st_size
    range_header = request.headers.get("range")
    if not range_header:
        return FileResponse(path, headers={"Accept-Ranges": "bytes"})

    parsed_range = _parse_byte_range(range_header, file_size)
    if parsed_range is None:
        return StreamingResponse(
            _iter_file_bytes(path),
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
            },
        )

    start, end = parsed_range
    content_length = end - start + 1
    return StreamingResponse(
        _iter_file_bytes(path, start=start, end=end),
        status_code=206,
        media_type="video/mp4",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Content-Range": f"bytes {start}-{end}/{file_size}",
        },
    )


_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)$")


def _parse_byte_range(range_header: str, file_size: int) -> tuple[int, int] | None:
    match = _RANGE_RE.fullmatch(range_header.strip())
    if not match or file_size <= 0:
        return None

    start_text, end_text = match.groups()
    if start_text == "" and end_text == "":
        return None

    if start_text == "":
        suffix_length = int(end_text)
        if suffix_length <= 0:
            return None
        start = max(file_size - suffix_length, 0)
        end = file_size - 1
        return (start, end) if start <= end else None

    start = int(start_text)
    if start >= file_size:
        return None

    if end_text == "":
        end = file_size - 1
    else:
        end = min(int(end_text), file_size - 1)

    if end < start:
        return None
    return start, end


def _iter_file_bytes(path: Path, *, start: int = 0, end: int | None = None, chunk_size: int = 64 * 1024):
    with path.open("rb") as handle:
        handle.seek(start)
        remaining = None if end is None else (end - start + 1)
        while True:
            if remaining is not None and remaining <= 0:
                break
            read_size = chunk_size if remaining is None else min(chunk_size, remaining)
            chunk = handle.read(read_size)
            if not chunk:
                break
            yield chunk
            if remaining is not None:
                remaining -= len(chunk)

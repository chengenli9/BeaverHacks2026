from fastapi import APIRouter, BackgroundTasks, HTTPException
from ..jobs.store import create_job
from ..jobs.runner import run_job
from ..jobs import tasks
from ..projects.service import ProjectNotFoundError, get_project_path

router = APIRouter()


def _enqueue(bg: BackgroundTasks, project_id: str, stage: str, fn):
    try:
        get_project_path(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    job = create_job(project_id, stage, f"{stage} queued")
    bg.add_task(run_job, job["job_id"], fn, project_id)
    return {"job_id": job["job_id"], "status": job["status"]}


@router.post("/scene-index")
def scene_index(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, project_id, "analyzing_scenes", tasks.analyze_scenes)


@router.post("/plan")
def plan(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, project_id, "generating_plan", tasks.generate_plan)


@router.post("/assets")
def assets(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, project_id, "generating_assets", tasks.generate_background_assets)


@router.post("/block-manifest")
def block_manifest(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, project_id, "building_manifest", tasks.build_manifest)

from fastapi import APIRouter, BackgroundTasks
from app.jobs.store import create_job
from app.jobs.runner import run_job
from app.jobs import tasks

router = APIRouter()


def _enqueue(bg: BackgroundTasks, job_type: str, fn, project_id: str):
    job = create_job(job_type, {"project_id": project_id})
    bg.add_task(run_job, job["job_id"], fn, project_id)
    return {"job_id": job["job_id"]}


@router.post("/scene-index")
def scene_index(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, "scene_index", tasks.scene_index_task, project_id)


@router.post("/plan")
def plan(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, "plan", tasks.plan_task, project_id)


@router.post("/assets")
def assets(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, "assets", tasks.asset_task, project_id)


@router.post("/block-manifest")
def block_manifest(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, "block_manifest", tasks.block_manifest_task, project_id)

from fastapi import APIRouter, BackgroundTasks
from app.jobs.store import create_job
from app.jobs.runner import run_job
from app.jobs import tasks

router = APIRouter()


def _enqueue(bg: BackgroundTasks, job_type: str, fn, project_id: str):
    job = create_job(job_type, {"project_id": project_id})
    bg.add_task(run_job, job["job_id"], fn, project_id)
    return {"job_id": job["job_id"]}


@router.post("/blocks")
def render_blocks(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, "render_blocks", tasks.render_blocks_task, project_id)


@router.post("/final")
def render_final(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, "render_final", tasks.render_final_task, project_id)

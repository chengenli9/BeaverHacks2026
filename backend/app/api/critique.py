from fastapi import APIRouter, BackgroundTasks
from app.jobs.store import create_job
from app.jobs.runner import run_job
from app.jobs import tasks

router = APIRouter()


def _enqueue(bg: BackgroundTasks, job_type: str, fn, project_id: str):
    job = create_job(job_type, {"project_id": project_id})
    bg.add_task(run_job, job["job_id"], fn, project_id)
    return {"job_id": job["job_id"]}


@router.post("/")
def critique(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, "critique", tasks.critique_task, project_id)


@router.post("/apply")
def apply(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, "apply_patches", tasks.apply_patches_task, project_id)

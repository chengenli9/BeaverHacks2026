from fastapi import APIRouter, BackgroundTasks, HTTPException
from ..manifests.models import ApplyPatchesRequest
from ..jobs.store import create_job
from ..jobs.runner import run_job
from ..jobs import tasks
from ..projects.service import ProjectNotFoundError, get_project_path

router = APIRouter()


def _enqueue(bg: BackgroundTasks, project_id: str, stage: str, fn, *args):
    try:
        get_project_path(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    job = create_job(project_id, stage, f"{stage} queued")
    bg.add_task(run_job, job["job_id"], fn, project_id, *args)
    return {"job_id": job["job_id"], "status": job["status"]}


@router.post("/")
def critique(project_id: str, bg: BackgroundTasks):
    return _enqueue(bg, project_id, "precritique", tasks.precritique_manifest)


@router.post("/apply")
def apply(request: ApplyPatchesRequest, bg: BackgroundTasks):
    return _enqueue(bg, request.project_id, "apply_patches", tasks.apply_approved_patches, request)

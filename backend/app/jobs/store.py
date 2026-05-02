from typing import Dict
from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4

JOBS: Dict[str, dict] = {}
LOCK = Lock()


def now():
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def create_job(project_id: str, stage: str, message: str):
    job_id = f"job_{uuid4().hex[:8]}"

    job = {
        "job_id": job_id,
        "project_id": project_id,
        "status": "queued",
        "stage": stage,
        "progress": 0.0,
        "message": message,
        "error": None,
        "created_at": now(),
        "updated_at": now(),
    }

    with LOCK:
        JOBS[job_id] = job

    return job


def mark_running(job_id: str, message: str):
    update(job_id, status="running", message=message)


def update_progress(job_id: str, progress: float, message: str):
    update(job_id, progress=progress, message=message)


def mark_succeeded(job_id: str, message: str):
    update(job_id, status="succeeded", progress=1.0, message=message)


def mark_failed(job_id: str, error: str):
    update(job_id, status="failed", error=error, message="Job failed")


def update(job_id: str, **fields):
    with LOCK:
        job = JOBS[job_id]
        job.update(fields)
        job["updated_at"] = now()


def get_job(job_id: str):
    with LOCK:
        job = JOBS.get(job_id)
        return dict(job) if job else None

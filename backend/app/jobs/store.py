from typing import Dict
from uuid import uuid4
from datetime import datetime

JOBS: Dict[str, dict] = {}


def create_job(job_type: str, payload: dict) -> dict:
    job_id = str(uuid4())

    job = {
        "job_id": job_id,
        "type": job_type,
        "status": "PENDING",
        "progress": 0.0,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": None,
        "result": None,
        "error": None,
        "meta": payload,
    }

    JOBS[job_id] = job
    return job


def update_job(job_id: str, **updates):
    job = JOBS[job_id]
    job.update(updates)
    job["updated_at"] = datetime.utcnow().isoformat()


def get_job(job_id: str):
    return JOBS.get(job_id)

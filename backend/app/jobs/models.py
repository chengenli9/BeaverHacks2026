from pydantic import BaseModel
from typing import Optional


class JobStatus(BaseModel):
    job_id: str
    project_id: str
    status: str
    stage: str
    progress: float
    message: str
    error: Optional[str]
    created_at: str
    updated_at: str

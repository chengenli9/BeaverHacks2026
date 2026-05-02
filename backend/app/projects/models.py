from pydantic import BaseModel


class ProjectInfo(BaseModel):
    project_id: str
    name: str
    artifacts: dict

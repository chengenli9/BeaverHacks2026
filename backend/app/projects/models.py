from pydantic import BaseModel


class ProjectInfo(BaseModel):
    project_id: str
    display_name: str
    artifacts: dict

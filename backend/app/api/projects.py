from fastapi import APIRouter
from uuid import uuid4
from app.projects.store import create_project, load_project

router = APIRouter()


@router.post("/create")
def create():
    project_id = str(uuid4())
    create_project(project_id)
    return {"project_id": project_id}


@router.get("/{project_id}")
def get(project_id: str):
    return load_project(project_id)

from fastapi import APIRouter, HTTPException
from uuid import uuid4
from ..projects.store import create_project, load_project

router = APIRouter()


@router.post("/create")
def create():
    project_id = str(uuid4())
    create_project(project_id)
    return {"project_id": project_id}


@router.get("/{project_id}")
def get(project_id: str):
    try:
        return load_project(project_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

from fastapi import FastAPI
from app.api import jobs, projects, generate, render, critique

app = FastAPI(title="DirectorLoop Backend")

app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(generate.router, prefix="/generate", tags=["generate"])
app.include_router(render.router, prefix="/render", tags=["render"])
app.include_router(critique.router, prefix="/critique", tags=["critique"])

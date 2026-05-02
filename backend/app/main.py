from fastapi import FastAPI
from app.api import jobs, projects, generate, render, critique

app = FastAPI()

app.include_router(jobs.router)
app.include_router(projects.router)
app.include_router(generate.router)
app.include_router(render.router)
app.include_router(critique.router)
